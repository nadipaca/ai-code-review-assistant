import httpx
from typing import List

class PRPublisher:
    """Posts code review suggestions to GitHub PRs"""
    
    def __init__(self, github_token: str):
        self.github_token = github_token
        self.base_headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    async def publish_review_to_pr(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        suggestions: List[dict]
    ) -> dict:
        """
        Post code review as a PR review.
        
        Args:
            owner: GitHub username/org
            repo: Repository name
            pull_number: PR number
            suggestions: List of {"file": "path", "comment": "review text"}
        
        Returns:
            Response from GitHub API
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/reviews"
        
        # Build a single review body summarizing suggestions instead of inline comments.
        # Inline comments require a valid `position` within the PR diff; to avoid 422 errors
        # when we don't have diff positions, we post a top-level review body that contains
        # per-file suggestions. This always succeeds and is visible on the PR as a review.
        parts = ["## 🤖 AI Code Review Summary", ""]
        for s in suggestions:
            parts.append(f"### {s.get('file')}")
            parts.append(s.get('comment', 'No suggestions'))
            parts.append("")

        payload = {
            "body": "\n".join(parts),
            "event": "COMMENT"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=payload,
                headers=self.base_headers
            )
            response.raise_for_status()
            return response.json()
