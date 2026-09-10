"""Migración, backfill e idempotencia del libro mayor de créditos v7."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile

from flask import Flask
from sqlalchemy import text


BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from database import database
from migrations.migrate_credit_ledger_v7 import migrate
from modules.facturacion_suscripcion.repository import BillingRepository
from modules.facturacion_suscripcion.services import BillingService


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pi_credit_ledger_", ignore_cleanup_errors=True) as raw:
        db_path = Path(raw) / "credits.sqlite3"
        app = Flask(__name__)
        app.config.update(
            DATABASE_URL=f"sqlite:///{db_path.as_posix()}",
            DATABASE_PATH=str(db_path),
            SQLALCHEMY_ENGINE_OPTIONS={},
        )
        database.configure(app)
        with app.app_context():
            with database.transaction() as conn:
                conn.execute(text("""CREATE TABLE fundaciones (
                    id INTEGER PRIMARY KEY, nombre TEXT NOT NULL,
                    fecha_inicio TEXT, fecha_vencimiento TEXT, plan_id INTEGER,
                    suscripcion_estado TEXT, creditos_disponibles INTEGER DEFAULT 0,
                    fecha_actualizacion TEXT)"""))
                conn.execute(text("""CREATE TABLE sesiones_usuario (
                    id INTEGER PRIMARY KEY, usuario_id INTEGER, fundacion_id INTEGER,
                    activa INTEGER DEFAULT 1, fecha_cierre TEXT)"""))
                conn.execute(text("""INSERT INTO fundaciones
                    (id,nombre,fecha_inicio,fecha_vencimiento,creditos_disponibles)
                    VALUES (1,'Fundación Prueba','2026-08-01','2026-09-01',150)"""))

            repo = BillingRepository(str(db_path))
            service = BillingService(repo)
            service.init(force=True)
            before = service.get_subscription(1)

            first = migrate(str(db_path))
            second = migrate(str(db_path))
            assert first["credits_schema_version"] == 1
            assert second["opening_movements"] == 0
            openings = repo.fetch_all(
                "SELECT * FROM movimientos_credito WHERE fundacion_id=? AND tipo='ASIGNACION_INICIAL'", (1,)
            )
            assert len(openings) == 1
            assert int(openings[0]["saldo_nuevo"]) == int(before["creditos_disponibles"])

            movement_1 = service.asignar_creditos({
                "fundacion_id": 1, "creditos": 25,
                "idempotency_key": "test-assignment-1",
            })
            movement_2 = service.asignar_creditos({
                "fundacion_id": 1, "creditos": 25,
                "idempotency_key": "test-assignment-1",
            })
            assert movement_1["id"] == movement_2["id"]
            after_assignment = service.get_subscription(1)
            assert int(after_assignment["creditos_disponibles"]) == int(before["creditos_disponibles"]) + 25

            consumption_1 = service.consumir_creditos(
                1, "exportacion_masiva", idempotency_key="test-consumption-1"
            )
            consumption_2 = service.consumir_creditos(
                1, "exportacion_masiva", idempotency_key="test-consumption-1"
            )
            assert consumption_1["id"] == consumption_2["id"]
            final = service.get_subscription(1)
            assert int(final["creditos_disponibles"]) == int(before["creditos_disponibles"]) + 20
            assert int(final["creditos_totales"]) == int(before["creditos_disponibles"]) + 25
            assert int(final["creditos_consumidos"]) == 5
            assert 0 <= float(final["porcentaje_consumido"]) <= 100
            assert int(final["dias_totales"]) >= 0
            assert "porcentaje_tiempo_consumido" in final
            assert "estado_creditos" in final
            alerts = service.subscription_alerts(final)
            assert len({(item["tipo"], item["umbral"]) for item in alerts}) == len(alerts)

            config_source = (BACKEND / "config.py").read_text(encoding="utf-8")
            middleware_source = (BACKEND / "modules" / "facturacion_suscripcion" / "services.py").read_text(encoding="utf-8")
            assert 'ENABLE_CREDIT_ENFORCEMENT", False' in config_source
            assert "Idempotency-Key" in middleware_source
            assert "automatic_charge_failed" in middleware_source
            assert "UPDATE sesiones_usuario SET activa=0" in middleware_source
            assert int(repo.fetch_one(
                "SELECT COUNT(*) AS total FROM movimientos_credito WHERE fundacion_id=? AND idempotency_key=?",
                (1, "test-consumption-1"),
            )["total"]) == 1

            last = repo.fetch_one(
                "SELECT saldo_nuevo FROM movimientos_credito WHERE fundacion_id=? ORDER BY id DESC LIMIT 1", (1,)
            )
            assert int(last["saldo_nuevo"]) == int(final["creditos_disponibles"])
            database.dispose()

    print("Libro mayor créditos y resumen visual: migración x2, idempotencia, métricas y reconciliación PASS")


if __name__ == "__main__":
    main()
