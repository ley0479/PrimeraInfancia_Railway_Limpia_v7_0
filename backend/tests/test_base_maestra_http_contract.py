from __future__ import annotations

import os
import sys
import tempfile
from io import BytesIO
from pathlib import Path

from flask import Flask

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from modules.base_maestra import routes


EXPECTED = {
    "/api/base-maestra/resumen": {"GET"},
    "/api/base-maestra/cargar-fuente": {"POST"},
    "/api/base-maestra/validar": {"POST"},
    "/api/base-maestra/consolidar": {"POST"},
    "/api/base-maestra/publicar": {"POST"},
    "/api/base-maestra/inconsistencias/descargar": {"GET"},
    "/api/base-maestra/unidad-registros/descargar": {"GET"},
}


def main() -> None:
    previous = os.environ.get("SKIP_RUNTIME_SCHEMA_DDL")
    original = routes.BaseMaestraRepository.init_schema
    service_names = [
        "require_roles", "dashboard_base_maestra", "guardar_fuente",
        "validar_fuentes_pendientes", "consolidar_base_maestra",
        "publicar_base_maestra",
    ]
    originals = {name: getattr(routes, name) for name in service_names}
    calls = []
    os.environ["SKIP_RUNTIME_SCHEMA_DDL"] = "1"
    routes.BaseMaestraRepository.init_schema = lambda self: calls.append(self.database_path)
    routes.require_roles = lambda *roles: (lambda function: function)
    routes.dashboard_base_maestra = lambda database_path: {"ok": True, "borradores": []}
    routes.guardar_fuente = lambda *args, **kwargs: {"ok": True, "carga_id": 1}
    routes.validar_fuentes_pendientes = lambda database_path: {"ok": True, "total_validaciones": 1}
    routes.consolidar_base_maestra = lambda *args, **kwargs: {"ok": True, "version_id": 1}
    routes.publicar_base_maestra = lambda *args, **kwargs: {"ok": True, "version_id": 1}
    try:
        with tempfile.TemporaryDirectory(prefix="pi-base-maestra-contract-") as temp:
            app = Flask(__name__)
            routes.register_base_maestra(app, str(Path(temp) / "db.sqlite3"), temp, temp)
            rules = {rule.rule: set(rule.methods or ()) for rule in app.url_map.iter_rules()}
            for path, methods in EXPECTED.items():
                assert path in rules, f"Ruta no registrada: {path}"
                assert methods <= rules[path], f"Método incorrecto en {path}: {rules[path]}"
            assert calls == [], "El worker ejecutó DDL aunque SKIP_RUNTIME_SCHEMA_DDL está activo."
            client = app.test_client()
            assert client.get("/api/base-maestra/resumen").status_code == 200
            assert client.post(
                "/api/base-maestra/cargar-fuente",
                data={"tipo_fuente": "cuentame", "file": (BytesIO(b"fixture"), "base.xlsx")},
                content_type="multipart/form-data",
            ).status_code == 201
            assert client.post("/api/base-maestra/validar", json={}).status_code == 200
            assert client.post("/api/base-maestra/consolidar", json={}).status_code == 201
            assert client.post("/api/base-maestra/publicar", json={"version_id": 1}).status_code == 200
    finally:
        routes.BaseMaestraRepository.init_schema = original
        for name, value in originals.items():
            setattr(routes, name, value)
        if previous is None:
            os.environ.pop("SKIP_RUNTIME_SCHEMA_DDL", None)
        else:
            os.environ["SKIP_RUNTIME_SCHEMA_DDL"] = previous
    print("BASE_MAESTRA_HTTP_CONTRACT_PASS")


if __name__ == "__main__":
    main()
