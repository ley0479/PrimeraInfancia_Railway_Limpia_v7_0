"""Contrato: IAN saluda al usuario autenticado antes de presentar la plataforma."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
controller = (ROOT / "frontend" / "js" / "liam" / "liam-controller.js").read_text(encoding="utf-8")
tour = (ROOT / "frontend" / "js" / "liam" / "elian-platform-tour.js").read_text(encoding="utf-8")

for contract in (
    "function authenticatedUser()",
    "function userFirstName()",
    "timeZone:'America/Bogota'",
    "Buenos días",
    "Buenas tardes",
    "Buenas noches",
    "Esta plataforma fue creada y diseñada por",
    "state.profile.designer",
    "state.profile.created_date",
    "await announceAsync(greeting);const identity=",
    "await announceAsync(identity);await presentation()",
    "state.welcomed=true",
):
    assert contract in controller, f"Falta contrato de saludo personal: {contract}"

assert controller.index("await announceAsync(greeting)") < controller.index("await announceAsync(identity)") < controller.index("await presentation()")
assert "Comencemos. Esta es" in tour
print("IAN_PERSONAL_GREETING_V7_PASS")
