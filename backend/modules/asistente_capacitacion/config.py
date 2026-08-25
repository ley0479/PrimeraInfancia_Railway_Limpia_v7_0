"""Configuración segura de LÍA. Ninguna bandera expone secretos al cliente."""
from __future__ import annotations

import os


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on', 'si', 'sí'}


def _int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))


def public_flags() -> dict:
    enabled = _bool('ENABLE_LIA_ASSISTANT', False)
    return {
        'enabled': enabled,
        'text_enabled': enabled and _bool('LIA_TEXT_ENABLED', True),
        'context_help_enabled': enabled and _bool('LIA_CONTEXT_HELP_ENABLED', True),
        'guided_tours_enabled': enabled and _bool('LIA_GUIDED_TOURS_ENABLED', True),
        'voice_enabled': enabled and _bool('LIA_VOICE_ENABLED', False),
        'browser_tts_enabled': enabled and _bool('LIA_BROWSER_TTS_ENABLED', True),
        'realtime_enabled': enabled and _bool('LIA_REALTIME_ENABLED', False),
        'ai_enabled': enabled and _bool('LIA_AI_ENABLED', False),
        'feedback_enabled': enabled and _bool('LIA_FEEDBACK_ENABLED', True),
        'diagnostics_enabled': enabled and _bool('LIA_DIAGNOSTICS_ENABLED', True),
        'max_message_length': _int('LIA_MAX_MESSAGE_LENGTH', 2000, 100, 5000),
        'rate_limit_per_minute': _int('LIA_RATE_LIMIT_PER_MINUTE', 20, 1, 120),
    }
