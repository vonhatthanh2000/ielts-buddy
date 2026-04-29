import json
import logging
import os
from typing import Optional
from uuid import uuid4

from supabase.client import Client

from agents.shadowing_evaluation_agent import shadowing_evaluation_agent

logger = logging.getLogger(__name__)

# Use same bucket as speech recordings
SHADOWING_BUCKET = os.getenv("SHADOWING_RECORDINGS_BUCKET", "speech-recordings")


def process_shadowing_attempt(
    audio_file_path: str,
    supabase: Client,
    profile_id: str,
    youtube_gem_id: str,
    target_sentence: str,
    target_sentence_index: Optional[int] = None,
    duration_seconds: Optional[int] = None,
) -> dict:
    """
    Full pipeline: transcribe audio -> compare with target -> evaluate -> save -> return result.

    Args:
        audio_file_path: Path to the uploaded audio file
        supabase: Supabase client for database operations
        profile_id: ID of the user's profile
        youtube_gem_id: ID of the YouTube video being shadowed
        target_sentence: The exact sentence from the transcript being practiced
        target_sentence_index: Optional index of the sentence in the transcript
        duration_seconds: Optional duration of the recording

    Returns:
        Dictionary containing the saved shadowing attempt with evaluation
    """
    # Step 1: Transcribe the user's audio using MLX Whisper
    user_transcript = _transcribe_audio(audio_file_path)
    if user_transcript is None:
        user_transcript = ""  # Allow empty transcript for failed attempts

    # Step 2: Upload audio to Supabase Storage
    audio_url = _upload_audio_to_storage(audio_file_path, supabase, profile_id)

    # Step 3: Run AI shadowing evaluation (compare user vs target)
    raw_evaluation = _run_shadowing_agent(target_sentence, user_transcript)
    evaluation_data = _parse_shadowing_output(raw_evaluation)

    # Step 4: Save to database
    result = _save_shadowing_attempt(
        audio_url=audio_url,
        user_transcript=user_transcript,
        target_sentence=target_sentence,
        target_sentence_index=target_sentence_index,
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
        logger.info(f"Starting MLX transcription for shadowing: {audio_path}")
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

    The file is stored in the shadowing bucket under the profile_id/shadowing folder.
    """
    file_ext = os.path.splitext(audio_path)[1] or ".m4a"
    storage_path = f"{profile_id}/shadowing/{uuid4()}{file_ext}"

    try:
        with open(audio_path, "rb") as f:
            file_bytes = f.read()

        # Upload to Supabase Storage
        result = supabase.storage.from_(SHADOWING_BUCKET).upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": _get_content_type(file_ext)},
        )

        if hasattr(result, "error") and result.error:
            raise RuntimeError(f"Storage upload failed: {result.error}")

        # Get public URL
        public_url = supabase.storage.from_(SHADOWING_BUCKET).get_public_url(storage_path)
        logger.info(f"Audio uploaded successfully: {public_url}")
        return public_url

    except Exception as e:
        logger.error(f"Failed to upload audio: {e}")
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


def _run_shadowing_agent(target_sentence: str, user_transcript: str) -> str:
    """Run the shadowing evaluation agent comparing target vs user transcript."""
    prompt = f"""TARGET SENTENCE:
{target_sentence}

USER TRANSCRIPT:
{user_transcript}

Compare these and report the similarity."""

    response = shadowing_evaluation_agent.run(prompt)
    return response.content if hasattr(response, "content") else str(response)


def _parse_shadowing_output(raw: str) -> dict:
    """Parse agent output into simple shadowing evaluation data."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse shadowing agent output as JSON: {raw[:200]}...")
        return {
            "similarity_score": 0,
            "differences": [],
            "feedback": "Could not parse evaluation. Please try again.",
        }

    # Ensure all expected fields exist with safe defaults
    return {
        "similarity_score": _clamp_score(data.get("similarity_score")),
        "differences": data.get("differences", []),
        "feedback": data.get("feedback", "No feedback available."),
    }


def _clamp_score(value) -> int:
    """Clamp a score value to 0-100 range."""
    try:
        score = int(value) if value is not None else 0
        return max(0, min(100, score))
    except (ValueError, TypeError):
        return 0


def _save_shadowing_attempt(
    audio_url: str,
    user_transcript: str,
    target_sentence: str,
    target_sentence_index: Optional[int],
    evaluation: dict,
    supabase: Client,
    profile_id: str,
    youtube_gem_id: str,
    duration_seconds: Optional[int] = None,
) -> dict:
    """Save or update the shadowing attempt using composite primary key."""
    if target_sentence_index is None:
        target_sentence_index = 0  # Default if not provided

    row = {
        "profile_id": profile_id,
        "youtube_gem_id": youtube_gem_id,
        "target_sentence_index": target_sentence_index,
        "target_sentence": target_sentence,
        "audio_url": audio_url,
        "audio_duration_seconds": duration_seconds,
        "user_transcript": user_transcript,
        "similarity_score": evaluation["similarity_score"],
        "word_differences": evaluation["differences"],
        "feedback": evaluation["feedback"],
    }

    # Use upsert to handle composite primary key (insert or update)
    res = supabase.table("shadowing_attempts").upsert(row).execute()
    if not res.data:
        raise RuntimeError("Failed to save shadowing attempt")

    saved = res.data[0]

    # Return in schema-compatible format
    # Use composite key as identifier: profile_id:youtube_gem_id:target_sentence_index
    composite_id = f"{profile_id}:{youtube_gem_id}:{target_sentence_index}"

    return {
        "id": composite_id,
        "created_at": saved["created_at"],
        "updated_at": saved.get("updated_at"),
        "youtube_gem_id": saved["youtube_gem_id"],
        "target_sentence": saved["target_sentence"],
        "target_sentence_index": saved["target_sentence_index"],
        "audio_url": saved["audio_url"],
        "audio_duration_seconds": saved["audio_duration_seconds"],
        "user_transcript": saved["user_transcript"],
        "evaluation": {
            "similarity_score": saved["similarity_score"],
            "differences": saved["word_differences"],
            "feedback": saved["feedback"],
        },
    }


def list_shadowing_attempts(
    supabase: Client,
    profile_id: str,
    youtube_gem_id: Optional[str] = None,
    *,
    page: int = 0,
    page_size: int = 20,
) -> dict:
    """Paginated shadowing attempts for a profile, optionally filtered by video."""
    page = max(0, page)
    page_size = min(max(1, page_size), 100)
    offset = page * page_size
    end = offset + page_size - 1

    query = (
        supabase.table("shadowing_attempts")
        .select(
            "created_at, youtube_gem_id, target_sentence, target_sentence_index, "
            "audio_url, audio_duration_seconds, similarity_score",
            count="exact",
        )
        .eq("profile_id", profile_id)
    )

    if youtube_gem_id:
        query = query.eq("youtube_gem_id", youtube_gem_id)

    res = query.order("created_at", desc=True).range(offset, end).execute()

    rows = res.data or []
    total = int(res.count) if res.count is not None else len(rows)

    # Transform rows to match history item schema
    items = []
    for row in rows:
        yid = row.get("youtube_gem_id")
        idx = row.get("target_sentence_index")
        composite_id = f"{profile_id}:{yid}:{idx}"
        items.append({
            "id": composite_id,
            "created_at": row.get("created_at"),
            "youtube_gem_id": yid,
            "target_sentence": row.get("target_sentence"),
            "target_sentence_index": idx,
            "audio_url": row.get("audio_url"),
            "audio_duration_seconds": row.get("audio_duration_seconds"),
            "similarity_score": row.get("similarity_score"),
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_shadowing_attempt_detail(
    supabase: Client,
    profile_id: str,
    attempt_id: str,
) -> Optional[dict]:
    """
    Load one shadowing attempt with full evaluation data.
    
    The attempt_id format is: profile_id:youtube_gem_id:target_sentence_index
    or can query by youtube_gem_id and target_sentence_index separately.
    """
    # Parse composite id if provided
    parts = attempt_id.split(":")
    if len(parts) == 3:
        _, youtube_gem_id, target_sentence_index = parts
        target_sentence_index = int(target_sentence_index)
    else:
        # Fallback: treat as youtube_gem_id and require separate index lookup
        return None

    res = (
        supabase.table("shadowing_attempts")
        .select(
            "created_at, updated_at, youtube_gem_id, target_sentence, target_sentence_index, "
            "audio_url, audio_duration_seconds, user_transcript, "
            "similarity_score, word_differences, feedback"
        )
        .eq("profile_id", profile_id)
        .eq("youtube_gem_id", youtube_gem_id)
        .eq("target_sentence_index", target_sentence_index)
        .limit(1)
        .execute()
    )

    if not res.data:
        return None

    row = res.data[0]
    yid = row.get("youtube_gem_id")
    idx = row.get("target_sentence_index")
    composite_id = f"{profile_id}:{yid}:{idx}"

    return {
        "id": composite_id,
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "youtube_gem_id": yid,
        "target_sentence": row.get("target_sentence"),
        "target_sentence_index": idx,
        "audio_url": row.get("audio_url"),
        "audio_duration_seconds": row.get("audio_duration_seconds"),
        "user_transcript": row.get("user_transcript"),
        "evaluation": {
            "similarity_score": row.get("similarity_score"),
            "differences": row.get("word_differences", []),
            "feedback": row.get("feedback"),
        },
    }


def get_all_shadowing_for_video(
    supabase: Client,
    profile_id: str,
    youtube_gem_id: str,
) -> dict:
    """Get all shadowing attempts for a specific YouTube video, ordered by sentence index."""
    res = (
        supabase.table("shadowing_attempts")
        .select(
            "created_at, youtube_gem_id, target_sentence, target_sentence_index, "
            "audio_url, audio_duration_seconds, similarity_score",
            count="exact",
        )
        .eq("profile_id", profile_id)
        .eq("youtube_gem_id", youtube_gem_id)
        .order("target_sentence_index", desc=False)
        .execute()
    )

    rows = res.data or []
    total = int(res.count) if res.count is not None else len(rows)

    # Transform rows to match history item schema
    items = []
    for row in rows:
        yid = row.get("youtube_gem_id")
        idx = row.get("target_sentence_index")
        composite_id = f"{profile_id}:{yid}:{idx}"
        items.append({
            "id": composite_id,
            "created_at": row.get("created_at"),
            "youtube_gem_id": yid,
            "target_sentence": row.get("target_sentence"),
            "target_sentence_index": idx,
            "audio_url": row.get("audio_url"),
            "audio_duration_seconds": row.get("audio_duration_seconds"),
            "similarity_score": row.get("similarity_score"),
        })

    return {
        "items": items,
        "total": total,
        "page": 0,
        "page_size": total,
    }


def get_shadowing_stats(
    supabase: Client,
    profile_id: str,
    youtube_gem_id: str,
) -> dict:
    """Get shadowing statistics for a specific YouTube video."""
    # Get all attempts for this video
    res = (
        supabase.table("shadowing_attempts")
        .select(
            "target_sentence_index, similarity_score"
        )
        .eq("profile_id", profile_id)
        .eq("youtube_gem_id", youtube_gem_id)
        .execute()
    )

    rows = res.data or []
    
    if not rows:
        return {
            "youtube_gem_id": youtube_gem_id,
            "total_attempts": 0,
            "sentences_practiced": 0,
            "average_similarity_score": None,
            "best_attempt_id": None,
            "best_similarity_score": None,
            "progress_by_sentence": [],
        }

    total_attempts = len(rows)
    
    # Calculate unique sentences practiced
    sentence_indices = set(row.get("target_sentence_index") for row in rows if row.get("target_sentence_index") is not None)
    sentences_practiced = len(sentence_indices)

    # Calculate average and best score
    scores = [row.get("similarity_score") for row in rows if row.get("similarity_score") is not None]
    average_score = sum(scores) / len(scores) if scores else None
    
    # Find best attempt and build composite id
    best_attempt = max(rows, key=lambda x: x.get("similarity_score") or 0, default=None)
    best_score = best_attempt.get("similarity_score") if best_attempt else None
    best_idx = best_attempt.get("target_sentence_index") if best_attempt else None
    best_id = f"{profile_id}:{youtube_gem_id}:{best_idx}" if best_idx is not None else None

    # Progress by sentence
    sentence_progress = {}
    for row in rows:
        idx = row.get("target_sentence_index")
        if idx is None:
            continue
        score = row.get("similarity_score")
        if idx not in sentence_progress:
            sentence_progress[idx] = {"attempts": 0, "best_score": 0}
        sentence_progress[idx]["attempts"] += 1
        if score and score > sentence_progress[idx]["best_score"]:
            sentence_progress[idx]["best_score"] = score

    progress_list = [
        {"sentence_index": idx, **data}
        for idx, data in sentence_progress.items()
    ]
    progress_list.sort(key=lambda x: x["sentence_index"])

    return {
        "youtube_gem_id": youtube_gem_id,
        "total_attempts": total_attempts,
        "sentences_practiced": sentences_practiced,
        "average_similarity_score": average_score,
        "best_attempt_id": best_id,
        "best_similarity_score": best_score,
        "progress_by_sentence": progress_list,
    }
