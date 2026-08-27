"""Contrato ALPHA77 de /api/procesar: síncrono salvo async explícito."""
from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
APP_PATH = ROOT / "backend" / "app.py"


class Values(dict):
    def get(self, key, default=None):
        return super().get(key, default)


def load_function(name: str):
    source = APP_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    module = ast.Module(body=[node], type_ignores=[])
    namespace: dict = {}
    exec(compile(module, str(APP_PATH), "exec"), namespace)
    return namespace[name]


def request(args=None, form=None):
    return SimpleNamespace(args=Values(args or {}), form=Values(form or {}))


def test_default_is_sync() -> None:
    decide = load_function("_procesamiento_async_explicito")
    assert decide(request()) is False


def test_legacy_sync_values_remain_sync() -> None:
    decide = load_function("_procesamiento_async_explicito")
    for value in ("1", "true", "si", "sí"):
        assert decide(request(form={"sync": value})) is False
    for value in ("sincrono", "síncrono"):
        assert decide(request(args={"modo_ejecucion": value})) is False


def test_only_explicit_async_uses_job() -> None:
    decide = load_function("_procesamiento_async_explicito")
    for value in ("1", "true"):
        assert decide(request(form={"async": value})) is True
    for value in ("asincrono", "asíncrono", "segundo_plano", "masivo"):
        assert decide(request(args={"modo_ejecucion": value})) is True
    assert decide(request(form={"procesamiento_masivo": "1"})) is True


def test_sync_wins_if_clients_send_both() -> None:
    decide = load_function("_procesamiento_async_explicito")
    assert decide(request(form={"sync": "1", "async": "1"})) is False


def test_endpoint_and_frontend_contract_are_wired() -> None:
    backend = APP_PATH.read_text(encoding="utf-8")
    frontend = (ROOT / "frontend" / "js" / "app.js").read_text(encoding="utf-8")
    assert "if not async_explicito:" in backend
    assert "resultado['modo'] = 'sincrono'" in backend
    assert "'modo': 'segundo_plano_explicito'" in backend
    # El endpoint conserva compatibilidad síncrona para clientes antiguos, pero
    # la interfaz web usa jobs para evitar el timeout 502 del proxy en Railway.
    assert "formData.delete('sync')" in frontend
    assert "formData.set('async', '1')" in frontend
    assert "formData.set('modo_ejecucion', 'segundo_plano')" in frontend
    assert "xhr.status === 202 && resultado.job_id" in frontend


if __name__ == "__main__":
    test_default_is_sync()
    test_legacy_sync_values_remain_sync()
    test_only_explicit_async_uses_job()
    test_sync_wins_if_clients_send_both()
    test_endpoint_and_frontend_contract_are_wired()
    print("Procesar síncrono default v2.7.0: PASS")
