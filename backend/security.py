"""Authentication dependencies shared by protected API routers."""
from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.database import get_user_by_session

bearer_scheme = HTTPBearer(auto_error=False)


def get_session_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str | None:
    """Read a session token from Bearer auth first, then the HttpOnly cookie."""
    if credentials and credentials.scheme.lower() == "bearer":
        return credentials.credentials
    return request.cookies.get("datasanitizer_session")


def get_optional_current_user(
    token: str | None = Depends(get_session_token),
) -> dict[str, Any] | None:
    """Return the authenticated user, or None for an anonymous/offline request."""
    if not token:
        return None
    return get_user_by_session(token)


def get_current_user(
    user: dict[str, Any] | None = Depends(get_optional_current_user),
) -> dict[str, Any]:
    """Require a valid, non-expired session for online workspace endpoints."""
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please log in first.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
