"""Contrato del reconocimiento local de LIAM sin proveedores externos."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

speech = (ROOT / "frontend/js/lia-assistant/speech-controller.js").read_text(encoding="utf-8")
controller = (ROOT / "frontend/js/liam/liam-controller.js").read_text(encoding="utf-8")
routes = (ROOT / "backend/modules/asistente_capacitacion/routes.py").read_text(encoding="utf-8")
local = (ROOT / "backend/modules/asistente_capacitacion/local_speech.py").read_text(encoding="utf-8")
startup = (ROOT / "start_hosting.sh").read_text(encoding="utf-8")
requirements = (ROOT / "backend/requirements-production.txt").read_text(encoding="utf-8")

for contract in ("listenLocal", "audio/wav", "16000", "listen-transcript", "stopListening", "getUserMedia"):
    assert contract in speech, f"Falta contrato de captura local: {contract}"
assert "local_stt_enabled" in controller and "Activando reconocimiento local seguro" in controller
assert "@bp.post('/voice/transcribe')" in routes and "get_request_user_context()" in routes
assert "1_000_000" in routes and "VOICE_TRANSCRIBED_LOCAL" in routes
assert "KaldiRecognizer" in local and "wave.open" in local
assert '"ready": ready' in local and "local_speech_status()" in routes
assert "python backend/tools/ensure_vosk_model.py" in startup
assert "vosk==0.3.45" in requirements
print("LIAM_LOCAL_SPEECH_FALLBACK_V7_PASS")
