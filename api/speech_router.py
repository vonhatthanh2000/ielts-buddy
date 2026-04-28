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
    SpeechEvaluationResponse,
    SpeechHistoryResponse,
    SpeechUploadRequest,
)
from services.speech_service import (
    get_speech_recording_detail,
    list_speech_recordings,
    process_speech_recording,
)
from supabase.client import Client, get_supabase

router = APIRouter(prefix="/v1/speech", tags=["speech"])

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


@router.post("/evaluate", response_model=SpeechEvaluationResponse)
async def speech_evaluate(
    audio: UploadFile = File(
        ...,
        description="Audio file of the speech recording. Supported formats: mp3, m4a, wav, webm, ogg, flac. Max 50MB."
    ),
    youtube_gem_id: Optional[str] = Form(
        None,
        description="Optional: ID of a YouTube video this speech is practicing with."
    ),
    duration_seconds: Optional[int] = Form(
        None,
        description="Duration of the recording in seconds (max 10 minutes)."
    ),
    supabase: Client = Depends(get_supabase),
    profile_id: str = Depends(get_current_profile_id),
) -> SpeechEvaluationResponse:
    """
    Upload and evaluate a speech recording.

    This endpoint accepts an audio file, transcribes it using MLX Whisper,
    evaluates the spoken English using an AI agent, and returns detailed
    feedback including scores for pronunciation, fluency, grammar, and vocabulary.

    The audio file is stored in Supabase Storage for future reference.
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
        # Process the recording (transcribe, evaluate, save)
        raw = process_speech_recording(
            audio_file_path=tmp_path,
            supabase=supabase,
            profile_id=profile_id,
            youtube_gem_id=youtube_gem_id,
            duration_seconds=duration_seconds,
        )
        return SpeechEvaluationResponse.model_validate(raw)
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


@router.get("/history", response_model=SpeechHistoryResponse)
def speech_history(
    supabase: Client = Depends(get_supabase),
    profile_id: str = Depends(get_current_profile_id),
    page: int = Query(0, ge=0, description="First page is 0."),
    page_size: int = Query(20, ge=1, le=100),
) -> SpeechHistoryResponse:
    """List paginated speech recordings for the current profile."""
    raw = list_speech_recordings(
        supabase, profile_id, page=page, page_size=page_size
    )
    return SpeechHistoryResponse.model_validate(raw)


@router.get("/{recording_id}", response_model=SpeechEvaluationResponse)
def speech_recording_detail(
    recording_id: UUID,
    supabase: Client = Depends(get_supabase),
    profile_id: str = Depends(get_current_profile_id),
) -> SpeechEvaluationResponse:
    """Get detailed evaluation for a specific speech recording."""
    raw = get_speech_recording_detail(supabase, profile_id, str(recording_id))
    if raw is None:
        raise HTTPException(status_code=404, detail="Recording not found")
    return SpeechEvaluationResponse.model_validate(raw)


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
