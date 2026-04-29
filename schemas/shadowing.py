"""Shadowing practice domain models for mimicking YouTube video sentences."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class WordDifference(BaseModel):
    """One word-level difference between target and user speech."""

    model_config = ConfigDict(extra="ignore")

    expected: str = Field(..., description="The word that should have been said.")
    actual: str = Field(..., description="What the user actually said, or [missing] if omitted.")


class ShadowingEvaluationData(BaseModel):
    """Simple shadowing evaluation results from AI agent."""

    model_config = ConfigDict(extra="ignore")

    similarity_score: int = Field(..., ge=0, le=100, description="Overall similarity score 0-100.")
    differences: List[WordDifference] = Field(default_factory=list, description="List of word differences found.")
    feedback: str = Field(..., description="Brief feedback on the attempt.")


class ShadowingAttemptRequest(BaseModel):
    """Request to upload and evaluate a shadowing attempt.

    Note: The actual audio file is uploaded via multipart/form-data.
    This model represents the metadata fields.
    """

    youtube_gem_id: str = Field(
        ...,
        description="ID of the YouTube video being shadowed.",
    )
    target_sentence: str = Field(
        ...,
        description="The exact sentence from the transcript being practiced.",
    )
    target_sentence_index: Optional[int] = Field(
        None,
        description="Index of the sentence in the transcript (for ordering).",
    )
    duration_seconds: Optional[int] = Field(
        None,
        ge=1,
        le=600,
        description="Duration of the recording in seconds (max 10 minutes).",
    )


class ShadowingAttemptResponse(BaseModel):
    """Response containing shadowing attempt and evaluation results."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="Composite ID: profile_id:youtube_gem_id:target_sentence_index")
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    youtube_gem_id: str = Field(..., description="ID of the YouTube video being shadowed.")
    target_sentence: str = Field(..., description="The target sentence practiced.")
    target_sentence_index: int = Field(..., description="Index of the sentence in the transcript.")
    audio_url: str = Field(..., description="URL to the stored audio file.")
    audio_duration_seconds: Optional[int] = None
    user_transcript: str = Field(..., description="Transcribed text from user's speech.")
    evaluation: ShadowingEvaluationData = Field(..., description="AI shadowing evaluation results.")


class ShadowingHistoryItem(BaseModel):
    """One saved shadowing attempt (list view, without full evaluation)."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="Composite ID: profile_id:youtube_gem_id:target_sentence_index")
    created_at: Optional[str] = None
    youtube_gem_id: str
    target_sentence: str = Field(..., description="The target sentence practiced.")
    target_sentence_index: int = Field(..., description="Index of the sentence in the transcript.")
    audio_url: str
    audio_duration_seconds: Optional[int] = None
    similarity_score: Optional[int] = None


class ShadowingHistoryResponse(BaseModel):
    """Paginated list of shadowing attempts."""

    items: List[ShadowingHistoryItem]
    total: int
    page: int = Field(..., description="0-based page index echoed from the request.")
    page_size: int


class ShadowingStatsResponse(BaseModel):
    """Shadowing statistics for a specific YouTube video."""

    youtube_gem_id: str
    total_attempts: int
    sentences_practiced: int
    average_similarity_score: Optional[float] = None
    best_attempt_id: Optional[str] = None
    best_similarity_score: Optional[int] = None
    progress_by_sentence: List[dict] = Field(
        default_factory=list,
        description="Array of {sentence_index, attempts, best_score}",
    )
