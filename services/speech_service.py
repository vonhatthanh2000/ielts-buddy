import json
import logging
import os
from typing import Optional
from uuid import uuid4

from supabase.client import Client

from agents.speech_evaluation_agent import speech_evaluation_agent

logger = logging.getLogger(__name__)


def process_speech_recording(
    audio_file_path: str,
    supabase: Client,
    profile_id: str,
    youtube_gem_id: Optional[str] = None,
    duration_seconds: Optional[int] = None,
) -> dict:
    """
    Full pipeline: transcribe audio -> evaluate with AI -> save -> return result.

    Args:
        audio_file_path: Path to the uploaded audio file
        supabase: Supabase client for database operations
        profile_id: ID of the user's profile
        youtube_gem_id: Optional linked YouTube analysis ID
        duration_seconds: Optional duration of the recording

    Returns:
        Dictionary containing the saved speech recording with evaluation
    """
    # Step 1: Transcribe the audio using MLX Whisper
    transcript = _transcribe_audio(audio_file_path)
    if not transcript:
        raise ValueError("Could not transcribe audio. Ensure the audio file is valid.")

    # Step 2: Upload audio to Supabase Storage
    audio_url = _upload_audio_to_storage(audio_file_path, supabase, profile_id)

    # Step 3: Run AI evaluation
    raw_evaluation = _run_evaluation_agent(transcript)
    evaluation_data = _parse_evaluation_output(raw_evaluation)

    # Step 4: Save to database
    result = _save_recording(
        audio_url=audio_url,
        transcript=transcript,
        evaluation=evaluation_data,
        supabase=supabase,
        profile_id=profile_id,
        youtube_gem_id=youtube_gem_id,
        duration_seconds=duration_seconds,
    )

    return result


def _transcribe_audio(audio_path: str) -> Optional[str]:
    """
    Transcribe audio file using MLX Whisper.

    Returns the transcribed text or None if transcription fails.
    """
    try:
        import mlx_whisper
    except ImportError as e:
        logger.error(f"mlx_whisper not available: {e}")
        return None

    if not os.path.exists(audio_path):
        logger.error(f"Audio file not found: {audio_path}")
        return None

    try:
        logger.info(f"Starting MLX transcription for {audio_path}")
        result = mlx_whisper.transcribe(
            audio_path,
            path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
            verbose=False,
        )
        transcript = result.get("text", "").strip()
        logger.info(f"Transcription successful, got {len(transcript)} characters")
        return transcript
    except Exception as e:
        logger.error(f"MLX transcription failed: {type(e).__name__}: {e}")
        return None


def _upload_audio_to_storage(
    audio_path: str, supabase: Client, profile_id: str
) -> str:
    """
    Upload audio file to Supabase Storage and return the public URL.

    The file is stored in the bucket configured by SPEECH_RECORDINGS_BUCKET
    env var (default: 'speech-recordings') under the profile_id folder.
    """
    bucket_name = os.getenv("SPEECH_RECORDINGS_BUCKET", "speech-recordings")
    file_ext = os.path.splitext(audio_path)[1] or ".m4a"
    storage_path = f"{profile_id}/{uuid4()}{file_ext}"

    try:
        # Check if bucket exists, create if not (this would typically be done in migrations)
        # For now, assume the bucket exists or handle error appropriately
        with open(audio_path, "rb") as f:
            file_bytes = f.read()

        # Upload to Supabase Storage
        result = supabase.storage.from_(bucket_name).upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": _get_content_type(file_ext)},
        )

        if hasattr(result, "error") and result.error:
            raise RuntimeError(f"Storage upload failed: {result.error}")

        # Get public URL
        public_url = supabase.storage.from_(bucket_name).get_public_url(storage_path)
        logger.info(f"Audio uploaded successfully: {public_url}")
        return public_url

    except Exception as e:
        logger.error(f"Failed to upload audio: {e}")
        # Fallback: store a placeholder URL
        return f"file://{audio_path}"


def _get_content_type(ext: str) -> str:
    """Get MIME content type for audio file extension."""
    mapping = {
        ".m4a": "audio/mp4",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".webm": "audio/webm",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
    }
    return mapping.get(ext.lower(), "audio/mpeg")


def _run_evaluation_agent(transcript: str) -> str:
    """Run the speech evaluation agent with the transcript."""
    # Truncate if too long (agent has token limits)
    max_chars = 15000
    if len(transcript) > max_chars:
        transcript = transcript[:max_chars] + "... [transcript truncated due to length]"

    prompt = f"Evaluate this spoken English transcript:\n\n{transcript}"
    response = speech_evaluation_agent.run(prompt)
    return response.content if hasattr(response, "content") else str(response)


def _parse_evaluation_output(raw: str) -> dict:
    """Parse agent output into structured evaluation data."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse agent output as JSON: {raw[:200]}...")
        return {
            "overall_score": 0,
            "pronunciation_score": 0,
            "fluency_score": 0,
            "grammar_score": 0,
            "vocabulary_score": 0,
            "strengths": [],
            "improvements": [],
            "detailed_feedback": "Could not parse evaluation. Please try again.",
            "learning_tip": "Try speaking more clearly and at a moderate pace.",
        }

    # Ensure all expected fields exist with safe defaults
    return {
        "overall_score": _clamp_score(data.get("overall_score")),
        "pronunciation_score": _clamp_score(data.get("pronunciation_score")),
        "fluency_score": _clamp_score(data.get("fluency_score")),
        "grammar_score": _clamp_score(data.get("grammar_score")),
        "vocabulary_score": _clamp_score(data.get("vocabulary_score")),
        "strengths": data.get("strengths", []),
        "improvements": data.get("improvements", []),
        "detailed_feedback": data.get("detailed_feedback", "No detailed feedback available."),
        "learning_tip": data.get("learning_tip", "Keep practicing to improve your speaking skills."),
    }


def _clamp_score(value) -> int:
    """Clamp a score value to 0-100 range."""
    try:
        score = int(value) if value is not None else 0
        return max(0, min(100, score))
    except (ValueError, TypeError):
        return 0


def _save_recording(
    audio_url: str,
    transcript: str,
    evaluation: dict,
    supabase: Client,
    profile_id: str,
    youtube_gem_id: Optional[str] = None,
    duration_seconds: Optional[int] = None,
) -> dict:
    """Save the speech recording and evaluation to the database."""
    row = {
        "profile_id": profile_id,
        "audio_url": audio_url,
        "audio_duration_seconds": duration_seconds,
        "transcript": transcript,
        "overall_score": evaluation["overall_score"],
        "pronunciation_score": evaluation["pronunciation_score"],
        "fluency_score": evaluation["fluency_score"],
        "grammar_score": evaluation["grammar_score"],
        "vocabulary_score": evaluation["vocabulary_score"],
        "strengths": evaluation["strengths"],
        "improvements": evaluation["improvements"],
        "detailed_feedback": evaluation["detailed_feedback"],
        "learning_tip": evaluation["learning_tip"],
        "youtube_gem_id": youtube_gem_id,
    }

    res = supabase.table("speech_recordings").insert(row).execute()
    if not res.data:
        raise RuntimeError("Failed to insert speech recording")

    saved = res.data[0]

    # Return in schema-compatible format
    return {
        "id": saved["id"],
        "created_at": saved["created_at"],
        "audio_url": saved["audio_url"],
        "audio_duration_seconds": saved["audio_duration_seconds"],
        "transcript": saved["transcript"],
        "youtube_gem_id": saved["youtube_gem_id"],
        "evaluation": {
            "overall_score": saved["overall_score"],
            "pronunciation_score": saved["pronunciation_score"],
            "fluency_score": saved["fluency_score"],
            "grammar_score": saved["grammar_score"],
            "vocabulary_score": saved["vocabulary_score"],
            "strengths": saved["strengths"],
            "improvements": saved["improvements"],
            "detailed_feedback": saved["detailed_feedback"],
            "learning_tip": saved["learning_tip"],
        },
    }


def list_speech_recordings(
    supabase: Client,
    profile_id: str,
    *,
    page: int = 0,
    page_size: int = 20,
) -> dict:
    """Paginated speech recordings for a profile, newest first."""
    page = max(0, page)
    page_size = min(max(1, page_size), 100)
    offset = page * page_size
    end = offset + page_size - 1

    res = (
        supabase.table("speech_recordings")
        .select(
            "id, created_at, audio_url, audio_duration_seconds, overall_score, transcript",
            count="exact",
        )
        .eq("profile_id", profile_id)
        .order("created_at", desc=True)
        .range(offset, end)
        .execute()
    )

    rows = res.data or []
    total = int(res.count) if res.count is not None else len(rows)

    # Transform rows to match history item schema
    items = []
    for row in rows:
        transcript = row.get("transcript", "")
        items.append({
            "id": row.get("id"),
            "created_at": row.get("created_at"),
            "audio_url": row.get("audio_url"),
            "audio_duration_seconds": row.get("audio_duration_seconds"),
            "overall_score": row.get("overall_score"),
            "transcript_preview": transcript[:100] + ("..." if len(transcript) > 100 else ""),
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_speech_recording_detail(
    supabase: Client,
    profile_id: str,
    recording_id: str,
) -> Optional[dict]:
    """Load one speech recording with full evaluation data."""
    res = (
        supabase.table("speech_recordings")
        .select(
            "id, created_at, audio_url, audio_duration_seconds, transcript, "
            "overall_score, pronunciation_score, fluency_score, grammar_score, vocabulary_score, "
            "strengths, improvements, detailed_feedback, learning_tip, youtube_gem_id"
        )
        .eq("id", recording_id)
        .eq("profile_id", profile_id)
        .limit(1)
        .execute()
    )

    if not res.data:
        return None

    row = res.data[0]

    return {
        "id": row.get("id"),
        "created_at": row.get("created_at"),
        "audio_url": row.get("audio_url"),
        "audio_duration_seconds": row.get("audio_duration_seconds"),
        "transcript": row.get("transcript"),
        "youtube_gem_id": row.get("youtube_gem_id"),
        "evaluation": {
            "overall_score": row.get("overall_score"),
            "pronunciation_score": row.get("pronunciation_score"),
            "fluency_score": row.get("fluency_score"),
            "grammar_score": row.get("grammar_score"),
            "vocabulary_score": row.get("vocabulary_score"),
            "strengths": row.get("strengths", []),
            "improvements": row.get("improvements", []),
            "detailed_feedback": row.get("detailed_feedback"),
            "learning_tip": row.get("learning_tip"),
        },
    }
