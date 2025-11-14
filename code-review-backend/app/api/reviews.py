from fastapi import APIRouter, HTTPException, Cookie
from pydantic import BaseModel
from typing import List, Optional
import httpx
import logging

from app.core.jwt_auth import verify_jwt
from app.services.github_client import GitHubClient
from app.services.rag_service import chunk_java_file, chunk_js_file
from app.services.llm_service import review_code_chunk
from app.api.auth import sessions
from app.services.pr_publisher import PRPublisher
from app.services.pr_creator import PRCreator

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


class FileRef(BaseModel):
    owner: str
    repo: str
    path: str


class ReviewRequest(BaseModel):
    files: List[FileRef]


class PublishSuggestion(BaseModel):
    file: str
    comment: str
    line: Optional[int] = None
    highlighted_lines: Optional[List[int]] = None


class PublishRequest(BaseModel):
    owner: str
    repo: str
    pull_number: int
    suggestions: List[PublishSuggestion]


class CreatePRRequest(BaseModel):
    owner: str
    repo: str
    base_branch: Optional[str] = None
    review_results: dict


def count_lines_before_chunk(code: str, chunk: str) -> int:
    """
    Count how many lines come before the given chunk in the full code.
    This helps us provide absolute line numbers to the LLM.
    """
    try:
        chunk_start = code.index(chunk)
        lines_before = code[:chunk_start].count('\n')
        return lines_before + 1  # Line numbers are 1-indexed
    except ValueError:
        return 1  # Chunk not found, default to line 1


@router.post("/start")
async def start_review(request: ReviewRequest, access_token: Optional[str] = Cookie(None)):
    """Start a code review for the provided files.

    Expects JSON body: { "files": [{"owner": "org", "repo": "name", "path": "src/..."}, ...] }
    Cookie `access_token` must contain a valid JWT (HttpOnly)
    """
    payload = verify_jwt(access_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Authentication error")

    user_id = payload.get("sub")
    github_token = sessions.get(user_id, {}).get("github_token")
    if not github_token:
        raise HTTPException(status_code=401, detail="No GitHub token found")

    gh = GitHubClient(github_token)
    results = []

    # Limits & thresholds
    MAX_FILE_BYTES = 200 * 1024  # 200 KB per file
    MAX_CHUNKS = 50  # avoid sending too many requests to LLM

    for f in request.files:
        try:
            # Fetch file content from GitHub
            try:
                code = await gh.get_file_content(f.owner, f.repo, f.path)
            except httpx.HTTPStatusError as he:
                status = he.response.status_code
                logging.exception("GitHub API error fetching %s: %s", f.path, he)
                if status in (401, 403):
                    raise HTTPException(status_code=401, detail="GitHub authentication failed - please sign in again")
                results.append({"file": f.path, "error": f"GitHub error fetching file (status {status})"})
                continue

            # File size guard
            if isinstance(code, (bytes, bytearray)):
                size = len(code)
            else:
                size = len(code or "")
            if size > MAX_FILE_BYTES:
                results.append({"file": f.path, "error": f"File too large ({size} bytes). Max allowed is {MAX_FILE_BYTES} bytes."})
                continue

            # Chunk file
            if f.path.endswith(".java"):
                chunks = chunk_java_file(code)
            elif f.path.endswith(".js"):
                chunks = chunk_js_file(code)
            else:
                chunks = [code]

            if len(chunks) > MAX_CHUNKS:
                results.append({"file": f.path, "error": f"File would produce too many chunks ({len(chunks)}). Max allowed is {MAX_CHUNKS}."})
                continue

            file_results = []
            # Review each chunk; catch LLM errors per-chunk
            for chunk in chunks:
                try:
                    # Calculate starting line number for this chunk
                    start_line = count_lines_before_chunk(code, chunk)
                    
                    suggestion = await review_code_chunk(
                        chunk, 
                        language=("java" if f.path.endswith(".java") else "js"),
                        start_line=start_line
                    )
                    
                    file_results.append({
                        "chunk_preview": chunk[:200],
                        "suggestion": suggestion.get("comment") if isinstance(suggestion, dict) else str(suggestion),
                        "highlighted_lines": suggestion.get("lines") if isinstance(suggestion, dict) else None,
                        "start_line": start_line
                    })
                except Exception as le:
                    logging.exception("LLM error reviewing chunk for %s: %s", f.path, le)
                    file_results.append({"chunk_preview": chunk[:200], "error": f"LLM review failed: {str(le)}"})

            results.append({"file": f.path, "results": file_results})
        except HTTPException:
            raise
        except Exception as e:
            logging.exception("Unexpected error reviewing %s: %s", f.path, e)
            results.append({"file": f.path, "error": str(e)})

    logging.debug("Final results: %s", results)
    return {"review": results}


@router.post("/publish")
async def publish_review_to_pr(request: PublishRequest, access_token: Optional[str] = Cookie(None)):
    """Publish review suggestions to a GitHub Pull Request using the user's stored GitHub token."""
    payload = verify_jwt(access_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Authentication error")

    user_id = payload.get("sub")
    github_token = sessions.get(user_id, {}).get("github_token")
    if not github_token:
        raise HTTPException(status_code=401, detail="No GitHub token found")

    publisher = PRPublisher(github_token)
    try:
        resp = await publisher.publish_review_to_pr(
            request.owner,
            request.repo,
            request.pull_number,
            [s.dict() for s in request.suggestions]
        )
        return {"ok": True, "result": resp}
    except httpx.HTTPStatusError as he:
        status = he.response.status_code
        text = he.response.text
        raise HTTPException(status_code=502, detail=f"GitHub API error ({status}): {text}")
    except Exception as e:
        logging.exception("Error publishing review to PR: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create-pr")
async def create_pr_with_review(
    request: CreatePRRequest,
    access_token: Optional[str] = Cookie(None)
):
    """Create a new PR with review suggestions as documentation."""
    payload = verify_jwt(access_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    user_id = payload.get("sub")
    github_token = sessions.get(user_id, {}).get("github_token")
    if not github_token:
        raise HTTPException(status_code=401, detail="No GitHub token found")
    
    logging.info(f"Creating PR for {request.owner}/{request.repo}")
    
    creator = PRCreator(github_token)
    try:
        pr = await creator.create_review_pr(
            owner=request.owner,
            repo=request.repo,
            base_branch=request.base_branch,
            review_results=request.review_results
        )
        
        logging.info(f"Successfully created PR #{pr['number']} in {request.owner}/{request.repo}")
        
        return {
            "ok": True,
            "pr": {
                "number": pr['number'],
                "html_url": pr['html_url'],
                "title": pr['title'],
                "state": pr['state'],
                "draft": pr.get('draft', False)
            }
        }
    except httpx.HTTPStatusError as he:
        status_code = he.response.status_code
        error_text = he.response.text
        
        logging.error(f"GitHub API error {status_code}: {error_text}")
        
        # Handle specific GitHub API errors
        if status_code == 401:
            raise HTTPException(status_code=401, detail="GitHub authentication failed. Please sign in again.")
        elif status_code == 403:
            raise HTTPException(status_code=403, detail="Insufficient permissions to create PR. Check repository access.")
        elif status_code == 404:
            raise HTTPException(status_code=404, detail="Repository not found or not accessible.")
        elif status_code == 422:
            try:
                error_json = he.response.json()
                error_message = error_json.get('message', 'Validation failed')
            except:
                error_message = 'Invalid request to GitHub API'
            raise HTTPException(status_code=422, detail=f"GitHub validation error: {error_message}")
        else:
            raise HTTPException(status_code=502, detail=f"GitHub API error ({status_code}): {error_text}")
            
    except Exception as e:
        logging.exception("Error creating PR: %s", e)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")