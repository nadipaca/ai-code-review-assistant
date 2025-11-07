import httpx
import base64
from typing import List, Dict

class GitHubClient:
    """
    Encapsulates interaction with GitHub API using a user's access token.
    """
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_headers = {
            "Authorization": f"token {self.access_token}",
            "Accept": "application/vnd.github.v3+json"
        }

    async def list_repos(self) -> List[Dict]:
        """
        Lists repositories for the authenticated user.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://api.github.com/user/repos", headers=self.base_headers)
            resp.raise_for_status()
            return resp.json()

    async def get_repo_contents(self, owner: str, repo: str, path: str="") -> List[Dict]:
        """
        Gets contents of a repo directory or file list.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self.base_headers)
            resp.raise_for_status()
            return resp.json()

    async def get_file_content(self, owner: str, repo: str, path: str) -> str:
        """Fetch raw file content for a file in a repository.

        Uses the GitHub Contents API and decodes base64-encoded files.
        Returns the file as a UTF-8 string.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self.base_headers)
            resp.raise_for_status()
            data = resp.json()
            # File responses include 'content' (base64) and 'encoding'
            if isinstance(data, dict) and data.get("encoding") == "base64" and "content" in data:
                raw = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
                return raw
            # Fallback: if the API returned text directly, coerce to string
            return str(data)
