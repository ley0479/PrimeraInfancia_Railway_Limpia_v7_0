"""Contrato del avatar 3D: opt-in, liviano, local y con respaldo 2D."""
from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from modules.asistente_capacitacion.config import public_liam_flags


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


os.environ.pop("LIAM_AVATAR_3D_ENABLED", None)
os.environ["ENABLE_LIAM_ASSISTANT"] = "true"
assert public_liam_flags()["avatar_3d_enabled"] is False
os.environ["LIAM_AVATAR_3D_ENABLED"] = "true"
assert public_liam_flags()["avatar_3d_enabled"] is True

male_model = ROOT / "frontend/assets/lia/3d/iam-hombre-v1.glb"
female_static_model = ROOT / "frontend/assets/lia/3d/liam-mujer-v1.glb"
engine = ROOT / "frontend/vendor/model-viewer/model-viewer-4.3.1.min.js"
assert male_model.is_file() and male_model.stat().st_size < 10 * 1024 * 1024
assert female_static_model.is_file() and female_static_model.stat().st_size < 10 * 1024 * 1024
assert engine.is_file() and engine.stat().st_size < 1200 * 1024

renderer = read("frontend/js/liam/liam-3d-renderer.js")
avatar_css = read("frontend/css/ian-avatar.css")
controller = read("frontend/js/liam/liam-controller.js")
index = read("frontend/index.html")
backend_app = read("backend/app.py")
assert "LIAM_AVATAR_3D_ENABLED=false" in read(".env.example")
assert "liam-3d-renderer.js" in index
assert "@app.route('/vendor/<path:filename>')" in backend_app
assert "_project_path('frontend', 'vendor')" in backend_app
assert "avatar_3d_enabled" in controller
assert "loadEngine" in renderer and "document.createElement('script')" in renderer
assert "liam-3d-ready" in renderer and "IAN_AVATAR" in read("frontend/js/liam/ian-avatar-renderer.js")
assert "liam-mujer-v1.glb" in renderer and "iam-hombre-v1.glb" in renderer
assert "texture-pbr-2" in renderer
assert "gender:state.visual?.avatar_gender" in controller
assert "shadow-intensity','0" in renderer and "viewer.pause" in renderer
assert "liam-3d-static" in renderer and "background:transparent" in avatar_css
for guard in ("saveData", "deviceMemory", "hardwareConcurrency", "webgl2", "prefers-reduced-motion"):
    assert guard in renderer
assert "LIAM_3D?.unmount" in controller
for clip in ("Idle", "Walk", "Wave", "Point", "Talk", "Listen", "Think"):
    assert clip in renderer
assert "camera-target" in renderer and "max-width: 768px" in renderer

print("LIAM_3D_PROGRESSIVE_CONTRACT_V7_PASS")
