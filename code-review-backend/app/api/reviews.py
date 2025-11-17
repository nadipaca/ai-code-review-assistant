from fastapi import APIRouter, HTTPException, Cookie
from pydantic import BaseModel
from typing import List, Optional
import httpx
import logging
import re

from app.core.jwt_auth import verify_jwt
from app.services.github_client import GitHubClient
from app.services.rag_service import (
    chunk_java_file, 
    chunk_js_file, 
    chunk_python_file,
    chunk_typescript_file,
    chunk_generic_file
)
from app.services.llm_service import review_code_chunk_with_context
from app.api.auth import sessions
from app.services.pr_publisher import PRPublisher
from app.services.pr_creator import PRCreator
from app.services.code_applier import CodeApplier
from app.models import FileRef, ApplySuggestionRequest

router = APIRouter(prefix="/api/reviews", tags=["reviews"])

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

class CreatePRWithChangesRequest(BaseModel):
    owner: str
    repo: str
    branch_name: str
    base_branch: Optional[str] = None
    changes: List[dict]

def get_language_and_chunks(file_path: str, content: str):
    """
    Determine language from file extension and return appropriate chunks.
    
    Returns:
        tuple: (language: str, chunks: List[str])
    """
    if file_path.endswith('.java'):
        return 'java', chunk_java_file(content)
    elif file_path.endswith('.js'):
        return 'javascript', chunk_js_file(content)
    elif file_path.endswith('.jsx'):
        return 'javascript', chunk_js_file(content)
    elif file_path.endswith('.ts'):
        return 'typescript', chunk_typescript_file(content)
    elif file_path.endswith('.tsx'):
        return 'typescript', chunk_typescript_file(content)
    elif file_path.endswith('.py'):
        return 'python', chunk_python_file(content)
    else:
        return 'text', chunk_generic_file(content)

@router.post("/start")
async def start_review(
    request: ReviewRequest,
    access_token: Optional[str] = Cookie(None)
):
    """Start a code review for the specified files with PROJECT CONTEXT"""
    if not access_token:
        raise HTTPException(status_code=401, detail="Missing access token")
    
    payload = verify_jwt(access_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = str(payload["sub"])
    github_token = sessions.get(user_id, {}).get("github_token")
    if not github_token:
        raise HTTPException(status_code=401, detail="No GitHub token found")
    
    client = GitHubClient(github_token)
    
    review_results = {"review": []}
    
    project_context = {
        "files": {},
        "structure": []
    }
    
    SKIP_FILES = [
        'auth.py',      # Don't review auth logic
        'protected.py', # Don't review JWT dependencies
        'jwt_auth.py',  # Don't review JWT core
        '__init__.py',  # Skip init files
    ]
    
    for file_ref in request.files:
        filename = file_ref.path.split('/')[-1]

        if filename in SKIP_FILES:
            logging.info(f"Skipping infrastructure file: {file_ref.path}")
            continue

        try:
            content = await client.get_file_content(
                file_ref.owner, 
                file_ref.repo, 
                file_ref.path
            )
            project_context["files"][file_ref.path] = content
            project_context["structure"].append(file_ref.path)
            logging.info(f"Fetched {file_ref.path}: {len(content)} chars")
        except Exception as e:
            logging.error(f"Failed to fetch {file_ref.path}: {e}")
            review_results["review"].append({
                "file": file_ref.path,
                "error": f"Failed to fetch file: {str(e)}"
            })
    
    # ✅ Build project context summary
    context_summary = (
        f"**Project Structure:**\n"
        f"Files: {', '.join(project_context['structure'])}\n\n"
        f"**Total files in context:** {len(project_context['files'])}\n"
    )
    
    # ✅ Second pass: Review each file with full project context
    for file_path, content in project_context["files"].items():
        try:
            language, chunks = get_language_and_chunks(file_path, content)
            
            file_reviews = []
            for idx, chunk in enumerate(chunks):
                start_line = idx * 50 + 1  # Approximate line numbers
                
                review = await review_code_chunk_with_context(
                    chunk=chunk,
                    language=language,
                    start_line=start_line,
                    file_path=file_path,
                    project_context=context_summary,
                    full_file_content=content
                )
                
                # ✅ Only include reviews with actual findings
                if review.get("severity") in ["HIGH", "MEDIUM"]:
                    file_reviews.append({
                        "comment": review["comment"],
                        "line": start_line,
                        "highlighted_lines": review.get("lines"),
                        "has_code_block": review.get("has_code_block", False),
                        "severity": review["severity"]
                    })
                    logging.info(f"Found {review['severity']} issue in {file_path} at line {start_line}")
            
            if file_reviews:
                review_results["review"].append({
                    "file": file_path,
                    "suggestions": file_reviews
                })
                logging.info(f"✅ Completed review of {file_path}: {len(file_reviews)} findings")
            else:
                logging.info(f"✅ No issues found in {file_path}")
                
        except Exception as e:
            logging.exception(f"Error reviewing {file_path}: {e}")
            review_results["review"].append({
                "file": file_path,
                "error": f"Review failed: {str(e)}"
            })
    
    return review_results

@router.post("/publish")
async def publish_review(
    request: PublishRequest,
    access_token: Optional[str] = Cookie(None)
):
    """Publish review suggestions to a GitHub PR"""
    if not access_token:
        raise HTTPException(status_code=401, detail="Missing access token")
    
    payload = verify_jwt(access_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = str(payload["sub"])
    github_token = sessions.get(user_id, {}).get("github_token")
    if not github_token:
        raise HTTPException(status_code=401, detail="No GitHub token found")
    
    publisher = PRPublisher(github_token)
    
    try:
        result = await publisher.publish_review_to_pr(
            owner=request.owner,
            repo=request.repo,
            pull_number=request.pull_number,
            suggestions=request.suggestions
        )
        return {"ok": True, "review": result}
    except Exception as e:
        logging.exception(f"Failed to publish review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create-pr")
async def create_review_pr(
    request: CreatePRRequest,
    access_token: Optional[str] = Cookie(None)
):
    """Create a new PR with AI review suggestions (draft PR without actual changes)"""
    if not access_token:
        raise HTTPException(status_code=401, detail="Missing access token")
    
    payload = verify_jwt(access_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = str(payload["sub"])
    github_token = sessions.get(user_id, {}).get("github_token")
    if not github_token:
        raise HTTPException(status_code=401, detail="No GitHub token found")
    
    creator = PRCreator(github_token)
    
    try:
        pr_data = await creator.create_review_pr(
            owner=request.owner,
            repo=request.repo,
            base_branch=request.base_branch,
            review_results=request.review_results
        )
        return {"ok": True, "pr": pr_data}
    except Exception as e:
        logging.exception(f"Failed to create PR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create-pr-with-changes")
async def create_pr_with_changes(
    request: CreatePRWithChangesRequest,
    access_token: Optional[str] = Cookie(None)
):
    """Create a PR with actual code changes from approved suggestions"""
    if not access_token:
        raise HTTPException(status_code=401, detail="Missing access token")
    
    payload = verify_jwt(access_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = str(payload["sub"])
    github_token = sessions.get(user_id, {}).get("github_token")
    if not github_token:
        raise HTTPException(status_code=401, detail="No GitHub token found")
    
    creator = PRCreator(github_token)
    
    try:
        approved_changes = [
            {
                "file": change["file"],
                "original_content": change.get("original_content", ""),
                "modified_content": change.get("modified_content", ""),
                "suggestion": change.get("suggestion", "")
            }
            for change in request.approved_changes
        ]
        
        pr_data = await creator.create_review_pr_with_changes(
            owner=request.owner,
            repo=request.repo,
            base_branch=request.base_branch,
            branch_name=request.branch_name,  
            approved_changes=approved_changes
        )
        
        return {"ok": True, "pr": pr_data}
    except Exception as e:
        logging.exception(f"Failed to create PR with changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/apply-suggestion")
async def apply_suggestion(
    request: ApplySuggestionRequest,
    access_token: Optional[str] = Cookie(None)
):
    """Apply an AI suggestion to a file and return the diff"""
    if not access_token:
        raise HTTPException(status_code=401, detail="Missing access token")
    
    payload = verify_jwt(access_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = str(payload["sub"])
    github_token = sessions.get(user_id, {}).get("github_token")
    if not github_token:
        raise HTTPException(status_code=401, detail="No GitHub token found")
    
    client = GitHubClient(github_token)
    
    try:
        # Fetch original file content
        original_content = await client.get_file_content(
            request.file_ref.owner,
            request.file_ref.repo,
            request.file_ref.path
        )
        
        # Apply suggestion
        result = CodeApplier.smart_apply_suggestion(
            original_code=original_content,
            suggestion=request.suggestion,
            line_start=request.line_start,
            line_end=request.line_end,
            file_path=request.file_ref.path
        )
        
        return result
    except Exception as e:
        logging.exception(f"Failed to apply suggestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))