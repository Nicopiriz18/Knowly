"""Admin panel: review access requests and manage users."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException

from deps import require_admin
from schemas import UpdateUserStatusRequest, UserInfo
from services import auth_service

router = APIRouter(dependencies=[Depends(require_admin)])


def _to_info(user: dict) -> UserInfo:
    return UserInfo(
        email=user["email"],
        status=user["status"],
        created_at=user["created_at"],
        decided_at=user["decided_at"],
        is_admin=auth_service.is_admin(user["email"]),
    )


@router.get("/users", response_model=list[UserInfo])
def list_users(status: Literal["pending", "approved", "rejected"] | None = None):
    return [_to_info(u) for u in auth_service.list_users(status)]


@router.patch("/users/{email}", response_model=UserInfo)
def update_user_status(email: str, body: UpdateUserStatusRequest):
    """Approve or reject a request. Rejecting an approved user revokes their access."""
    if auth_service.is_admin(email):
        raise HTTPException(status_code=400, detail="No se puede cambiar el acceso de un administrador.")
    user = auth_service.set_user_status(email, body.status)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return _to_info(user)
