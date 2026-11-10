"""Registration, login, logout and current-session endpoints."""
from __future__ import annotations

import os
import re
import sqlite3
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
