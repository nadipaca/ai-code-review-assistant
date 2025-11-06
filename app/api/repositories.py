from fastapi import APIRouter, Depends, HTTPException
from app.core.jwt_auth import verify_jwt
from fastapi import Cookie
from app.services.github_client import GitHubClient

router = APIRouter(prefix="/api/repos", tags=["repositories"])

# Dependency to get user's access token from cookie/JWT

def get_github_token(access_token: str = Cookie(None)):
    payload = verify_jwt(access_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    # In a robust app, you'd look up the real GitHub token associated with the user
    # For demo, just assume user_id is the GitHub token
    return payload["sub"]

@router.post("/connect")
async def connect_repo(
    owner: str,
    repo: str,
    github_token: str = Depends(get_github_token),
):
    client = GitHubClient(github_token)
    repos = await client.list_repos()
    # Optionally verify the user owns the repo, then fetch files
    files = await client.get_repo_contents(owner, repo)
    return {"files": files}
