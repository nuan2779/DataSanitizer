"""Registration, login, logout and current-session endpoints."""
from __future__ import annotations

import json
import os
import re
import secrets
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from backend.database import (
    create_session,
    delete_session,
    execute_query,
    fetch_one,
    hash_password,
    verify_password,
)
from backend.security import get_current_user, get_session_token

router = APIRouter(prefix="/auth", tags=["Authentication"])
COOKIE_NAME = "datasanitizer_session"
SESSION_DAYS = 7
SESSION_MAX_AGE = SESSION_DAYS * 24 * 60 * 60
COOKIE_SECURE = os.getenv("DATASANITIZER_COOKIE_SECURE", "false").lower() == "true"
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,30}$")


class RegisterRequest(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=30)
    email: str | None = Field(default=None, max_length=254)
    # Allows the current one-field form to submit an email as its identifier.
    identifier: str | None = Field(default=None, max_length=254)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    identifier: str | None = Field(default=None, max_length=254)
    username: str | None = Field(default=None, max_length=254)
    email: str | None = Field(default=None, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class GoogleAuthRequest(BaseModel):
    credential: str | None = Field(default=None, description="Google ID Token from Google Identity Services")
    id_token: str | None = Field(default=None, description="Alias for credential")
    token: str | None = Field(default=None, description="Alias for credential")
    code: str | None = Field(default=None, description="Authorization code or token")


def _public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user["id"],
        "email": user["email"],
        "username": user["username"],
        "created_at": user.get("created_at"),
    }


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


def _create_login_response(response: Response, user: dict[str, Any]) -> dict[str, Any]:
    token = create_session(int(user["id"]), duration_days=SESSION_DAYS)
    _set_session_cookie(response, token)
    return {
        "message": "Authentication successful",
        "user": _public_user(user),
        # access_token supports clients that prefer Authorization: Bearer.
        "access_token": token,
        "token": token,
        "token_type": "bearer",
        "expires_in": SESSION_MAX_AGE,
    }


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, response: Response):
    """Create an account and immediately issue a seven-day session."""
    raw_email = payload.email or payload.identifier
    if not raw_email or not EMAIL_RE.fullmatch(raw_email.strip()):
        raise HTTPException(status_code=422, detail="A valid email address is required")

    email = raw_email.strip().lower()
    raw_username = payload.username
    if not raw_username and payload.identifier and "@" in payload.identifier:
        raw_username = payload.identifier.split("@", 1)[0]
    if not raw_username:
        raw_username = email.split("@", 1)[0]
    username = raw_username.strip().lower()

    if not USERNAME_RE.fullmatch(username):
        raise HTTPException(
            status_code=422,
            detail="Username must be 3-30 characters and contain only letters, numbers, dot, underscore or hyphen",
        )
    if len(payload.password) < 8:
        raise HTTPException(status_code=422, detail="Password must contain at least 8 characters")

    existing = fetch_one(
        "SELECT id FROM users WHERE email = ? OR username = ?",
        (email, username),
    )
    if existing:
        raise HTTPException(status_code=409, detail="Email or username is already registered")

    password_hash, salt = hash_password(payload.password)
    try:
        user_id = execute_query(
            "INSERT INTO users (email, username, password_hash, salt) VALUES (?, ?, ?, ?)",
            (email, username, password_hash, salt),
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Email or username is already registered") from exc

    user = fetch_one(
        "SELECT id, email, username, created_at FROM users WHERE id = ?",
        (user_id,),
    )
    return _create_login_response(response, user)


@router.post("/login")
def login(payload: LoginRequest, response: Response):
    """Authenticate by username or email."""
    identifier = (payload.identifier or payload.username or payload.email or "").strip().lower()
    if not identifier:
        raise HTTPException(status_code=422, detail="Username or email is required")

    user_record = fetch_one(
        "SELECT id, email, username, password_hash, salt, created_at "
        "FROM users WHERE lower(email) = ? OR lower(username) = ?",
        (identifier, identifier),
    )
    if not user_record or not verify_password(
        payload.password,
        user_record["password_hash"],
        user_record["salt"],
    ):
        raise HTTPException(status_code=401, detail="Invalid username/email or password")

    return _create_login_response(response, user_record)


@router.post("/logout")
def logout(response: Response, token: str | None = Depends(get_session_token)):
    """Revoke the current session and clear the browser cookie."""
    if token:
        delete_session(token)
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
    )
    return {"message": "Logged out successfully"}


@router.get("/me")
def get_me(user: dict[str, Any] = Depends(get_current_user)):
    """Return the profile associated with the current session."""
    return {"user": _public_user(user)}


def _verify_google_token(token: str) -> dict[str, Any]:
    """Verify Google ID token via Google's tokeninfo endpoint."""
    encoded = urllib.parse.quote(token.strip())
    url = f"https://oauth2.googleapis.com/tokeninfo?id_token={encoded}"
    req = urllib.request.Request(url, headers={"User-Agent": "DataSanitizer/2.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            err_body = json.loads(exc.read().decode("utf-8"))
            err_msg = err_body.get("error_description") or err_body.get("error") or "Invalid Google authentication token"
        except Exception:
            err_msg = "Google authentication failed"
        raise HTTPException(status_code=401, detail=err_msg) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise HTTPException(status_code=503, detail="Could not reach Google authentication server") from exc

    email = data.get("email")
    email_verified = data.get("email_verified")
    if not email or str(email_verified).lower() not in ("true", "1"):
        raise HTTPException(status_code=400, detail="Google email is unverified or missing")

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    if client_id and data.get("aud") != client_id:
        raise HTTPException(status_code=401, detail="Google token client ID does not match")

    return {
        "email": email.strip().lower(),
        "name": data.get("name") or data.get("given_name") or email.split("@")[0],
        "sub": data.get("sub"),
        "picture": data.get("picture"),
    }


@router.post("/google")
def google_auth(payload: GoogleAuthRequest, response: Response):
    """Authenticate or register a user using Google ID token."""
    raw_token = payload.credential or payload.id_token or payload.token or payload.code
    if not raw_token or not raw_token.strip():
        raise HTTPException(status_code=422, detail="Google credential token is required")

    google_user = _verify_google_token(raw_token.strip())
    email = google_user["email"]

    # 1. Tìm xem email này đã tồn tại trong DB chưa
    user_record = fetch_one(
        "SELECT id, email, username, created_at FROM users WHERE lower(email) = ?",
        (email,),
    )

    if not user_record:
        # 2. Nếu chưa có, tự động tạo tài khoản mới cho người dùng
        raw_name = google_user.get("name") or email.split("@")[0]
        base_username = re.sub(r"[^a-zA-Z0-9_.-]", "", raw_name).lower()[:20]
        if len(base_username) < 3:
            base_username = f"user_{base_username}"[:20]
        if len(base_username) < 3:
            base_username = f"user_{secrets.token_hex(3)}"

        # Đảm bảo username là duy nhất trong SQLite
        candidate = base_username
        counter = 1
        while fetch_one("SELECT id FROM users WHERE lower(username) = ?", (candidate,)):
            candidate = f"{base_username[:17]}_{counter}"
            counter += 1
        username = candidate

        # Sinh hash mật khẩu ngẫu nhiên an toàn
        random_pw = secrets.token_urlsafe(32)
        password_hash, salt = hash_password(random_pw)

        try:
            user_id = execute_query(
                "INSERT INTO users (email, username, password_hash, salt) VALUES (?, ?, ?, ?)",
                (email, username, password_hash, salt),
            )
        except sqlite3.IntegrityError:
            user_record = fetch_one(
                "SELECT id, email, username, created_at FROM users WHERE lower(email) = ?",
                (email,),
            )
            if not user_record:
                raise HTTPException(status_code=500, detail="Could not create user account")

        if not user_record:
            user_record = fetch_one(
                "SELECT id, email, username, created_at FROM users WHERE id = ?",
                (user_id,),
            )

    # 3. Cấp session cookie và trả về thông tin đăng nhập thành công
    return _create_login_response(response, user_record)
