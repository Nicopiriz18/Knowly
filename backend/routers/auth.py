"""Login with email + one-time password, and access requests."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from config import settings
from deps import CurrentUser, client_ip, get_current_user
from schemas import LoginStartRequest, LoginStartResponse, LoginVerifyRequest, LoginVerifyResponse, MeResponse
from services import auth_service
from services.rate_limit import check_rate_limit

logger = logging.getLogger("knowly.auth")

router = APIRouter()

_TEN_MINUTES = 600


@router.post("/start", response_model=LoginStartResponse)
def start(request: Request, body: LoginStartRequest):
    """Send a one-time code to approved emails, or register an access request."""
    email = auth_service.normalize_email(body.email)
    check_rate_limit(f"auth-start:ip:{client_ip(request)}", settings.auth_start_limit_per_ip, _TEN_MINUTES)
    check_rate_limit(f"auth-start:email:{email}", 5, _TEN_MINUTES)
    try:
        status = auth_service.start_login(email)
    except Exception:
        logger.exception("Login start failed for %s", email)
        raise HTTPException(status_code=502, detail="No pudimos enviar el mail. Probá de nuevo en unos minutos.")
    return LoginStartResponse(status=status)


@router.post("/verify", response_model=LoginVerifyResponse)
def verify(request: Request, body: LoginVerifyRequest):
    """Exchange a one-time code for a session token."""
    check_rate_limit(f"auth-verify:ip:{client_ip(request)}", settings.auth_verify_limit_per_ip, _TEN_MINUTES)
    try:
        token = auth_service.verify_otp(body.email, body.code)
    except auth_service.InvalidOTPError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return LoginVerifyResponse(token=token)


@router.get("/me", response_model=MeResponse)
def me(user: CurrentUser = Depends(get_current_user)):
    return MeResponse(email=user.email, is_admin=user.is_admin)
