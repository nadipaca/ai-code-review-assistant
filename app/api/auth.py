from fastapi import APIRouter
from fastapi.responses import RedirectResponse
import os
import httpx
from fastapi import Request, HTTPException

router = APIRouter(prefix="/api/auth/github", tags=["auth"])

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
    # For now, just return the token (in a real app you'd store this!)
    return {"access_token": access_token}
