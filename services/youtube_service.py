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

    # Fetch transcript (captions first, MLX fallback)
    transcript, video_title, used_mlx = _fetch_transcript_with_fallback(video_id, url)
    if not transcript:
        raise ValueError(
            "Could not fetch transcript. Video may not have captions available, "
            "and MLX transcription is unavailable (requires Apple Silicon)."
        )

    # Use extracted title or placeholder
    if not video_title:
        video_title = _extract_title_from_transcript(transcript) or "YouTube Video"

    # Run agent analysis
    raw = _run_agent(transcript)
    parsed = _parse_output(url, video_title, raw)

    # TODO: Re-enable after testing
    # Save to database
    # _save(parsed, supabase, profile_id)

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


def _fetch_transcript_with_fallback(
    video_id: str, url: str
) -> tuple[Optional[str], Optional[str], bool]:
    """
    Fetch transcript with fallback to MLX transcription.

    Returns: (transcript, video_title, used_mlx)
    - First tries YouTube captions via youtube-transcript-api
    - Falls back to downloading audio and transcribing with mlx-whisper
    """
    import logging
    logger = logging.getLogger(__name__)

    # Try 1: Check if English transcript exists and fetch it
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        ytt_api = YouTubeTranscriptApi()

        # First, check what transcripts are available
        try:
            transcript_list = ytt_api.list(video_id)
        except Exception as e:
            logger.warning(f"Could not list transcripts for {video_id}: {e}")
            # If we can't list, try MLX directly
            return _transcribe_with_mlx(video_id, url)

        # Check if English transcript exists (manually created or generated)
        english_transcript = None
        try:
            # Try to find English transcript directly
            english_transcript = transcript_list.find_transcript(['en'])
        except Exception:
            # No English transcript found - check if we can translate to English
            logger.info(f"No direct English transcript for {video_id}, checking translation options")
            try:
                # Find any transcript that can be translated to English
                for transcript in transcript_list:
                    if transcript.is_translatable:
                        # Check if English is in translation languages
                        translatable_codes = [lang.language_code for lang in transcript.translation_languages]
                        if 'en' in translatable_codes:
                            logger.info(f"Found {transcript.language_code} transcript, translating to English")
                            english_transcript = transcript.translate('en')
                            break
            except Exception as trans_e:
                logger.warning(f"Could not find translatable transcript: {trans_e}")

        if english_transcript is None:
            logger.info(f"No English transcript available for {video_id}, using MLX transcription")
            return _transcribe_with_mlx(video_id, url)

        # Fetch the English transcript
        fetched = english_transcript.fetch()
        full_text = ' '.join(segment.text for segment in fetched)
        logger.info(f"Successfully fetched English captions for video {video_id}")
        return full_text, None, False

    except Exception as e:
        logger.warning(f"youtube-transcript-api failed for {video_id}: {type(e).__name__}: {e}")
        # Fall through to MLX

    # Try 2: MLX Whisper transcription (requires Apple Silicon)
    try:
        return _transcribe_with_mlx(video_id, url)
    except Exception as e:
        logger.error(f"MLX transcription failed for {video_id}: {type(e).__name__}: {e}")
        return None, None, False


def _transcribe_with_mlx(video_id: str, url: str) -> tuple[Optional[str], Optional[str], bool]:
    """
    Download YouTube audio and transcribe using MLX Whisper.

    Returns: (transcript, video_title, used_mlx=True)
    """
    import subprocess

    # Check if mlx_whisper is available
    try:
        import mlx_whisper
    except ImportError:
        return None, None, False

    # Create temp directory for audio download
    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = os.path.join(tmpdir, f"{video_id}.m4a")

        # Download audio using yt-dlp
        try:
            result = subprocess.run(
                [
                    "yt-dlp",
                    "-f", "bestaudio[ext=m4a]/bestaudio",
                    "-o", audio_path,
                    "--no-playlist",
                    "--quiet",
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                return None, None, False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None, None, False

        # Check if file was downloaded
        if not os.path.exists(audio_path):
            return None, None, False

        # Get video title from yt-dlp
        video_title = None
        try:
            title_result = subprocess.run(
                [
                    "yt-dlp",
                    "--print", "%(title)s",
                    "--no-playlist",
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if title_result.returncode == 0:
                video_title = title_result.stdout.strip()
        except Exception:
            pass

        # Transcribe with MLX Whisper
        try:
            result = mlx_whisper.transcribe(
                audio_path,
                path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
                verbose=False,
            )
            transcript = result.get("text", "").strip()
            return transcript, video_title, True
        except Exception:
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


def _parse_output(url: str, video_title: str, raw: str) -> dict:
    """Parse agent output into structured data."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "video_title": video_title,
            "video_url": url,
            "useful_sentences": [],
            "grammar_patterns": [],
            "everyday_phrases": [],
            "learning_tip": "Could not parse analysis. Please try again.",
        }

    # Ensure all expected fields exist
    result = {
        "video_title": data.get("video_title", video_title),
        "video_url": url,
        "useful_sentences": data.get("useful_sentences", []),
        "grammar_patterns": data.get("grammar_patterns", []),
        "everyday_phrases": data.get("everyday_phrases", []),
        "learning_tip": data.get("learning_tip"),
    }

    return result


def _save(data: dict, supabase: Client, profile_id: str) -> None:
    """Save the analysis to the database."""
    sentences = data.get("useful_sentences", [])
    phrases = data.get("everyday_phrases", [])

    row = {
        "profile_id": profile_id,
        "video_title": data.get("video_title", ""),
        "video_url": data.get("video_url", ""),
        "sentence_count": len(sentences),
        "phrase_count": len(phrases),
        "analysis_data": data,  # Store full JSON for detail view
    }

    res = supabase.table("youtube_analyses").insert(row).execute()
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

    res = (
        supabase.table("youtube_analyses")
        .select(
            "id, created_at, video_title, video_url, sentence_count, phrase_count",
            count="exact",
        )
        .eq("profile_id", profile_id)
        .order("created_at", desc=True)
        .range(offset, end)
        .execute()
    )
    rows = res.data or []
    total = int(res.count) if res.count is not None else len(rows)
    return {
        "items": rows,
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
        supabase.table("youtube_analyses")
        .select("id, video_title, video_url, analysis_data, created_at")
        .eq("id", analysis_id)
        .eq("profile_id", profile_id)
        .limit(1)
        .execute()
    )
    if not res.data:
        return None

    row = res.data[0]
    analysis_data = row.get("analysis_data", {})

    return {
        "id": row.get("id"),
        "video_title": row.get("video_title", ""),
        "video_url": row.get("video_url", ""),
        "useful_sentences": analysis_data.get("useful_sentences", []),
        "grammar_patterns": analysis_data.get("grammar_patterns", []),
        "everyday_phrases": analysis_data.get("everyday_phrases", []),
        "learning_tip": analysis_data.get("learning_tip"),
        "created_at": row.get("created_at"),
    }
