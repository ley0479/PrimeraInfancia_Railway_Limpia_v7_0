"""Contrato de la presentación institucional navegable de LIAM."""
from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from modules.asistente_capacitacion.platform_profile import get_platform_profile


def read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


os.environ["LIA_PLATFORM_DESIGNER"] = "Profesional confirmado"
os.environ["LIA_PLATFORM_CREATED_DATE"] = "2026-06-04"
profile = get_platform_profile()
assert profile["name"] == "Plataforma Primera Infancia"
assert profile["identity_confirmed"] is True
assert profile["designer"] == "Profesional confirmado"
assert profile["created_date"] == "2026-06-04"

engine = read("frontend/js/liam/liam-tour-engine.js")
controller = read("frontend/js/liam/liam-controller.js")
routes = read("backend/modules/asistente_capacitacion/routes.py")

assert "startPresentation" in engine
assert "modules.map" in engine
assert "workflow.map" in engine
assert "platform_presentation_enabled" in controller
assert "LIAM_TOURS?.startPresentation" in controller
assert "ROLE_MENU_PERMISSIONS" in routes
assert "modules.append" in routes
for forbidden in ("eval(", "new Function", "innerHTML="):
    assert forbidden not in engine

print("LIAM_PLATFORM_PRESENTATION_V7_PASS")
