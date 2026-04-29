"""
Shared Pydantic models for HTTP, services, and any other callers.

Import from here: ``from schemas import SentenceCorrectResponse`` or use
submodules ``schemas.sentence``, ``schemas.user``.
"""

from schemas.auth import LoginRequest, LoginResponse, RegisterRequest, SwitchProfileRequest
from schemas.profile import (
    ProfileCreate,
    ProfileListResponse,
    ProfileResponse,
    ProfileUpdate,
)
from schemas.sentence import (
    BatchAnalysisListResponse,
    BatchAnalysisRequest,
    BatchAnalysisResponse,
    ImprovementItem,
    SentenceCorrectResponse,
    SentenceHistoryItem,
    SentenceHistoryResponse,
    SentenceMistakeItem,
    SentenceRequest,
    StructuredBatchAnalysis,
    StructuredBatchAnalysisListItem,
    StructuredBatchAnalysisListResponse,
    StructuredBatchAnalysisRequest,
    StructuredBatchAnalysisResponse,
)
from schemas.user import UserResponse
from schemas.speech import (
    ImprovementItem as SpeechImprovementItem,
    SpeechEvaluationData,
    SpeechEvaluationResponse,
    SpeechHistoryItem,
    SpeechHistoryResponse,
    SpeechUploadRequest,
    StrengthItem,
)
from schemas.shadowing import (
    ShadowingAttemptRequest,
    ShadowingAttemptResponse,
    ShadowingEvaluationData,
    ShadowingHistoryItem,
    ShadowingHistoryResponse,
    ShadowingStatsResponse,
    WordDifference,
)
from schemas.youtube import (
    YoutubeAnalysisHistoryResponse,
    YoutubeAnalysisRequest,
    YoutubeAnalysisResponse,
)

__all__ = [
    "BatchAnalysisListResponse",
    "BatchAnalysisRequest",
    "BatchAnalysisResponse",
    "ImprovementItem",
    "LoginRequest",
    "LoginResponse",
    "ProfileCreate",
    "ProfileListResponse",
    "ProfileResponse",
    "ProfileUpdate",
    "RegisterRequest",
    "SentenceCorrectResponse",
    "SentenceHistoryItem",
    "SentenceHistoryResponse",
    "SentenceMistakeItem",
    "SentenceRequest",
    "StructuredBatchAnalysis",
    "StructuredBatchAnalysisListItem",
    "StructuredBatchAnalysisListResponse",
    "StructuredBatchAnalysisRequest",
    "StructuredBatchAnalysisResponse",
    "ShadowingAttemptRequest",
    "ShadowingAttemptResponse",
    "ShadowingEvaluationData",
    "ShadowingHistoryItem",
    "ShadowingHistoryResponse",
    "ShadowingStatsResponse",
    "SpeechEvaluationData",
    "SpeechEvaluationResponse",
    "SpeechHistoryItem",
    "SpeechHistoryResponse",
    "SpeechImprovementItem",
    "SpeechUploadRequest",
    "StrengthItem",
    "SwitchProfileRequest",
    "UserResponse",
    "WordDifference",
    "YoutubeAnalysisHistoryResponse",
    "YoutubeAnalysisRequest",
    "YoutubeAnalysisResponse",
]
