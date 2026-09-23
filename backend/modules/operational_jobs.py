"""Gestor liviano de trabajos operativos en segundo plano.

Alpha24: evita timeouts 524 en túnel Cloudflare/ngrok moviendo tareas largas
(carga de base Cuéntame, generación de formatos y cronogramas) a jobs
consultables por /api/jobs/<job_id>.
"""
from __future__ import annotations

import json
import os
import threading
import time
import traceback
import uuid
from datetime import datetime
from typing import Any, Callable

from modules.seguridad.tenant_context import (
    capture_tenant_context,
    current_tenant_context,
    tenant_context,
)

_LOCK = threading.RLock()
_JOBS: dict[str, dict[str, Any]] = {}
_LOG_DIR: os.PathLike[str] | str | None = None
_MAX_LOGS = 200


def configure(log_dir: os.PathLike[str] | str | None = None) -> None:
    """Configura carpeta de logs de jobs. No falla si no puede crearla."""
    global _LOG_DIR
    _LOG_DIR = log_dir
    if _LOG_DIR:
        try:
            os.makedirs(os.fspath(_LOG_DIR), exist_ok=True)
        except Exception:
            # La ruta puede ser dinámica por tenant y no estar disponible hasta
            # que exista un contexto autenticado. Se conserva para resolverla
            # al escribir el primer log.
            pass


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _public_job(job: dict[str, Any], include_result: bool = True) -> dict[str, Any]:
    data = {k: v for k, v in job.items() if k not in {"thread"}}
    if not include_result and "resultado" in data:
        data["resultado"] = None
    return data


def _write_job_log(job: dict[str, Any], include_result: bool = False) -> None:
    if not _LOG_DIR:
        return
    try:
        log_dir = os.fspath(_LOG_DIR)
        os.makedirs(log_dir, exist_ok=True)
        path = os.path.join(log_dir, f"job_{job['id']}.json")
        data = _public_job(job, include_result=include_result)
        # El resultado puede contener miles de beneficiarios; para el archivo se evita
        # guardar un JSON pesado, pero la respuesta en memoria sí conserva el resultado.
        if not include_result and data.get("resultado") is None:
            data.pop("resultado", None)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2, default=str)
    except Exception:
        pass


def _read_job_log(job_id: str) -> dict[str, Any] | None:
    """Recupera el estado persistido cuando el proceso web fue reiniciado."""
    if not _LOG_DIR or not str(job_id).isalnum():
        return None
    try:
        path = os.path.join(os.fspath(_LOG_DIR), f"job_{job_id}.json")
        with open(path, "r", encoding="utf-8") as fh:
            job = json.load(fh)
        if not isinstance(job, dict) or str(job.get("id")) != str(job_id):
            return None

        if job.get("estado") in {"pendiente", "procesando"}:
            job["estado"] = "error"
            job["etapa"] = "Interrumpido por reinicio del servicio"
            job["error"] = (
                "El servicio se reinició mientras generaba los formatos. "
                "Vuelve a pulsar Procesar unidades seleccionadas."
            )
            job["fecha_fin"] = _now()
            job["fecha_actualizacion"] = _now()
            _write_job_log(job, include_result=False)
        elif job.get("estado") == "completado" and not job.get("resultado"):
            # Los resultados grandes solo viven en memoria. Después de reiniciar
            # no se puede reconstruir con seguridad el archivo de descarga.
            job["estado"] = "error"
            job["etapa"] = "Resultado expirado"
            job["error"] = (
                "El resultado expiró después de reiniciar el servicio. "
                "Vuelve a procesar la selección."
            )
        return job
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None


def _append_log(job: dict[str, Any], message: str) -> None:
    logs = job.setdefault("logs", [])
    logs.append({"fecha": _now(), "mensaje": str(message)[:1000]})
    if len(logs) > _MAX_LOGS:
        del logs[:-_MAX_LOGS]


def _job_visible(job: dict[str, Any]) -> bool:
    context = current_tenant_context()
    if context.allow_global and context.role == "SUPERADMIN":
        return True
    tenant_id = context.tenant_id
    job_tenant = (job.get("metadata") or {}).get("fundacion_id")
    if tenant_id is None:
        # Los procesos internos sin usuario pueden inspeccionar jobs del sistema.
        return context.source == "background" and context.role == "SYSTEM"
    try:
        return int(job_tenant or 0) == int(tenant_id)
    except (TypeError, ValueError):
        return False


def get_job(job_id: str) -> dict[str, Any] | None:
    with _LOCK:
        job = _JOBS.get(str(job_id))
        if not job:
            job = _read_job_log(str(job_id))
            if job:
                _JOBS[str(job_id)] = job
        return _public_job(job) if job and _job_visible(job) else None


def list_jobs(limit: int = 50) -> list[dict[str, Any]]:
    with _LOCK:
        jobs = sorted(_JOBS.values(), key=lambda j: j.get("fecha_creacion", ""), reverse=True)
        visible = [job for job in jobs if _job_visible(job)]
        return [_public_job(j, include_result=False) for j in visible[:limit]]


def _cleanup_old_jobs(max_age_seconds: int = 3600 * 8, keep: int = 100) -> None:
    now_ts = time.time()
    with _LOCK:
        finished = [
            (job_id, job)
            for job_id, job in _JOBS.items()
            if job.get("estado") in {"completado", "error", "cancelado"}
        ]
        finished.sort(key=lambda item: item[1].get("fecha_actualizacion", ""), reverse=True)
        protected = {job_id for job_id, _ in finished[:keep]}
        for job_id, job in finished[keep:]:
            if job_id not in protected:
                _JOBS.pop(job_id, None)
                continue
            started = float(job.get("_ts", now_ts))
            if now_ts - started > max_age_seconds:
                _JOBS.pop(job_id, None)


def start_job(
    tipo: str,
    target: Callable[[Callable[..., None]], Any],
    metadata: dict[str, Any] | None = None,
    descripcion: str | None = None,
) -> dict[str, Any]:
    """Inicia un trabajo en segundo plano.

    target recibe update(**kwargs), por ejemplo:
        update(progreso=40, etapa="Generando formatos")
    El resultado retornado por target queda en job["resultado"].
    """
    _cleanup_old_jobs()
    captured = capture_tenant_context()
    job_id = uuid.uuid4().hex[:16]
    job_metadata = dict(metadata or {})
    if captured.tenant_id:
        job_metadata["fundacion_id"] = int(captured.tenant_id)
    job_metadata.setdefault("usuario", captured.username)
    job_metadata.setdefault("rol", captured.role)
    job = {
        "id": job_id,
        "tipo": tipo,
        "descripcion": descripcion or tipo,
        "estado": "pendiente",
        "progreso": 0,
        "etapa": "En cola",
        "resultado": None,
        "error": None,
        "traceback": None,
        "metadata": job_metadata,
        "logs": [],
        "fecha_creacion": _now(),
        "fecha_inicio": None,
        "fecha_fin": None,
        "fecha_actualizacion": _now(),
        "_ts": time.time(),
    }

    def update(**kwargs: Any) -> None:
        with _LOCK:
            current = _JOBS.get(job_id)
            if not current:
                return
            for key, value in kwargs.items():
                if key in {"log", "mensaje"}:
                    _append_log(current, str(value))
                elif key == "logs" and isinstance(value, (list, tuple)):
                    for item in value:
                        _append_log(current, str(item))
                else:
                    current[key] = value
            current["fecha_actualizacion"] = _now()
            _write_job_log(current, include_result=False)

    def runner() -> None:
        with tenant_context(
            captured.tenant_id,
            role=captured.role,
            username=captured.username,
            allow_global=captured.allow_global,
            source=f"job:{job_id}",
        ):
            with _LOCK:
                job["estado"] = "procesando"
                job["fecha_inicio"] = _now()
                job["etapa"] = "Iniciando"
                job["fecha_actualizacion"] = _now()
                _write_job_log(job, include_result=False)
            try:
                result = target(update)
                with _LOCK:
                    job["estado"] = "completado"
                    job["progreso"] = 100
                    job["etapa"] = "Completado"
                    job["resultado"] = result
                    job["fecha_fin"] = _now()
                    job["fecha_actualizacion"] = _now()
                    _write_job_log(job, include_result=False)
            except Exception as exc:  # pragma: no cover - cubierto por integración manual
                tb = traceback.format_exc()
                with _LOCK:
                    job["estado"] = "error"
                    job["error"] = str(exc)
                    job["traceback"] = tb[-6000:]
                    job["etapa"] = "Error"
                    job["fecha_fin"] = _now()
                    job["fecha_actualizacion"] = _now()
                    _append_log(job, str(exc))
                    _write_job_log(job, include_result=False)

    thread = threading.Thread(target=runner, name=f"PrimeraInfanciaJob-{job_id}", daemon=True)
    job["thread"] = thread
    with _LOCK:
        _JOBS[job_id] = job
    thread.start()
    return _public_job(job, include_result=False)
