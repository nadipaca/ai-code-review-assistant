from pydantic import BaseModel
from typing import List, Optional

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
    suggestions: List[dict]  # [{"file": "...", "comment": "...", "line": 42, "highlighted_lines": [10,15]}]