"""Banderas seguras, cobertura contextual y registro cerrado de LÍA."""
import os
from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))

from modules.asistente_capacitacion.config import public_flags
from modules.asistente_capacitacion.guides import GUIDES

os.environ.pop('ENABLE_LIA_ASSISTANT', None)
flags = public_flags()
assert flags['enabled'] is False
assert flags['voice_enabled'] is False
assert flags['ai_enabled'] is False
assert flags['realtime_enabled'] is False

required = {'dashboard','base-maestra','talento','salud-nutricion','calendario-inteligente','motor-documental','formatos','administracion','relacion-mes'}
assert required.issubset(GUIDES)
for key in required:
    assert GUIDES[key]['proposito']
    assert len(GUIDES[key]['pasos']) >= 3
    assert GUIDES[key]['resultado']
    assert GUIDES[key]['errores_frecuentes']

registry = (ROOT / 'frontend/js/lia-assistant/help-registry.js').read_text(encoding='utf-8')
assert 'LIA_HELP_REGISTRY' in registry
assert 'document.querySelector(selector)' not in registry
print('LIA_FLAGS_GUIDES_V7_PASS')
