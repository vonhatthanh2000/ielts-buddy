"""Audio transcription: MLX Whisper on Apple Silicon, faster-whisper elsewhere (e.g. Docker)."""

import logging
import os
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)

MLX_REPO = "mlx-community/whisper-large-v3-turbo"
_faster_model: Any = None


@dataclass
class TranscriptionResult:
    text: str
    segments: list[dict[str, Any]]
    backend: str


def transcribe_audio_file(audio_path: str) -> Optional[TranscriptionResult]:
    """Transcribe an audio file; returns None if all backends fail."""
    if not os.path.exists(audio_path):
        logger.error("Audio file not found: %s", audio_path)
        return None

    result = _transcribe_mlx(audio_path)
    if result is not None:
        return result
    return _transcribe_faster_whisper(audio_path)


def _transcribe_mlx(audio_path: str) -> Optional[TranscriptionResult]:
    try:
        import mlx_whisper
    except ImportError:
        return None

    try:
        logger.info("Transcribing with MLX Whisper: %s", audio_path)
        raw = mlx_whisper.transcribe(
            audio_path,
            path_or_hf_repo=MLX_REPO,
            verbose=False,
        )
        text = raw.get("text", "").strip()
        if not text:
            return None
        return TranscriptionResult(
            text=text,
            segments=raw.get("segments") or [],
            backend="mlx",
        )
    except Exception as e:
        logger.error("MLX transcription failed: %s: %s", type(e).__name__, e)
        return None


def _get_faster_whisper_model():
    global _faster_model
    if _faster_model is None:
        from faster_whisper import WhisperModel

        model_size = os.getenv("WHISPER_MODEL", "base")
        device = os.getenv("WHISPER_DEVICE", "cpu")
        compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
        logger.info("Loading faster-whisper model=%s device=%s", model_size, device)
        _faster_model = WhisperModel(model_size, device=device, compute_type=compute_type)
    return _faster_model


def _transcribe_faster_whisper(audio_path: str) -> Optional[TranscriptionResult]:
    try:
        model = _get_faster_whisper_model()
    except ImportError:
        logger.error("faster-whisper not installed; transcription unavailable")
        return None
    except Exception as e:
        logger.error("Failed to load faster-whisper: %s: %s", type(e).__name__, e)
        return None

    try:
        logger.info("Transcribing with faster-whisper: %s", audio_path)
        segments_iter, _info = model.transcribe(audio_path)
        segments: list[dict[str, Any]] = []
        for seg in segments_iter:
            segments.append(
                {
                    "start": float(seg.start),
                    "end": float(seg.end),
                    "text": seg.text,
                }
            )
        text = "".join(s["text"] for s in segments).strip()
        if not text:
            text = " ".join(s["text"].strip() for s in segments).strip()
        if not text:
            return None
        return TranscriptionResult(text=text, segments=segments, backend="faster-whisper")
    except Exception as e:
        logger.error("faster-whisper transcription failed: %s: %s", type(e).__name__, e)
        return None
