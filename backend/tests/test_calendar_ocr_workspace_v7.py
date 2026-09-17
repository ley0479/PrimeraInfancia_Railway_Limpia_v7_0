from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
frontend = (ROOT / "frontend/js/modules/calendario-inteligente.js").read_text(encoding="utf-8")
styles = (ROOT / "frontend/css/calendario-inteligente.css").read_text(encoding="utf-8")
index = (ROOT / "frontend/index.html").read_text(encoding="utf-8")

for token in (
    "ci-upload-workspace",
    "ci-upload-dropzone",
    "ci-camera-file",
    "capture=\"environment\"",
    "ci-ocr-progress",
    "ciPrepararCronograma",
    "ciCronogramaDrop",
    "Leer y detectar actividades",
):
    assert token in frontend, token

assert ".ci-upload-layout" in styles
assert ".ci-upload-visual img" in styles
assert "calendario-inteligente.css?v=2.7.6-ocr-auto-calendar-2" in index
assert "calendario-inteligente.js?v=2.7.6-ocr-auto-calendar-2" in index
assert "fd.append('auto_confirmar', 'true')" in frontend

print("CALENDAR_OCR_WORKSPACE_V7_PASS")
