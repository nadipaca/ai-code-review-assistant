from fastapi import APIRouter, Cookie, HTTPException, Depends
from app.core.jwt_auth import verify_jwt

router = APIRouter(prefix="/api", tags=["profile"])


def get_current_user(access_token: str = Cookie(None)):
    """Dependency that verifies JWT from the `access_token` cookie.

    Raises HTTP 401 when token is missing/invalid.
    Returns the decoded payload on success.
    """
    if not access_token:
        raise HTTPException(status_code=401, detail="Missing access token cookie.")
    payload = verify_jwt(access_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    return payload


@router.get("/profile")
async def get_profile(payload: dict = Depends(get_current_user)):
    # Return minimal profile info (user id stored under 'sub')
    return {"user_id": payload.get("sub")}