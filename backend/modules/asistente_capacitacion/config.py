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


def public_liam_flags() -> dict:
    """Banderas públicas de LIAM; ninguna contiene secretos ni autoridad."""
    enabled = _bool('ENABLE_LIAM_ASSISTANT', False)
    performance = os.getenv('LIAM_PERFORMANCE_MODE', 'auto').strip().lower()
    if performance not in {'auto', 'full', 'light', 'reduced'}:
        performance = 'auto'
    motion = os.getenv('LIAM_DEFAULT_MOTION_LEVEL', 'light').strip().lower()
    if motion not in {'full', 'light', 'reduced'}:
        motion = 'light'
    return {
        'enabled': enabled,
        'text_enabled': enabled and _bool('LIAM_TEXT_ENABLED', True),
        'voice_enabled': enabled and _bool('LIAM_VOICE_ENABLED', False),
        'animation_enabled': enabled and _bool('LIAM_ANIMATION_ENABLED', True),
        'walk_enabled': enabled and _bool('LIAM_WALK_ENABLED', False),
        'teleport_enabled': enabled and _bool('LIAM_TELEPORT_ENABLED', True),
        'lip_sync_enabled': enabled and _bool('LIAM_LIP_SYNC_ENABLED', False),
        'hologram_enabled': enabled and _bool('LIAM_HOLOGRAM_ENABLED', True),
        'context_guide_enabled': enabled and _bool('LIAM_CONTEXT_GUIDE_ENABLED', True),
        'tours_enabled': enabled and _bool('LIAM_TOURS_ENABLED', True),
        'platform_presentation_enabled': enabled and _bool('LIAM_PLATFORM_PRESENTATION_ENABLED', True),
        'tablet_display_enabled': enabled and _bool('LIAM_TABLET_DISPLAY_ENABLED', True),
        'mini_help_enabled': enabled and _bool('LIAM_MINI_HELP_ENABLED', False),
        'ai_enabled': enabled and _bool('LIAM_AI_ENABLED', False),
        'realtime_voice_enabled': enabled and _bool('LIAM_REALTIME_VOICE_ENABLED', False),
        'performance_mode': performance,
        'default_motion_level': motion,
    }


def public_elian_flags() -> dict:
    """Identidad nueva con fallback compatible a la activación actual de LIAM."""
    legacy = public_liam_flags()
    explicitly_enabled = os.getenv('ENABLE_ELIAN_ASSISTANT')
    enabled = legacy['enabled'] if explicitly_enabled is None else _bool('ENABLE_ELIAN_ASSISTANT', False)
    return {
        **legacy,
        'enabled': enabled,
        'assistant_name': (os.getenv('ELIAN_ASSISTANT_NAME') or 'ELIAN').strip()[:40] or 'ELIAN',
        'platform_tour_enabled': enabled and _bool('ELIAN_PLATFORM_TOUR_ENABLED', True),
        'avatar_gender': (os.getenv('ELIAN_AVATAR_GENDER') or 'male').strip().lower(),
        'avatar_variant': (os.getenv('ELIAN_AVATAR_VARIANT') or 'afro_colombian_institutional').strip().lower(),
        'skin_tone': (os.getenv('ELIAN_SKIN_TONE') or 'dark').strip().lower(),
    }
