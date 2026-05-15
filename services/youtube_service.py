import json
import os
import re
import tempfile
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

from supabase.client import Client

from agents.youtube_analysis_agent import youtube_analysis_agent
from services.transcription import transcribe_audio_file


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
    transcript, video_title, used_mlx, transcript_segments = _transcribe_with_mlx(
        video_id, url
    )
    if not transcript:
        raise ValueError(
            "Could not transcribe video. Transcription failed "
            "(requires mlx-whisper on Apple Silicon or faster-whisper in Docker/Linux)."
        )

    # Use extracted title or placeholder
    if not video_title:
        video_title = _extract_title_from_transcript(transcript) or "YouTube Video"

    # Run agent analysis
    raw = _run_agent(transcript)
    parsed = _parse_output(
        url, video_title, transcript, raw, transcript_segments=transcript_segments
    )

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


def _split_transcript_into_sentences(text: str) -> list[str]:
    """Split transcript on sentence-ending punctuation followed by whitespace."""
    text = text.strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def _concat_ranges_from_whisper_segments(
    segments: list[dict[str, Any]],
) -> tuple[str, list[tuple[int, int, float, float]]]:
    """
    Concatenate Whisper segment texts in order and record char ranges with wall times.

    Returns (timeline_text, [(char_start, char_end, t_start, t_end), ...]).
    """
    offset = 0
    ranges: list[tuple[int, int, float, float]] = []
    parts: list[str] = []
    for seg in segments:
        txt = seg.get("text") or ""
        if not txt:
            continue
        t0 = float(seg.get("start", 0.0))
        t1 = float(seg.get("end", t0))
        g0, g1 = offset, offset + len(txt)
        ranges.append((g0, g1, t0, t1))
        parts.append(txt)
        offset = g1
    return "".join(parts), ranges


def _time_for_char_index(
    char_index: float,
    ranges: list[tuple[int, int, float, float]],
) -> float:
    """Piecewise-linear time for a character index into timeline_text."""
    if not ranges:
        return 0.0
    total = ranges[-1][1]
    ci = max(0.0, min(float(char_index), total - 1e-9))
    for g0, g1, t0, t1 in ranges:
        if g0 <= ci < g1 or (g1 >= total and g0 <= ci <= g1):
            span = max(g1 - g0, 1e-6)
            frac = (ci - g0) / span
            return t0 + frac * (t1 - t0)
    return ranges[-1][3]


def _transcript_segments_from_whisper(
    transcript: str, whisper_segments: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Build [{text, start_time, end_time}, ...] from MLX Whisper segments + full transcript text.

    Maps each sentence's character span in the transcript onto the concatenated segment
    string (same order as Whisper) to recover piecewise-linear timestamps.
    """
    transcript = transcript.strip()
    if not transcript:
        return []

    clean_whisper = [s for s in whisper_segments if (s.get("text") or "").strip()]
    if not clean_whisper:
        return [
            {
                "text": transcript,
                "start_time": 0.0,
                "end_time": 0.0,
            }
        ]

    timeline, ranges = _concat_ranges_from_whisper_segments(clean_whisper)
    t_wall0 = float(clean_whisper[0].get("start", 0.0))
    t_wall1 = float(clean_whisper[-1].get("end", t_wall0))
    duration = max(t_wall1 - t_wall0, 1e-3)

    sentences = _split_transcript_into_sentences(transcript)
    if not sentences:
        return [
            {
                "text": transcript,
                "start_time": t_wall0,
                "end_time": t_wall1,
            }
        ]

    n_tr = max(len(transcript), 1)
    tln = max(len(timeline), 1)

    def times_for_span(cs: int, ce: int) -> tuple[float, float]:
        if timeline:
            m_start = int(cs * tln / n_tr)
            m_end_excl = int(ce * tln / n_tr)
            m_end_excl = max(m_end_excl, m_start + 1)
            m_end_excl = min(m_end_excl, len(timeline))
            end_idx = max(m_start, m_end_excl - 1)
            m_start = min(max(0, m_start), len(timeline) - 1)
            end_idx = min(max(m_start, end_idx), len(timeline) - 1)
            st = _time_for_char_index(m_start, ranges)
            en = _time_for_char_index(end_idx, ranges)
            return st, max(en, st + 0.05)
        st = t_wall0 + (cs / n_tr) * duration
        en = t_wall0 + (ce / n_tr) * duration
        return st, max(en, st + 0.05)

    out: list[dict[str, Any]] = []
    search_from = 0
    for sent in sentences:
        idx = transcript.find(sent, search_from)
        if idx < 0:
            idx = transcript.find(sent)
        if idx < 0:
            idx = search_from
        cs, ce = idx, idx + len(sent)
        search_from = ce
        st, en = times_for_span(cs, ce)
        if out and st < out[-1]["end_time"]:
            st = out[-1]["end_time"]
        if en <= st:
            en = st + 0.05
        out.append({"text": sent, "start_time": round(st, 3), "end_time": round(en, 3)})

    return out


def _transcribe_with_mlx(
    video_id: str, url: str
) -> tuple[Optional[str], Optional[str], bool, list[dict[str, Any]]]:
    """
    Download YouTube audio and transcribe using MLX Whisper.

    Returns: (transcript, video_title, used_mlx, transcript_segments)
    """
    import logging
    import subprocess

    logger = logging.getLogger(__name__)

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
                return None, None, False, []
            logger.info("yt-dlp download successful")
        except subprocess.TimeoutExpired:
            logger.error("yt-dlp timed out after 120 seconds")
            return None, None, False, []
        except FileNotFoundError:
            logger.error("yt-dlp not found. Install with: pip install yt-dlp")
            return None, None, False, []

        # Check if file was downloaded
        if not os.path.exists(audio_path):
            logger.error(f"Audio file not found at {audio_path}")
            return None, None, False, []
        logger.info(f"Audio file exists, size: {os.path.getsize(audio_path)} bytes")

        try:
            logger.info("Starting transcription for %s", video_id)
            tr = transcribe_audio_file(audio_path)
            if not tr or not tr.text:
                return None, None, False, []
            transcript_segments = _transcript_segments_from_whisper(
                tr.text, tr.segments
            )
            logger.info(
                "Transcription successful (%s), %d characters, %d timed segments",
                tr.backend,
                len(tr.text),
                len(transcript_segments),
            )
            return tr.text, video_title, tr.backend == "mlx", transcript_segments
        except Exception as e:
            logger.error(f"Transcription failed: {type(e).__name__}: {e}")
            return None, None, False, []


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


def _parse_output(
    url: str,
    video_title: str,
    transcript: str,
    raw: str,
    *,
    transcript_segments: Optional[list[dict[str, Any]]] = None,
) -> dict:
    """Parse agent output into structured data."""
    segments = transcript_segments if transcript_segments is not None else []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "video_title": video_title,
            "video_url": url,
            "transcript": transcript,
            "transcript_segments": segments,
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
        "transcript_segments": segments,
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
        "transcript_segments": data.get("transcript_segments", []),
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
        .select(
            "id, video_title, video_url, transcript, transcript_segments, "
            "useful_sentences, grammar_patterns, everyday_phrases, learning_tip, created_at"
        )
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
        "transcript_segments": row.get("transcript_segments") or [],
        "useful_sentences": row.get("useful_sentences", []),
        "grammar_patterns": row.get("grammar_patterns", []),
        "everyday_phrases": row.get("everyday_phrases", []),
        "learning_tip": row.get("learning_tip"),
        "created_at": row.get("created_at"),
    }
