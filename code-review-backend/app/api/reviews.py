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
from pydantic import BaseModel
from typing import List
from app.services.pr_publisher import PRPublisher
import httpx

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


class FileRef(BaseModel):
    owner: str
    repo: str
    path: str


class ReviewRequest(BaseModel):
    files: List[FileRef]


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
                # If token invalid/expired, return 401 so frontend can re-authenticate
                if status in (401, 403):
                    raise HTTPException(status_code=401, detail="GitHub authentication failed - please sign in again")
                # Other HTTP errors are reported per-file
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
                    suggestion = await review_code_chunk(chunk, language=("java" if f.path.endswith(".java") else "js"))
                    file_results.append({
                        "chunk_preview": chunk[:200],
                        "suggestion": suggestion.get("comment") if isinstance(suggestion, dict) else str(suggestion),
                        "highlighted_lines": suggestion.get("lines") if isinstance(suggestion, dict) else None
                    })
                except Exception as le:
                    logging.exception("LLM error reviewing chunk for %s: %s", f.path, le)
                    file_results.append({"chunk_preview": chunk[:200], "error": f"LLM review failed: {str(le)}"})

            results.append({"file": f.path, "results": file_results})
        except HTTPException:
            # re-raise authentication HTTPExceptions
            raise
        except Exception as e:
            logging.exception("Unexpected error reviewing %s: %s", f.path, e)
            results.append({"file": f.path, "error": str(e)})

    logging.debug("Final results: %s", results)
    return {"review": results}



class PublishSuggestion(BaseModel):
    file: str
    comment: str


class PublishRequest(BaseModel):
    owner: str
    repo: str
    pull_number: int
    suggestions: List[PublishSuggestion]


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
        # Bubble up GitHub API errors with reasonable message
        status = he.response.status_code
        text = he.response.text
        raise HTTPException(status_code=502, detail=f"GitHub API error ({status}): {text}")
    except Exception as e:
        logging.exception("Error publishing review to PR: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
 