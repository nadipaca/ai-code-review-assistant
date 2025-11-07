from pydantic import BaseModel
from typing import List

class FileToReview(BaseModel):
    owner: str
    repo: str
    path: str

class ReviewRequest(BaseModel):
    files: List[FileToReview]

class PRPublishRequest(BaseModel):
    """Request to publish review to GitHub PR"""
    owner: str
    repo: str
    pull_number: int
    suggestions: List[dict]  # [{"file": "...", "comment": "..."}]
