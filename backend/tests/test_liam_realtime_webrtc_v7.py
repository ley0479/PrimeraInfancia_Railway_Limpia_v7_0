from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
routes=(ROOT/'backend/modules/asistente_capacitacion/routes.py').read_text(encoding='utf-8')
controller=(ROOT/'frontend/js/liam/liam-controller.js').read_text(encoding='utf-8')
runtime=(ROOT/'frontend/js/liam/liam-realtime-webrtc.js').read_text(encoding='utf-8')
index=(ROOT/'frontend/index.html').read_text(encoding='utf-8')

assert "@bp.post('/voice/realtime/call')" in routes
assert "https://api.openai.com/v1/realtime/calls" in routes
assert "OpenAI-Safety-Identifier" in routes
assert "files={'sdp':(None,sdp),'session':" in routes
assert "LIAM_REALTIME_MODEL" in routes
assert "get_request_user_context()" in routes
assert "RTCPeerConnection" in runtime and "getUserMedia" in runtime
assert "Content-Type':'application/sdp'" in runtime
assert "conversation.item.input_audio_transcription.completed" in runtime
assert "interrupt_response':True" in routes
assert "data-action=\"realtime\"" in controller
assert "liam-realtime-webrtc" in controller
assert "liam-controller.js?v=2.7.5-realtime-webrtc-1" in index
print('LIAM_REALTIME_WEBRTC_V7_PASS')
