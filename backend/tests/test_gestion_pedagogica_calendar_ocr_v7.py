from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
routes = (ROOT / "backend/modules/gestion_pedagogica/routes.py").read_text(encoding="utf-8")

assert "read_document_intelligent(Path(ruta))" in routes
assert "OCR_SIN_TEXTO" in routes
assert "OCR_SIN_FECHAS" in routes
assert "patron_numerico" in routes
assert "no se aplica OCR en este módulo" not in routes

print("GESTION_PEDAGOGICA_CALENDAR_OCR_V7_PASS")
