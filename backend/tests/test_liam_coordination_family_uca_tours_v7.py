"""Contrato LIAM para coordinación, familias y expediente operativo UCA."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
read = lambda relative: (ROOT / relative).read_text(encoding="utf-8")

controls = read("frontend/js/liam/liam-control-registry.js")
anchors = read("frontend/js/liam/liam-anchor-registry.js")
tours = read("frontend/js/liam/liam-tour-engine.js")
controller = read("frontend/js/liam/liam-controller.js")

for tour_id in ("gestion-coordinador.overview", "familias-redes.overview", "expediente-uca.overview"):
    assert tour_id in tours and tour_id in controller

for prefix in ("gestion-coordinador.", "familias-redes.", "expediente-uca."):
    assert prefix in controls

for anchor in ("liam.anchor.coordinator", "liam.anchor.families", "liam.anchor.uca"):
    assert anchor in anchors

assert "sin crear una asignación paralela" in tours
assert "no deben duplicarlos" in tours
assert "no copia ni duplica sus registros" in tours
assert ".click()" not in tours

print("LIAM_COORDINATION_FAMILY_UCA_TOURS_V7_PASS")
