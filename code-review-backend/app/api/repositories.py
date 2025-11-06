from fastapi import APIRouter, Depends, HTTPException, Cookie
from app.core.jwt_auth import verify_jwt
from app.services.github_client import GitHubClient
from app.api.auth import sessions

router = APIRouter(prefix="/api/repos", tags=["repositories"])


# Dependency to get user's access token from cookie/JWT
def get_github_token(access_token: str = Cookie(None)):
    payload = verify_jwt(access_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    # normalize the user id to string to match how we store sessions
    user_id = str(payload["sub"]) if payload is not None else None
    github_token = sessions.get(user_id, {}).get("github_token")
    if not github_token:
        raise HTTPException(status_code=401, detail="No GitHub token found.")
    return github_token


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


@router.get("/list")
async def list_user_repos(github_token: str = Depends(get_github_token)):
    """Return a list of the user's GitHub repositories using their token."""
    client = GitHubClient(github_token)
    repos = await client.list_repos()
    return {"repos": repos}

# List files/folders at path (default 892 root)
@router.get("/{owner}/{repo}/contents")
async def list_contents(owner: str, repo: str, path: str = "", github_token: str = Depends(get_github_token)):
    client = GitHubClient(github_token)
    files = await client.get_repo_contents(owner, repo, path)
    return files
