"""Contrato de recorridos prioritarios de LIAM y avance por eventos reales."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


html = read("frontend/index.html")
calendar = read("frontend/js/modules/calendario-inteligente.js")
controls = read("frontend/js/liam/liam-control-registry.js")
anchors = read("frontend/js/liam/liam-anchor-registry.js")
tours = read("frontend/js/liam/liam-tour-engine.js")
controller = read("frontend/js/liam/liam-controller.js")
idp = read("frontend/js/modules/idp-documental.js")
context = read("frontend/js/liam/liam-context-collector.js")

for help_id in (
    "base-maestra.file.upload",
    "base-maestra.units.search",
    "motor-documental.file.select",
    "motor-documental.file.upload",
    "formatos.template.type",
    "formatos.template.file",
    "formatos.template.save",
):
    assert f'data-help-id="{help_id}"' in html

for help_id in (
    "calendario.activity.create",
    "calendario.schedule.upload",
    "calendario.view.month",
    "calendario.pending.list",
    "calendario.alerts.list",
):
    assert f'data-help-id="{help_id}"' in calendar

for tour_id in (
    "base-maestra.first-upload",
    "calendario.overview",
    "motor-documental.first-read",
    "formatos.template-registration",
):
    assert tour_id in tours

assert "base-file-selected" in tours and "document-received" in tours
assert "liam:business-event" in controller and "liam:business-event" in idp
assert "querySelector(item.selector)" in controls
assert "devices.includes(device())" in anchors
assert "modal_id" in context and "tab_id" in context
for forbidden in ("eval(", "new Function", "document.write"):
    assert forbidden not in tours
    assert forbidden not in context

print("LIAM_PRIORITY_TOURS_V7_PASS")
