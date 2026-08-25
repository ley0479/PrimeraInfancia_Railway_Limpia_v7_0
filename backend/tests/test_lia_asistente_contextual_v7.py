"""Contrato fuente de LÍA: multimodal, contextual y sin escritura operativa."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
frontend = (ROOT / 'frontend/js/modules/asistente-capacitacion.js').read_text(encoding='utf-8')
styles = (ROOT / 'frontend/css/asistente-capacitacion.css').read_text(encoding='utf-8')
readme = (ROOT / 'backend/modules/asistente_capacitacion/README.md').read_text(encoding='utf-8')

assert 'Línea Inteligente de Ayuda' in frontend
speech = (ROOT / 'frontend/js/lia-assistant/speech-controller.js').read_text(encoding='utf-8')
assert 'SpeechRecognition' in speech and 'webkitSpeechRecognition' in speech
assert 'La transcripción está lista' in frontend
assert 'tools/get_pending_activities_summary' in frontend
assert 'showWhere' in frontend and 'lia-target' in styles
assert 'Nunca modifica información sin tu autorización' in frontend
assert 'LÍA — Línea Inteligente de Ayuda' in readme
print('LIA_ASISTENTE_CONTEXTUAL_V7_PASS')
