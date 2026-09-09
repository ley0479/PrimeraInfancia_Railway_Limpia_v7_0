"""Transcripción local de audio WAV para LIAM; no envía voz a terceros."""
from __future__ import annotations

import json
import os
import wave
from pathlib import Path

_model = None


def enabled() -> bool:
    return os.getenv("LIAM_LOCAL_STT_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on", "si", "sí"}


def model_path() -> Path:
    return Path(os.getenv("LIAM_VOSK_MODEL_PATH") or Path(os.getenv("DATA_DIR", "/data")) / "models" / "vosk-model-small-es-0.42")


def status() -> dict:
    ready = (model_path() / "conf" / "model.conf").exists()
    return {"enabled": enabled(), "ready": ready, "provider": "vosk-local" if ready else None}


def _load_model():
    global _model
    if _model is None:
        if not enabled():
            raise RuntimeError("El reconocimiento local está desactivado.")
        path = model_path()
        if not (path / "conf" / "model.conf").exists():
            raise RuntimeError("El modelo local de español todavía no está disponible.")
        from vosk import Model
        _model = Model(str(path))
    return _model


def transcribe_wav(path: str | Path) -> str:
    from vosk import KaldiRecognizer
    with wave.open(str(path), "rb") as audio:
        if audio.getnchannels() != 1 or audio.getsampwidth() != 2 or audio.getframerate() != 16000:
            raise ValueError("El audio debe ser WAV PCM mono de 16 kHz.")
        recognizer = KaldiRecognizer(_load_model(), 16000)
        while chunk := audio.readframes(4000):
            recognizer.AcceptWaveform(chunk)
        result = json.loads(recognizer.FinalResult() or "{}")
    return str(result.get("text") or "").strip()
