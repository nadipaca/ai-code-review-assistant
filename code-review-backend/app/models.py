from pydantic import BaseModel
from typing import List, Optional

class FileRef(BaseModel):
    owner: str
    repo: str
    path: str

class FileToReview(BaseModel):
    owner: str
    repo: str
    path: str

class ReviewRequest(BaseModel):
    files: List[FileToReview]

class PRPublishRequest(BaseModel):
    """Request to publish review to GitHub PR with inline comments"""
    owner: str
    repo: str
    pull_number: int
    suggestions: List[dict]

class ApprovedChange(BaseModel):
    file: str
    original_content: str
    modified_content: str
    suggestion: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None

class CreatePRWithChangesRequest(BaseModel):
    owner: str
    repo: str
    base_branch: Optional[str] = None
    branch_name: Optional[str] = None
    approved_changes: List[ApprovedChange]

class ApplySuggestionRequest(BaseModel):
    file_ref: FileRef
    suggestion: str
    line_start: int
    line_end: Optional[int] = None
