import json
import sys
import tempfile
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from modules import operational_jobs
from modules.seguridad.tenant_context import tenant_context


def test_persisted_running_job_becomes_retryable_error_after_restart():
    with tempfile.TemporaryDirectory() as tmp:
        job_id = "reinicio12345678"
        Path(tmp, f"job_{job_id}.json").write_text(
            json.dumps(
                {
                    "id": job_id,
                    "tipo": "procesar_formatos",
                    "estado": "procesando",
                    "progreso": 45,
                    "etapa": "Generando formatos",
                    "metadata": {"fundacion_id": 7},
                    "fecha_creacion": "2026-09-23T00:00:00",
                    "fecha_actualizacion": "2026-09-23T00:01:00",
                }
            ),
            encoding="utf-8",
        )
        operational_jobs.configure(tmp)
        operational_jobs._JOBS.clear()

        with tenant_context(7, role="ADMIN", username="qa", source="request"):
            recovered = operational_jobs.get_job(job_id)

        assert recovered is not None
        assert recovered["estado"] == "error"
        assert "reinició" in recovered["error"]
        assert "Procesar unidades seleccionadas" in recovered["error"]

        with tenant_context(8, role="ADMIN", username="otra", source="request"):
            assert operational_jobs.get_job(job_id) is None


def test_frontend_stops_polling_missing_jobs_immediately():
    source = (BACKEND_DIR.parent / "frontend" / "js" / "app.js").read_text(encoding="utf-8")
    assert "Number(error?.status || 0) === 404" in source
    assert "Vuelve a pulsar Procesar unidades seleccionadas" in source
    assert "liam:operational-error" in source


def test_liam_announces_operational_errors_automatically():
    source = (BACKEND_DIR.parent / "frontend" / "js" / "liam" / "liam-controller.js").read_text(encoding="utf-8")
    assert 'addEventListener("liam:operational-error"' in source
    assert 'open();' in source
    assert 'window.LIA_SPEECH?.speak(message)' in source
