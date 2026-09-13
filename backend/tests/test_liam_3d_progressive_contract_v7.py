"""Contrato del avatar lector: cambio visual estático sin duplicar el asistente."""
import json
import os
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from modules.asistente_capacitacion.config import public_liam_flags


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def glb_json(relative: str) -> dict:
    with (ROOT / relative).open("rb") as source:
        assert source.read(4) == b"glTF"
        version, _length = struct.unpack("<II", source.read(8))
        assert version == 2
        chunk_length, chunk_type = struct.unpack("<II", source.read(8))
        assert chunk_type == 0x4E4F534A
        return json.loads(source.read(chunk_length))


os.environ.pop("LIAM_AVATAR_3D_ENABLED", None)
os.environ["ENABLE_LIAM_ASSISTANT"] = "true"
assert public_liam_flags()["avatar_3d_enabled"] is False
os.environ["LIAM_AVATAR_3D_ENABLED"] = "true"
assert public_liam_flags()["avatar_3d_enabled"] is True

desktop_path = "frontend/assets/lia/3d/liam-lector.glb"
mobile_path = "frontend/assets/lia/3d/liam-lector-movil.glb"
poster_path = "frontend/assets/lia/3d/liam-lector-frontal.png"
female_path = ROOT / "frontend/assets/lia/3d/liam-mujer-v1.glb"
engine_path = ROOT / "frontend/vendor/model-viewer/model-viewer-4.3.1.min.js"
assert 1_000_000 < (ROOT / desktop_path).stat().st_size < 4_000_000
assert 500_000 < (ROOT / mobile_path).stat().st_size < 2_000_000
assert (ROOT / poster_path).is_file() and female_path.is_file()
assert engine_path.is_file() and engine_path.stat().st_size < 1200 * 1024

for model_path in (desktop_path, mobile_path):
    model = glb_json(model_path)
    assert not model.get("animations"), model.get("animations")
    assert not model.get("skins"), model.get("skins")
    assert len(model.get("materials", [])) == 1
    assert len(model.get("images", [])) == 1
    assert all(not primitive.get("targets") for mesh in model.get("meshes", []) for primitive in mesh.get("primitives", []))

renderer = read("frontend/js/liam/liam-3d-renderer.js")
movement = read("frontend/js/liam/liam-movement-controller.js")
speech = read("frontend/js/lia-assistant/speech-controller.js")
avatar_css = read("frontend/css/ian-avatar.css")
controller = read("frontend/js/liam/liam-controller.js")
index = read("frontend/index.html")
backend_app = read("backend/app.py")

assert "LIAM_AVATAR_3D_ENABLED=false" in read(".env.example")
assert "liam-3d-renderer.js" in index
assert "@app.route('/vendor/<path:filename>')" in backend_app
assert "_project_path('frontend', 'vendor')" in backend_app
assert "avatar_3d_enabled" in controller and "gender:state.visual?.avatar_gender" in controller
assert "loadEngine" in renderer and "document.createElement('script')" in renderer
assert "liam-lector.glb" in renderer and "liam-lector-movil.glb" in renderer
assert "liam-lector-frontal.png" in renderer and "liam-mujer-v1.glb" in renderer
assert "selectedSource" in renderer and "camera-target" in renderer
assert "availableAnimations" not in renderer and "viewer.play" not in renderer
assert "LIAM_STATE?.subscribe?.(animate)" in renderer
assert "showPoster" in renderer and "liam-lector-ready" in renderer
assert "movedViewer" in movement and "viewerHome" in movement and "moveToControl" in movement
assert "liam-lector-voice-pulse" in avatar_css and "pointer-events:none" in avatar_css
assert "window.LIA_SPEECH?.speak(d.speech_text)" in controller
assert "window.LIA_SPEECH?.stop()" in controller
assert "window.LIAM_STATE?.set('speaking')" in speech
assert "speechSynthesis.speak(current)" in speech
assert "liam-lector.js" not in index and "speech-core.mjs" not in index
for guard in ("saveData", "deviceMemory", "hardwareConcurrency", "webgl2", "prefers-reduced-motion"):
    assert guard in renderer

print("LIAM_STATIC_READER_CONTRACT_V7_PASS")
