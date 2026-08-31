"""Contrato del Manual Maestro: fuente única, roles, controles y PDF."""
from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))

from modules.asistente_capacitacion.knowledge_base import load_knowledge, manual_for_role, build_manual_pdf


data = load_knowledge()
assert data["metadata"]["status"] == "verified"
assert data["metadata"]["guide_version"]
module_ids = [item["module_id"] for item in data["modules"]]
assert len(module_ids) == len(set(module_ids))
assert {"dashboard", "base-maestra", "calendario-inteligente", "formatos", "motor-plantillas", "administracion"} <= set(module_ids)

controls = [control for module in data["modules"] for control in module.get("controls", [])]
help_ids = [item["help_id"] for item in controls]
assert len(help_ids) == len(set(help_ids))
assert {"base-maestra.cuentame.upload", "formatos.rpp.download"} <= set(help_ids)

frontend_index = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
frontend_app = (ROOT / "frontend" / "js" / "app.js").read_text(encoding="utf-8")
for help_id in help_ids:
    assert help_id in frontend_index or help_id in frontend_app, f"Control sin data-help-id real: {help_id}"

teacher = manual_for_role("DOCENTE")
teacher_modules = {item["module_id"] for item in teacher["modules"]}
assert "formatos" in teacher_modules
assert "administracion" not in teacher_modules
assert "motor-plantillas" not in teacher_modules
assert any(item["workflow_id"] == "generar-rpp" for item in teacher["workflows"])

rpp_context = manual_for_role("DOCENTE", module_id="formatos", screen_id="formatos.rpp", help_id="formatos.rpp.download")
assert rpp_context["active_control"]["title"] == "Descargar RPP"
assert any(item["code"] == "RPP_NO_PARTICIPANTS" for item in rpp_context["errors"])

pdf = build_manual_pdf(teacher)
assert pdf.startswith(b"%PDF-1.4") and pdf.endswith(b"%%EOF") and len(pdf) > 1500
print("LIAM_MANUAL_MASTER_V7_PASS")
