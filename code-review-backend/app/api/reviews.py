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
    chunk_generic_file,
)
from app.services.llm_service import review_code_chunk_with_context, parse_individual_issues
from app.api.auth import sessions
from app.services.pr_publisher import PRPublisher
from app.services.pr_creator import PRCreator
from app.services.code_applier import CodeApplier
from app.models import FileRef, ApplySuggestionRequest, ReviewRequest, CreatePRWithChangesRequest

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


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
    branch_name: Optional[str] = None
    title: Optional[str] = None
    body: Optional[str] = None


def get_language_and_chunks(file_path: str, content: str):
    """
    Determine language from file extension and return appropriate chunks.

    Returns:
        tuple: (language: str, chunks: List[str])
    """
    if file_path.endswith(".java"):
        return "java", chunk_java_file(content)
    elif file_path.endswith(".js"):
        return "javascript", chunk_js_file(content)
    elif file_path.endswith(".jsx"):
        return "javascript", chunk_js_file(content)
    elif file_path.endswith(".ts"):
        return "typescript", chunk_typescript_file(content)
    elif file_path.endswith(".tsx"):
        return "typescript", chunk_typescript_file(content)
    elif file_path.endswith(".py"):
        return "python", chunk_python_file(content)
    else:
        return "text", chunk_generic_file(content)


@router.post("/start")
async def start_review(
    request: ReviewRequest,
    access_token: Optional[str] = Cookie(None),
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

    # First pass: Fetch all file contents to build project context
    project_context = {
        "files": {},
        "structure": [],
    }

    # Updated skip list - only skip infrastructure files, NOT test files
    SKIP_FILES = [
        "auth.py",
        "protected.py",
        "jwt_auth.py",
        "__init__.py",
    ]

    for file_ref in request.files:
        filename = file_ref.path.split("/")[-1]

        if filename in SKIP_FILES:
            logging.info(f"Skipping infrastructure file: {file_ref.path}")
            continue

        try:
            content = await client.get_file_content(
                file_ref.owner,
                file_ref.repo,
                file_ref.path,
            )
            project_context["files"][file_ref.path] = content
            project_context["structure"].append(file_ref.path)
            logging.info(f"Fetched {file_ref.path}: {len(content)} chars")
        except Exception as e:
            logging.error(f"Failed to fetch {file_ref.path}: {e}")
            review_results["review"].append(
                {
                    "file": file_ref.path,
                    "error": f"Failed to fetch file: {str(e)}",
                }
            )

    # Build context summary
    context_summary = (
        f"Project structure: {', '.join(project_context['structure'])}\n"
    )
    context_summary += f"Total files in context: {len(project_context['files'])}\n"

    # Second pass: Review each file with full project context
    for file_path, content in project_context["files"].items():
        try:
            language, chunks = get_language_and_chunks(file_path, content)

            file_reviews: List[dict] = []

            for i, chunk in enumerate(chunks):
                # NOTE: assumes each chunk is <= 1000 lines
                start_line = i * 1000 + 1

                review = await review_code_chunk_with_context(
                    chunk=chunk,
                    language=language,
                    start_line=start_line,
                    file_path=file_path,
                    project_context=context_summary,
                    full_file_content=content,
                )

                # Only include reviews with actual findings
                if review.get("severity") in ["HIGH", "MEDIUM"] and review.get("comment"):
                    # Parse individual issues from the LLM response
                    individual_issues = parse_individual_issues(
                        llm_response=review["comment"],
                        original_code=content,
                        file_path=file_path,
                    )

                    if individual_issues:
                        # Add each parsed issue as a separate entry
                        for issue in individual_issues:
                            file_reviews.append(
                                {
                                    "comment": issue["comment"],
                                    "diff": issue["diff"],
                                    "highlighted_lines": issue["highlighted_lines"],
                                    "severity": issue["severity"],
                                    "has_code_block": issue["has_code_block"],
                                }
                            )
                            logging.info(
                                f"Found {issue['severity']} issue in {file_path}"
                            )
                    else:
                        # Fallback: if parsing fails but chunk says HIGH/MEDIUM, keep the chunk as a single issue
                        file_reviews.append(
                            {
                                "comment": review["comment"],
                                "diff": "",
                                "highlighted_lines": review.get("lines") or [],
                                "severity": review["severity"],
                                "has_code_block": review.get("has_code_block", False),
                            }
                        )
                        logging.info(
                            f"Fallback: treated entire chunk as single {review['severity']} issue in {file_path}"
                        )

            if file_reviews:
                review_results["review"].append(
                    {
                        "file": file_path,
                        "original_content": content,
                        "results": file_reviews,
                    }
                )
                logging.info(
                    f"✅ Completed review of {file_path}: {len(file_reviews)} findings"
                )
            else:
                logging.info(f"✅ No issues found in {file_path}")

        except Exception as e:
            logging.exception(f"Error reviewing {file_path}: {e}")
            review_results["review"].append(
                {
                    "file": file_path,
                    "error": f"Review failed: {str(e)}",
                }
            )

    return review_results


@router.post("/publish")
async def publish_review(
    request: PublishRequest,
    access_token: Optional[str] = Cookie(None),
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
            suggestions=[s.dict() for s in request.suggestions],
        )
        return {"ok": True, "review": result}
    except Exception as e:
        logging.exception(f"Failed to publish review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create-review-pr")
async def create_review_pr(
    request: CreatePRRequest,
    access_token: Optional[str] = Cookie(None),
):
    """Create a new PR with review comments (no code changes)"""
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
        pr_data = await creator.create_review_pr_with_changes(
            owner=request.owner,
            repo=request.repo,
            branch_name=request.branch_name,
            title=request.title,
            body=request.body,
            approved_changes=[],
        )
        return {"ok": True, "pr": pr_data}
    except Exception as e:
        logging.exception(f"Failed to create review PR: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create-pr-with-changes")
async def create_pr_with_changes(
    request: CreatePRWithChangesRequest,
    access_token: Optional[str] = Cookie(None),
):
    """Create a PR with actual code changes from approved suggestions"""
    logging.info(f"🔍 create_pr_with_changes called")
    logging.info(f"  - request.owner: {request.owner}")
    logging.info(f"  - request.repo: {request.repo}")
    logging.info(f"  - request.branch_name: {request.branch_name}")
    logging.info(f"  - request.approved_changes length: {len(request.approved_changes) if request.approved_changes else 0}")
    
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
                "file": change.file,
                "original_content": change.original_content,
                "modified_content": change.modified_content,
                "suggestion": change.suggestion,
            }
            for change in request.approved_changes
        ]
        
        logging.info(f"📊 Processed {len(approved_changes)} approved changes")
        for idx, change in enumerate(approved_changes):
            logging.info(f"  Change {idx+1}: file={change['file']}, has_content={bool(change['modified_content'])}")

        pr_data = await creator.create_review_pr_with_changes(
            owner=request.owner,
            repo=request.repo,
            base_branch=request.base_branch,
            branch_name=request.branch_name,
            approved_changes=approved_changes,
        )

        return {"ok": True, "pr": pr_data}
    except Exception as e:
        logging.exception(f"Failed to create PR with changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/apply-suggestion")
async def apply_suggestion(
    request: ApplySuggestionRequest,
    access_token: Optional[str] = Cookie(None),
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
        # Determine base content: use current_content if provided (for cumulative changes),
        # otherwise fetch from GitHub
        if request.current_content:
            base_content = request.current_content
        else:
            base_content = await client.get_file_content(
                request.file_ref.owner,
                request.file_ref.repo,
                request.file_ref.path,
            )

        # Strategy 1: Use pre-computed diff if available (most reliable)
        if request.diff:
            # Extract fixed lines from diff (lines starting with +)
            fixed_lines = []
            for line in request.diff.split('\n'):
                if line.startswith('+') and not line.startswith('+++'):
                    # Remove the '+' prefix
                    fixed_lines.append(line[1:])
            
            if fixed_lines:
                fixed_code = '\n'.join(fixed_lines)
                
                # INTELLIGENT RANGE DETECTION
                # Check if the fixed code represents a complete function/class block
                # and expand the line range accordingly
                detected_start, detected_end = CodeApplier.detect_code_block_range(
                    original_code=base_content,
                    fix_code=fixed_code,
                    suggested_start=request.line_start,
                    suggested_end=request.line_end or request.line_start,
                    file_path=request.file_ref.path
                )
                
                # Apply the fix using the detected range
                base_lines = base_content.split('\n')
                start_idx = max(0, detected_start - 1)
                end_idx = min(len(base_lines), detected_end)
                
                # Replace the lines
                new_lines = base_lines[:start_idx] + fixed_lines + base_lines[end_idx:]
                modified_code = '\n'.join(new_lines)
                
                # Generate new diff
                diff = CodeApplier.generate_diff(
                    base_content,
                    modified_code,
                    request.file_ref.path,
                    context_lines=5
                )
                
                return {
                    "original_content": base_content,
                    "modified_code": modified_code,
                    "diff": diff,
                    "applied": True,
                    "changes": [{
                        "lines": [detected_start, detected_end],
                        "code": fixed_code,
                        "description": "Applied fix from diff with intelligent range detection",
                        "language": "javascript"
                    }],
                    "error": None,
                }

        # Strategy 2: Fallback to CodeApplier (legacy behavior)
        result = CodeApplier.smart_apply_suggestion(
            original_code=base_content,
            suggestion=request.suggestion,
            line_start=request.line_start,
            line_end=request.line_end,
            file_path=request.file_ref.path,
        )

        # Enhanced response with original content and diff
        return {
            "original_content": base_content,
            "modified_code": result["modified_code"],
            "diff": result["diff"],
            "applied": result["applied"],
            "changes": result["changes"],
            "error": result.get("error"),
        }
    except Exception as e:
        logging.exception(f"Failed to apply suggestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))
