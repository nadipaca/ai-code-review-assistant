import httpx
from typing import Optional, List, Dict
import logging
import base64
import json
import os

# Configuration constant
DEFAULT_TIMEOUT = float(os.getenv("GITHUB_API_TIMEOUT", "30.0"))

class PRCreator:
    """Creates GitHub Pull Requests with actual code changes"""
    
    def __init__(self, github_token: str) -> None:
        self.github_token: str = github_token
        self.base_headers: Dict[str, str] = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    async def _get_default_branch(self, owner: str, repo: str) -> str:
        """Get the default branch of the repository"""
        url = f"https://api.github.com/repos/{owner}/{repo}"
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.get(url, headers=self.base_headers)
            response.raise_for_status()
            repo_info = response.json()
            return repo_info.get('default_branch', 'main')
    
    async def _get_latest_commit_sha(self, owner: str, repo: str, branch: str) -> str:
        """Get the latest commit SHA from a branch"""
        url = f"https://api.github.com/repos/{owner}/{repo}/git/refs/heads/{branch}"
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.get(url, headers=self.base_headers)
            response.raise_for_status()
            ref_info = response.json()
            return ref_info['object']['sha']
    
    async def _get_file_sha(self, owner: str, repo: str, branch: str, path: str) -> Optional[str]:
        """Get the SHA of a file in a specific branch (needed for updates)"""
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            try:
                response = await client.get(url, headers=self.base_headers)
                response.raise_for_status()
                data = response.json()
                return data.get('sha')
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return None  # File doesn't exist
                raise
    
    async def _create_branch(self, owner: str, repo: str, branch_name: str, sha: str) -> bool:
        """Create a new branch from a commit SHA"""
        check_url = f"https://api.github.com/repos/{owner}/{repo}/git/refs/heads/{branch_name}"
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            try:
                check_response = await client.get(check_url, headers=self.base_headers)
                if check_response.status_code == 200:
                    logging.info(f"Branch {branch_name} already exists")
                    return True
            except httpx.HTTPStatusError:
                pass
        
        url = f"https://api.github.com/repos/{owner}/{repo}/git/refs"
        payload = {
            "ref": f"refs/heads/{branch_name}",
            "sha": sha
        }
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            try:
                response = await client.post(url, json=payload, headers=self.base_headers)
                response.raise_for_status()
                logging.info(f"Created branch {branch_name} from {sha}")
                return True
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 422:
                    logging.warning(f"Branch {branch_name} already exists (422)")
                    return True
                logging.error(f"Failed to create branch: {e.response.text}")
                raise

    async def _update_file(
        self,
        owner: str,
        repo: str,
        branch: str,
        path: str,
        content: str,
        message: str
    ) -> dict:
        """
        Create or update a file using GitHub Contents API.
        Returns the commit information.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        
        # Get current file SHA if it exists (required for updates)
        file_sha = await self._get_file_sha(owner, repo, branch, path)
        
        # Encode content as base64
        content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        
        payload = {
            "message": message,
            "content": content_b64,
            "branch": branch
        }
        
        if file_sha:
            payload["sha"] = file_sha  # Required for updates
        
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.put(url, json=payload, headers=self.base_headers)
            response.raise_for_status()
            return response.json()
    
    async def create_review_pr_with_changes(
        self,
        owner: str,
        repo: str,
        base_branch: Optional[str] = None,
        branch_name: Optional[str] = None,  # ✅ Add parameter
        approved_changes: List[Dict] = None,
        title: Optional[str] = None,
        body: Optional[str] = None
    ) -> dict:
        """
        Create a PR with actual code changes based on approved suggestions.
        """
        try:
            if not approved_changes or len(approved_changes) == 0:
                raise ValueError("No approved changes to commit")
            
            if not base_branch:
                base_branch = await self._get_default_branch(owner, repo)
                logging.info(f"Using default branch: {base_branch}")
            
            # ✅ Use provided branch_name or generate one
            if not branch_name:
                import time
                timestamp = int(time.time())
                review_branch = f"ai-review-{timestamp}"
            else:
                review_branch = branch_name
            
            latest_sha = await self._get_latest_commit_sha(owner, repo, base_branch)
            logging.info(f"Latest SHA for {base_branch}: {latest_sha}")
            
            # Create new branch
            await self._create_branch(owner, repo, review_branch, latest_sha)
            
            # Apply each approved change as a separate commit
            commit_count = 0
            for change in approved_changes:
                file_path = change['file']
                modified_content = change['modified_content']
                suggestion = change.get('suggestion', 'AI code review suggestion')
                
                # Create commit message
                commit_msg = f"🤖 AI Review: {file_path}\n\n{suggestion[:200]}"
                
                try:
                    await self._update_file(
                        owner=owner,
                        repo=repo,
                        branch=review_branch,
                        path=file_path,
                        content=modified_content,
                        message=commit_msg
                    )
                    commit_count += 1
                    logging.info(f"Committed changes to {file_path}")
                except Exception as e:
                    logging.error(f"Failed to commit {file_path}: {e}")
                    continue
            
            if commit_count == 0:
                raise ValueError("Failed to commit any changes")
            
            # Generate PR title and body
            if not title:
                title = f"🤖 AI Code Review: {commit_count} file(s) updated"
            
            if not body:
                body = self._format_pr_body(approved_changes)
            
            # Create PR
            url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
            payload = {
                "title": title,
                "body": body,
                "head": review_branch,
                "base": base_branch,
                "draft": False
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=self.base_headers)
                response.raise_for_status()
                pr_data = response.json()
                logging.info(f"Created PR #{pr_data['number']}: {pr_data['html_url']}")
                return pr_data
                
        except httpx.HTTPStatusError as e:
            error_text = e.response.text
            logging.error(f"GitHub API error: {e.response.status_code} - {error_text}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error in create_review_pr_with_changes: {str(e)}")
            raise
    
    def _format_pr_body(self, approved_changes: List[Dict]) -> str:
        """Format approved changes as PR description"""
        parts = ["# 🤖 AI Code Review - Approved Changes\n"]
        parts.append("This PR contains AI-suggested improvements that have been reviewed and approved.\n")
        parts.append(f"\n## Summary\n")
        parts.append(f"- **Files Changed:** {len(approved_changes)}")
        parts.append(f"- **Changes:** Human-reviewed AI suggestions\n")
        
        parts.append("\n## Changes by File\n")
        for idx, change in enumerate(approved_changes, 1):
            file_path = change['file']
            suggestion = change.get('suggestion', 'Code improvement')
            
            parts.append(f"\n### {idx}. `{file_path}`\n")
            parts.append(f"{suggestion}\n")
        
        parts.append("\n---\n")
        parts.append("*🤖 Generated by AI Code Review Assistant*\n")
        parts.append("*All changes were reviewed and approved by a human developer.*")
        
        return "\n".join(parts)