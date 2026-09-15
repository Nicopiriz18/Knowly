"""Shared FastAPI dependencies: authentication and client identification."""

from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services.auth_service import is_admin, user_from_token

_bearer = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    email: str
    is_admin: bool


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(status_code=401, detail="No autenticado.")
    user = user_from_token(credentials.credentials)
    if user is None:
        raise HTTPException(status_code=401, detail="Sesión inválida o vencida.")
    return CurrentUser(email=user["email"], is_admin=is_admin(user["email"]))


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores.")
    return user


def client_ip(request: Request) -> str:
    # uvicorn already rewrites request.client from X-Forwarded-For when the proxy
    # is trusted (FORWARDED_ALLOW_IPS env var).
    return request.client.host if request.client else "unknown"
