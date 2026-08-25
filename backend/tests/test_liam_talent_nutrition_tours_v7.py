"""Contrato de recorridos seguros para Talento Humano y Salud y Nutrición."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


html = read("frontend/index.html")
controls = read("frontend/js/liam/liam-control-registry.js")
anchors = read("frontend/js/liam/liam-anchor-registry.js")
tours = read("frontend/js/liam/liam-tour-engine.js")
controller = read("frontend/js/liam/liam-controller.js")

for help_id in (
    "talento.file.select", "talento.file.upload", "talento.sync.global",
    "talento.manual.save", "talento.people.list",
    "salud-nutricion.tab.dashboard", "salud-nutricion.tab.integral",
    "salud-nutricion.tab.alertas", "salud-nutricion.tab.entregables",
    "salud-nutricion.integral.unit-filter", "salud-nutricion.alerts.refresh",
):
    assert help_id in html
    assert help_id in controls

for tour_id in ("talento.overview", "salud-nutricion.overview"):
    assert tour_id in tours
    assert tour_id in controller

assert "talent-file-selected" in tours
assert "talent-file-selected" in controller
assert "liam.anchor.talent" in anchors
assert "liam.anchor.nutrition" in anchors
assert "Una alerta no constituye por sí sola un diagnóstico" in tours
assert ".click()" not in tours

print("LIAM_TALENT_NUTRITION_TOURS_V7_PASS")
