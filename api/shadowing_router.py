import os
import tempfile
from typing import Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)

from api.deps import get_current_profile_id
from schemas import (
    ShadowingAttemptResponse,
    ShadowingHistoryResponse,
    ShadowingStatsResponse,
)
from services.shadowing_service import (
    get_shadowing_attempt_detail,
    get_shadowing_stats,
    list_shadowing_attempts,
    process_shadowing_attempt,
)
from supabase.client import Client, get_supabase

router = APIRouter(prefix="/v1/shadowing", tags=["shadowing"])

# Supported audio file formats
SUPPORTED_AUDIO_TYPES = {
    "audio/mpeg",      # .mp3
    "audio/mp4",       # .m4a, .mp4
    "audio/wav",       # .wav
    "audio/webm",      # .webm
    "audio/ogg",       # .ogg
    "audio/flac",      # .flac
    "audio/x-m4a",     # .m4a (alternative MIME)
}

MAX_FILE_SIZE_MB = 50


@router.post("/attempt", response_model=ShadowingAttemptResponse)
async def shadowing_attempt(
    audio: UploadFile = File(
        ...,
        description="Audio file of the shadowing attempt. Supported formats: mp3, m4a, wav, webm, ogg, flac. Max 50MB."
    ),
    youtube_gem_id: str = Form(
        ...,
        description="ID of the YouTube video being shadowed."
    ),
    target_sentence: str = Form(
        ...,
        description="The exact sentence from the transcript being practiced."
    ),
    target_sentence_index: Optional[int] = Form(
        None,
        description="Index of the sentence in the transcript (for ordering)."
    ),
    duration_seconds: Optional[int] = Form(
        None,
        description="Duration of the recording in seconds (max 10 minutes)."
    ),
    supabase: Client = Depends(get_supabase),
    profile_id: str = Depends(get_current_profile_id),
) -> ShadowingAttemptResponse:
    """
    Upload and evaluate a shadowing attempt.

    This endpoint accepts an audio file of the user attempting to shadow
    (mimic) a sentence from a YouTube video. It transcribes the audio,
    compares it with the target sentence, and returns detailed feedback on
    how closely the user matched the native speaker.
    """
    # Validate file type
    content_type = audio.content_type or ""
    if content_type not in SUPPORTED_AUDIO_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {content_type}. "
                   f"Supported formats: mp3, m4a, wav, webm, ogg, flac"
        )

    # Validate file size (check by reading)
    file_content = await audio.read()
    file_size_mb = len(file_content) / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {file_size_mb:.1f}MB. Maximum size: {MAX_FILE_SIZE_MB}MB"
        )

    # Save to temporary file for processing
    file_ext = _get_extension_from_mime(content_type) or ".tmp"
    with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as tmp_file:
        tmp_file.write(file_content)
        tmp_path = tmp_file.name

    try:
        # Process the shadowing attempt (transcribe, compare, evaluate, save)
        raw = process_shadowing_attempt(
            audio_file_path=tmp_path,
            supabase=supabase,
            profile_id=profile_id,
            youtube_gem_id=youtube_gem_id,
            target_sentence=target_sentence,
            target_sentence_index=target_sentence_index,
            duration_seconds=duration_seconds,
        )
        return ShadowingAttemptResponse.model_validate(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        # Clean up temporary file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


@router.get("/history", response_model=ShadowingHistoryResponse)
def shadowing_history(
    youtube_gem_id: Optional[str] = Query(
        None,
        description="Optional: Filter by specific YouTube video ID."
    ),
    supabase: Client = Depends(get_supabase),
    profile_id: str = Depends(get_current_profile_id),
    page: int = Query(0, ge=0, description="First page is 0."),
    page_size: int = Query(20, ge=1, le=100),
) -> ShadowingHistoryResponse:
    """List paginated shadowing attempts for the current profile."""
    raw = list_shadowing_attempts(
        supabase, profile_id, youtube_gem_id=youtube_gem_id, page=page, page_size=page_size
    )
    return ShadowingHistoryResponse.model_validate(raw)


@router.get("/{attempt_id}", response_model=ShadowingAttemptResponse)
def shadowing_attempt_detail(
    attempt_id: UUID,
    supabase: Client = Depends(get_supabase),
    profile_id: str = Depends(get_current_profile_id),
) -> ShadowingAttemptResponse:
    """Get detailed evaluation for a specific shadowing attempt."""
    raw = get_shadowing_attempt_detail(supabase, profile_id, str(attempt_id))
    if raw is None:
        raise HTTPException(status_code=404, detail="Shadowing attempt not found")
    return ShadowingAttemptResponse.model_validate(raw)


@router.get("/stats/{youtube_gem_id}", response_model=ShadowingStatsResponse)
def shadowing_stats(
    youtube_gem_id: str,
    supabase: Client = Depends(get_supabase),
    profile_id: str = Depends(get_current_profile_id),
) -> ShadowingStatsResponse:
    """
    Get shadowing statistics for a specific YouTube video.

    Returns progress metrics including:
    - Total attempts made
    - Number of unique sentences practiced
    - Average and best scores
    - Per-sentence progress breakdown
    """
    raw = get_shadowing_stats(supabase, profile_id, youtube_gem_id)
    return ShadowingStatsResponse.model_validate(raw)


def _get_extension_from_mime(mime_type: str) -> Optional[str]:
    """Map MIME type to file extension."""
    mapping = {
        "audio/mpeg": ".mp3",
        "audio/mp4": ".m4a",
        "audio/wav": ".wav",
        "audio/webm": ".webm",
        "audio/ogg": ".ogg",
        "audio/flac": ".flac",
        "audio/x-m4a": ".m4a",
    }
    return mapping.get(mime_type)
