import httpx
from typing import List, Optional
import logging

class PRPublisher:
    """Posts code review suggestions to GitHub PRs"""
    
    def __init__(self, github_token: str):
        self.github_token = github_token
        self.base_headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    async def get_pr_files(self, owner: str, repo: str, pull_number: int) -> List[dict]:
        """
        Fetch the list of files changed in a PR with their patch/diff information.
        This is needed to map line numbers to diff positions for inline comments.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/files"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.base_headers)
            response.raise_for_status()
            return response.json()
    
    def _find_diff_position(self, patch: str, line_number: int) -> Optional[int]:
        """
        Given a patch/diff string and a line number in the file,
        find the position in the diff where that line appears.
        
        GitHub requires the 'position' parameter for inline comments,
        which is the line number in the diff (not the absolute file line).
        
        Returns None if the line is not found in the diff.
        """
        if not patch:
            return None
        
        lines = patch.split('\n')
        current_line = 0
        diff_position = 0
        
        for line in lines:
            diff_position += 1
            
            # Lines starting with '+' are additions (new lines)
            if line.startswith('+') and not line.startswith('+++'):
                current_line += 1
                if current_line == line_number:
                    return diff_position
            # Lines starting with ' ' are context lines (unchanged)
            elif line.startswith(' '):
                current_line += 1
                if current_line == line_number:
                    return diff_position
        
        return None
    
    async def publish_review_to_pr(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        suggestions: List[dict]
    ) -> dict:
        """
        Post AI review with inline comments at specific lines in the PR.

        Expected suggestion format:
          {
            "file": "path/to/file.js",
            "comment": "Review comment text",
            "line": 42,  # optional: line number for inline comment
            "highlighted_lines": [10, 15, 20]  # optional: alternative to single line
          }

        If 'line' or 'highlighted_lines' is provided, attempts to post inline comment.
        Falls back to general review comment if inline fails.
        """
        # First, fetch PR files to get diff information
        try:
            pr_files = await self.get_pr_files(owner, repo, pull_number)
            file_map = {f['filename']: f for f in pr_files}
        except Exception as e:
            logging.warning(f"Could not fetch PR files for inline comments: {e}")
            file_map = {}
        
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/reviews"
        
        # Build inline comments array
        comments = []
        general_body_parts = []
        
        for suggestion in suggestions:
            fname = suggestion.get("file", "unknown")
            comment_text = suggestion.get("comment", "").strip()
            line = suggestion.get("line")
            highlighted_lines = suggestion.get("highlighted_lines", [])
            
            # Try to post inline comment if line info is available
            if (line or highlighted_lines) and fname in file_map:
                file_info = file_map[fname]
                patch = file_info.get('patch', '')
                
                # Use first highlighted line if available, otherwise use 'line'
                target_line = highlighted_lines[0] if highlighted_lines else line
                
                if target_line:
                    diff_position = self._find_diff_position(patch, target_line)
                    
                    if diff_position:
                        # Create inline comment
                        comments.append({
                            "path": fname,
                            "position": diff_position,
                            "body": f"🤖 **AI Review**\n\n{comment_text}"
                        })
                        logging.info(f"Added inline comment for {fname} at line {target_line} (diff position {diff_position})")
                    else:
                        # Line not in diff, add to general comment
                        general_body_parts.append(f"## File: `{fname}` (Line {target_line})\n\n{comment_text}\n")
                        logging.warning(f"Line {target_line} not found in diff for {fname}, adding to general comment")
                else:
                    general_body_parts.append(f"## File: `{fname}`\n\n{comment_text}\n")
            else:
                # No line info or file not in PR, add to general comment
                general_body_parts.append(f"## File: `{fname}`\n\n{comment_text}\n")
        
        # Build general review body
        body = "# 🤖 AI Code Review\n\n"
        if general_body_parts:
            body += "\n".join(general_body_parts)
        else:
            body += "_All suggestions posted as inline comments._\n"
        
        body += "\n---\n*Generated by AI Code Review Assistant*"
        
        payload = {
            "body": body,
            "event": "COMMENT",
            "comments": comments  # Array of inline comments
        }
        
        # Post review with inline comments
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=payload,
                headers=self.base_headers
            )
            response.raise_for_status()
            return response.json()