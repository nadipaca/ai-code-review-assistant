from fastapi import APIRouter
from fastapi.responses import RedirectResponse
import os
import httpx
from fastapi import Request, HTTPException
from fastapi import Response
from app.core.jwt_auth import create_jwt

router = APIRouter(prefix="/api/auth/github", tags=["auth"])

# Simple in-memory session store for demo (not production!)
sessions = {}

@router.get("/login")
async def github_login():
    """
    Step 1: Redirects user to GitHub OAuth consent screen.
    """
    client_id = os.environ["GITHUB_CLIENT_ID"]
    redirect_uri = "http://localhost:8000/api/auth/github/callback"
    github_oauth_url = (
        f"https://github.com/login/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}&scope=read:user repo"
    )
    return RedirectResponse(github_oauth_url)

@router.get("/callback")
async def github_callback(request: Request):
    """
    Step 2: GitHub calls you back here with a `code` parameter.
    You then exchange it for an access token.
    """
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="No code in callback.")
    client_id = os.environ["GITHUB_CLIENT_ID"]
    client_secret = os.environ["GITHUB_CLIENT_SECRET"]
    token_url = "https://github.com/login/oauth/access_token"
    async with httpx.AsyncClient() as client:
        headers = {"Accept": "application/json"}
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": "http://localhost:8000/api/auth/github/callback",
        }
        response = await client.post(token_url, data=data, headers=headers)
        response.raise_for_status()
        token_data = response.json()
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="No access token obtained.")
    
    # Use the access token to get the GitHub user info, create a JWT for your app,
    # set it as an HttpOnly cookie and redirect the user to the app root.
    async with httpx.AsyncClient() as client:
        user_resp = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"token {access_token}", "Accept": "application/json"},
        )
        user_resp.raise_for_status()
        user = user_resp.json()

    # Choose a user identifier to encode in the JWT (id or login)
    # Normalize to string to avoid int/str mismatches when looking up sessions
    github_user_id = str(user.get("id") or user.get("login"))
    # Store user's GitHub access token server-side (DO NOT put in JWT)
    sessions[github_user_id] = {"github_token": access_token}
    jwt_token = create_jwt(github_user_id)

    resp = RedirectResponse("/")
    # In production set secure=True and consider SameSite and domain restrictions
    secure_cookie = os.environ.get("ENV") == "production"
    resp.set_cookie(
        key="access_token",
        value=jwt_token,
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        max_age=14 * 24 * 3600,
        path="/",
    )
    return resp
