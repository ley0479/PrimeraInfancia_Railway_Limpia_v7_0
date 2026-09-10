"""Contrato: sin pago o créditos no se crea una sesión operativa."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
routes = (ROOT / "backend/modules/seguridad/routes.py").read_text(encoding="utf-8")
billing = (ROOT / "backend/modules/facturacion_suscripcion/services.py").read_text(encoding="utf-8")

start = routes.index("validate_subscription_before_session")
create = routes.index("g.error_context['stage'] = 'create_session_atomic'", start)
assert start < create, "La facturación debe validarse antes de crear el token"
for code in ("SUBSCRIPTION_MISSING", "SUBSCRIPTION_PAYMENT_REQUIRED", "CREDITS_EXHAUSTED", "BILLING_VALIDATION_UNAVAILABLE"):
    assert code in routes, f"Falta código de bloqueo: {code}"
assert "usuario['rol'] != 'SUPERADMIN'" in routes[start - 500:create]
assert "ENFORCE_LOGIN_BILLING" in routes and "ENFORCE_LOGIN_BILLING" in billing
assert "creditos_disponibles') or 0) <= 0" in billing
assert "request.path.startswith('/api/facturacion')" in billing
assert "UPDATE sesiones_usuario SET activa=0" in billing
print("LOGIN_BILLING_LOCK_V7_PASS")
