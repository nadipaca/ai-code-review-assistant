import httpx
from typing import Optional
import logging
import base64

class PRCreator:
    """Creates GitHub Pull Requests with review suggestions"""
    
    def __init__(self, github_token: str):
        self.github_token = github_token
        self.base_headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    async def _get_default_branch(self, owner: str, repo: str) -> str:
        """Get the default branch of the repository"""
        url = f"https://api.github.com/repos/{owner}/{repo}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.base_headers)
            response.raise_for_status()
            repo_info = response.json()
            return repo_info.get('default_branch', 'main')
    
    async def _get_latest_commit_sha(self, owner: str, repo: str, branch: str) -> str:
        """Get the latest commit SHA from a branch"""
        url = f"https://api.github.com/repos/{owner}/{repo}/git/refs/heads/{branch}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.base_headers)
            response.raise_for_status()
            ref_info = response.json()
            return ref_info['object']['sha']
    
    async def _create_branch(self, owner: str, repo: str, branch_name: str, sha: str) -> bool:
        """Create a new branch from a commit SHA"""
        check_url = f"https://api.github.com/repos/{owner}/{repo}/git/refs/heads/{branch_name}"
        async with httpx.AsyncClient() as client:
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
        async with httpx.AsyncClient() as client:
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

    async def _create_file_commit(
        self,
        owner: str,
        repo: str,
        branch: str,
        file_path: str,
        content: str,
        message: str
    ) -> str:
        """
        Create a commit that adds/updates a file in the repository.
        Returns the new commit SHA.
        """
        # Step 1: Get the current commit SHA of the branch
        current_sha = await self._get_latest_commit_sha(owner, repo, branch)
        
        # Step 2: Get the tree SHA of the current commit
        url = f"https://api.github.com/repos/{owner}/{repo}/git/commits/{current_sha}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.base_headers)
            response.raise_for_status()
            commit_data = response.json()
            base_tree_sha = commit_data['tree']['sha']
        
        # Step 3: Create a blob for the new file content
        blob_url = f"https://api.github.com/repos/{owner}/{repo}/git/blobs"
        blob_payload = {
            "content": base64.b64encode(content.encode('utf-8')).decode('utf-8'),
            "encoding": "base64"
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(blob_url, json=blob_payload, headers=self.base_headers)
            response.raise_for_status()
            blob_sha = response.json()['sha']
        
        # Step 4: Create a new tree with the blob
        tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees"
        tree_payload = {
            "base_tree": base_tree_sha,
            "tree": [
                {
                    "path": file_path,
                    "mode": "100644",  # regular file
                    "type": "blob",
                    "sha": blob_sha
                }
            ]
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(tree_url, json=tree_payload, headers=self.base_headers)
            response.raise_for_status()
            new_tree_sha = response.json()['sha']
        
        # Step 5: Create a commit with the new tree
        commit_url = f"https://api.github.com/repos/{owner}/{repo}/git/commits"
        commit_payload = {
            "message": message,
            "tree": new_tree_sha,
            "parents": [current_sha]
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(commit_url, json=commit_payload, headers=self.base_headers)
            response.raise_for_status()
            new_commit_sha = response.json()['sha']
        
        # Step 6: Update the branch reference to point to the new commit
        ref_url = f"https://api.github.com/repos/{owner}/{repo}/git/refs/heads/{branch}"
        ref_payload = {
            "sha": new_commit_sha,
            "force": False
        }
        async with httpx.AsyncClient() as client:
            response = await client.patch(ref_url, json=ref_payload, headers=self.base_headers)
            response.raise_for_status()
        
        logging.info(f"Created commit {new_commit_sha} on branch {branch}")
        return new_commit_sha

    async def create_review_pr(
        self,
        owner: str,
        repo: str,
        base_branch: Optional[str] = None,
        review_results: dict = None,
        title: Optional[str] = None,
        body: Optional[str] = None
    ) -> dict:
        """Create a new PR with AI review suggestions as the description."""
        try:
            if not base_branch:
                base_branch = await self._get_default_branch(owner, repo)
                logging.info(f"Using default branch: {base_branch}")
            
            import time
            timestamp = int(time.time())
            review_branch = f"ai-review-{timestamp}"
            
            latest_sha = await self._get_latest_commit_sha(owner, repo, base_branch)
            logging.info(f"Latest SHA for {base_branch}: {latest_sha}")
            
            # Create new branch
            await self._create_branch(owner, repo, review_branch, latest_sha)
            
            # Generate review content
            if not title:
                file_count = len(review_results.get('review', [])) if review_results else 0
                title = f"🤖 AI Code Review: {file_count} file(s) analyzed"
            
            if not body:
                body = self._format_review_as_pr_body(review_results or {})
            
            # ✅ KEY FIX: Create a commit with the review content
            review_file_content = f"# AI Code Review Report\n\n{body}"
            await self._create_file_commit(
                owner=owner,
                repo=repo,
                branch=review_branch,
                file_path=".github/AI_REVIEW.md",
                content=review_file_content,
                message="🤖 Add AI code review report"
            )
            
            # Now create the PR with the commit
            url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
            payload = {
                "title": title,
                "body": body,
                "head": review_branch,
                "base": base_branch,
                "draft": True
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
            logging.error(f"Unexpected error in create_review_pr: {str(e)}")
            raise

    def _format_review_as_pr_body(self, review_results: dict) -> str:
        """Format review results as PR description"""
        parts = ["# 🤖 AI Code Review Report\n"]
        parts.append("This PR documents AI-generated code review suggestions.\n")
        parts.append("> **Note:** This PR contains a review report file, not code changes.\n")
        
        review_list = review_results.get('review', [])
        
        if not review_list:
            parts.append("\n_No review results available._\n")
        else:
            for file_review in review_list:
                file_path = file_review.get('file', 'unknown')
                parts.append(f"\n## 📄 `{file_path}`\n")
                
                if file_review.get('error'):
                    parts.append(f"❌ **Error**: {file_review['error']}\n")
                    continue
                
                results = file_review.get('results', [])
                if not results:
                    parts.append("_No suggestions for this file._\n")
                    continue
                
                for idx, result in enumerate(results, 1):
                    if result.get('error'):
                        parts.append(f"\n### ⚠️ Chunk {idx} Error\n")
                        parts.append(f"```\n{result['error']}\n```\n")
                    elif result.get('suggestion'):
                        parts.append(f"\n### 💡 Suggestion {idx}\n")
                        parts.append(f"{result['suggestion']}\n")
                        
                        if result.get('highlighted_lines'):
                            lines = result['highlighted_lines']
                            parts.append(f"\n**Affected Lines:** {', '.join(map(str, lines))}\n")
                        
                        if result.get('chunk_preview'):
                            parts.append(f"\n**Code Preview:**\n```\n{result['chunk_preview'][:300]}\n```\n")
        
        parts.append("\n---\n")
        parts.append("*🤖 Generated by AI Code Review Assistant*\n")
        parts.append("*This is an automated review. Please verify all suggestions before implementing.*")
        
        return "\n".join(parts)