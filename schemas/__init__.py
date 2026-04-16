"""
Shared Pydantic models for HTTP, services, and any other callers.

Import from here: ``from schemas import SentenceCorrectResponse`` or use
submodules ``schemas.sentence``, ``schemas.user``.
"""

from schemas.auth import LoginRequest, LoginResponse, RegisterRequest
from schemas.sentence import (
    BatchAnalysisRequest,
    BatchAnalysisResponse,
    ImprovementItem,
    SentenceCorrectResponse,
    SentenceMistakeItem,
    SentenceRequest,
)
from schemas.user import UserResponse

__all__ = [
    "BatchAnalysisRequest",
    "BatchAnalysisResponse",
    "ImprovementItem",
    "LoginRequest",
    "LoginResponse",
    "RegisterRequest",
    "SentenceCorrectResponse",
    "SentenceMistakeItem",
    "SentenceRequest",
    "UserResponse",
]
