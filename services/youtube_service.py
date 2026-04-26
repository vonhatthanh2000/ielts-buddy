import json
import os
import re
import tempfile
from typing import Optional
from urllib.parse import parse_qs, urlparse

from supabase.client import Client

from agents.youtube_analysis_agent import youtube_analysis_agent


def analyze_youtube_video(
    url: str, supabase: Client, profile_id: str
) -> dict:
    """
    Full pipeline: extract transcript -> call agent -> parse output -> save -> return result.

    Tries YouTube captions first, falls back to MLX transcription if unavailable.
    """
    # Extract video ID
    video_id = _extract_video_id(url)
    if not video_id:
        raise ValueError("Invalid YouTube URL. Could not extract video ID.")

    # Download audio and transcribe with MLX Whisper
    transcript, video_title, used_mlx = _transcribe_with_mlx(video_id, url)
    if not transcript:
        raise ValueError(
            "Could not transcribe video. MLX transcription failed or is unavailable "
            "(requires Apple Silicon Mac with mlx-whisper installed)."
        )

    # Use extracted title or placeholder
    if not video_title:
        video_title = _extract_title_from_transcript(transcript) or "YouTube Video"

    # Run agent analysis
    raw = _run_agent(transcript)
    parsed = _parse_output(url, video_title, transcript, raw)

    _save(parsed, supabase, profile_id)

    return parsed


def _extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/v/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    # Try parsing as standard URL
    parsed = urlparse(url)
    if parsed.hostname in ('youtube.com', 'www.youtube.com'):
        qs = parse_qs(parsed.query)
        if 'v' in qs:
            return qs['v'][0]
    elif parsed.hostname == 'youtu.be':
        return parsed.path.lstrip('/')

    return None


def _transcribe_with_mlx(video_id: str, url: str) -> tuple[Optional[str], Optional[str], bool]:
    """
    Download YouTube audio and transcribe using MLX Whisper.

    Returns: (transcript, video_title, used_mlx=True)
    """
    import logging
    import subprocess

    logger = logging.getLogger(__name__)

    # Check if mlx_whisper is available
    try:
        import mlx_whisper
        logger.info("mlx_whisper imported successfully")
    except ImportError as e:
        logger.error(f"mlx_whisper not available: {e}")
        return None, None, False

    # Create temp directory for audio download
    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = os.path.join(tmpdir, f"{video_id}.m4a")
        logger.info(f"Downloading audio to {audio_path}")

        # Download audio and get video title in one yt-dlp call
        video_title = None
        try:
            # First, get video info without downloading to extract title
            info_result = subprocess.run(
                [
                    "yt-dlp",
                    "--print", "%(title)s",
                    "--no-playlist",
                    "--skip-download",
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if info_result.returncode == 0:
                video_title = info_result.stdout.strip()
                logger.info(f"Got video title: {video_title}")
        except Exception as e:
            logger.warning(f"Could not get video title: {e}")

        # Download audio using yt-dlp
        try:
            result = subprocess.run(
                [
                    "yt-dlp",
                    "-f", "bestaudio[ext=m4a]/bestaudio",
                    "-o", audio_path,
                    "--no-playlist",
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                logger.error(f"yt-dlp failed: {result.stderr}")
                return None, None, False
            logger.info("yt-dlp download successful")
        except subprocess.TimeoutExpired:
            logger.error("yt-dlp timed out after 120 seconds")
            return None, None, False
        except FileNotFoundError:
            logger.error("yt-dlp not found. Install with: pip install yt-dlp")
            return None, None, False

        # Check if file was downloaded
        if not os.path.exists(audio_path):
            logger.error(f"Audio file not found at {audio_path}")
            return None, None, False
        logger.info(f"Audio file exists, size: {os.path.getsize(audio_path)} bytes")

        # Transcribe with MLX Whisper
        try:
            logger.info(f"Starting MLX transcription for {video_id}")
            result = mlx_whisper.transcribe(
                audio_path,
                path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
                verbose=False,
            )
            transcript = result.get("text", "").strip()
            logger.info(f"MLX transcription successful, got {len(transcript)} characters")
            return transcript, video_title, True
        except Exception as e:
            logger.error(f"MLX transcription failed: {type(e).__name__}: {e}")
            return None, None, False


def _extract_title_from_transcript(transcript: str) -> Optional[str]:
    """Try to extract a title from the transcript (first sentence or first 50 chars)."""
    if not transcript:
        return None

    # Use first sentence or first 50 characters
    first_part = transcript[:100].strip()
    if '.' in first_part:
        return first_part.split('.')[0] + '.'
    return first_part[:50] + '...' if len(first_part) > 50 else first_part


def _run_agent(transcript: str) -> str:
    """Run the YouTube analysis agent with the transcript."""
    # Truncate if too long (agent has token limits)
    max_chars = 15000
    if len(transcript) > max_chars:
        transcript = transcript[:max_chars] + "... [transcript truncated due to length]"

    prompt = f"Analyze this YouTube transcript:\n\n{transcript}"
    response = youtube_analysis_agent.run(prompt)
    return response.content if hasattr(response, "content") else str(response)


def _parse_output(url: str, video_title: str, transcript: str, raw: str) -> dict:
    """Parse agent output into structured data."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "video_title": video_title,
            "video_url": url,
            "transcript": transcript,
            "useful_sentences": [],
            "grammar_patterns": [],
            "everyday_phrases": [],
            "learning_tip": "Could not parse analysis. Please try again.",
        }

    # Ensure all expected fields exist
    # Prefer yt-dlp title over agent title, unless yt-dlp failed
    agent_title = data.get("video_title", "")
    final_title = video_title if video_title and video_title.lower() not in ("unknown", "") else agent_title
    if not final_title or final_title.lower() == "unknown":
        final_title = "YouTube Video"

    result = {
        "video_title": final_title,
        "video_url": url,
        "transcript": transcript,
        "useful_sentences": data.get("useful_sentences", []),
        "grammar_patterns": data.get("grammar_patterns", []),
        "everyday_phrases": data.get("everyday_phrases", []),
        "learning_tip": data.get("learning_tip"),
    }

    return result


def _save(data: dict, supabase: Client, profile_id: str) -> None:
    """Save the analysis to the database."""
    row = {
        "profile_id": profile_id,
        "video_title": data.get("video_title", ""),
        "video_url": data.get("video_url", ""),
        "transcript": data.get("transcript", ""),
        "useful_sentences": data.get("useful_sentences", []),
        "grammar_patterns": data.get("grammar_patterns", []),
        "everyday_phrases": data.get("everyday_phrases", []),
        "learning_tip": data.get("learning_tip"),
    }

    res = supabase.table("youtube_gem").insert(row).execute()
    if not res.data:
        raise RuntimeError("Failed to insert YouTube analysis")


def list_youtube_analyses(
    supabase: Client,
    profile_id: str,
    *,
    page: int = 0,
    page_size: int = 20,
) -> dict:
    """Paginated YouTube analyses for a profile, newest first."""
    page = max(0, page)
    page_size = min(max(1, page_size), 100)
    offset = page * page_size
    end = offset + page_size - 1

    # Calculate counts from JSONB arrays
    res = (
        supabase.table("youtube_gem")
        .select(
            "id, created_at, video_title, video_url, useful_sentences, everyday_phrases",
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
        useful_sentences = row.get("useful_sentences", [])
        everyday_phrases = row.get("everyday_phrases", [])
        items.append({
            "id": row.get("id"),
            "created_at": row.get("created_at"),
            "video_title": row.get("video_title", ""),
            "video_url": row.get("video_url", ""),
            "sentence_count": len(useful_sentences) if isinstance(useful_sentences, list) else 0,
            "phrase_count": len(everyday_phrases) if isinstance(everyday_phrases, list) else 0,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_youtube_analysis_detail(
    supabase: Client,
    profile_id: str,
    analysis_id: str,
) -> Optional[dict]:
    """Load one YouTube analysis with full data."""
    res = (
        supabase.table("youtube_gem")
        .select("id, video_title, video_url, transcript, useful_sentences, grammar_patterns, everyday_phrases, learning_tip, created_at")
        .eq("id", analysis_id)
        .eq("profile_id", profile_id)
        .limit(1)
        .execute()
    )
    if not res.data:
        return None

    row = res.data[0]

    return {
        "id": row.get("id"),
        "video_title": row.get("video_title", ""),
        "video_url": row.get("video_url", ""),
        "transcript": row.get("transcript", ""),
        "useful_sentences": row.get("useful_sentences", []),
        "grammar_patterns": row.get("grammar_patterns", []),
        "everyday_phrases": row.get("everyday_phrases", []),
        "learning_tip": row.get("learning_tip"),
        "created_at": row.get("created_at"),
    }
