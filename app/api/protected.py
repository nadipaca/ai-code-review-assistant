from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.jwt_auth import verify_jwt

router = APIRouter()

# HTTP Bearer security instance
security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency that validates a JWT passed in the Authorization header.

    Raises HTTP 401 if token is missing/invalid. Returns the user id (sub claim).
    """
    token = credentials.credentials
    payload = verify_jwt(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired JWT token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload.get("sub")


@router.get("/api/protected")
async def protected(user_id: str = Depends(get_current_user)):
    """A protected endpoint — requires Authorization: Bearer <token>."""
    return {"message": f"Hello user {user_id}, you are authenticated!"}
