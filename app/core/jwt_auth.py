from jose import jwt
from datetime import datetime, timedelta
import os

def create_jwt(user_id: str) -> str:
    secret = os.getenv("JWT_SECRET")
    expire = datetime.utcnow() + timedelta(seconds=int(os.getenv("JWT_EXPIRE_SECONDS", 3600)))
    payload = {
        "sub": user_id,
        "exp": expire,
    }
    return jwt.encode(payload, secret, algorithm="HS256")

def verify_jwt(token: str) -> dict:
    secret = os.getenv("JWT_SECRET")
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return payload
    except Exception:
        return None
