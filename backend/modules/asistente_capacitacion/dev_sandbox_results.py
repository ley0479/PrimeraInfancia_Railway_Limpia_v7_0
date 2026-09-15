"""Recepción verificable de resultados producidos por un sandbox externo."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import hmac
import json
import os
from pathlib import PurePosixPath
import re
import uuid

from modules.dbapi_compat import sqlite3

MAX_PAYLOAD_BYTES = 256 * 1024
MAX_DIFF_BYTES = 120 * 1024
MAX_TESTS = 50
REQUEST_PATTERN = re.compile(r"DEV-\d{8}-[A-F0-9]{8}")


class SandboxResultError(ValueError):
    def __init__(self, message: str, status_code: int = 422):
        super().__init__(message)
        self.status_code = status_code


def verify_signature(raw: bytes, signature: str, signing_key: str) -> None:
    if not signing_key:
        raise SandboxResultError("La recepción del sandbox no está configurada.", 503)
    supplied = str(signature or "").strip()
    if not supplied.startswith("sha256="):
        raise SandboxResultError("Firma del sandbox ausente o inválida.", 403)
    expected = hmac.new(signing_key.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(supplied[7:].lower(), expected):
        raise SandboxResultError("Firma del sandbox inválida.", 403)


def _safe_path(value: str) -> str:
    path = str(value or "").strip().replace("\\", "/")
    pure = PurePosixPath(path)
    if not path or pure.is_absolute() or ".." in pure.parts or path.startswith((".git/", ".env")):
        raise SandboxResultError("El diff contiene una ruta prohibida.")
    return str(pure)


def _diff_paths(diff: str) -> list[str]:
    paths = []
    for line in diff.splitlines():
        if not line.startswith(("+++ ", "--- ")):
            continue
        raw = line[4:].split("\t", 1)[0].strip()
        if raw == "/dev/null":
            continue
        if raw.startswith(("a/", "b/")):
            raw = raw[2:]
        normalized = _safe_path(raw)
        if normalized not in paths:
            paths.append(normalized)
    if diff.strip() and not paths:
        raise SandboxResultError("No fue posible verificar las rutas del diff unificado.")
    return paths


def ingest(database_path: str, request_id: str, tenant_id: int, user_id: int, payload: dict) -> dict:
    request_id = str(request_id or "").strip().upper()
    if not REQUEST_PATTERN.fullmatch(request_id):
        raise SandboxResultError("Identificador técnico inválido.")
    if not isinstance(payload, dict) or set(payload) - {"plan_sha256", "diff", "git_diff_check", "tests", "runner", "base_commit"}:
        raise SandboxResultError("El resultado contiene campos no permitidos.")
    plan_sha = str(payload.get("plan_sha256") or "").lower()
    if not re.fullmatch(r"[a-f0-9]{64}", plan_sha):
        raise SandboxResultError("Checksum del plan inválido.")
    diff = payload.get("diff")
    if not isinstance(diff, str) or not diff.strip():
        raise SandboxResultError("El runner debe adjuntar un diff unificado no vacío.")
    if len(diff.encode("utf-8")) > MAX_DIFF_BYTES:
        raise SandboxResultError("El diff supera el límite permitido.", 413)
    diff_check = str(payload.get("git_diff_check") or "").upper()
    if diff_check not in {"PASS", "FAIL"}:
        raise SandboxResultError("El estado de git diff --check no es válido.")
    tests = payload.get("tests")
    if not isinstance(tests, list) or not tests or len(tests) > MAX_TESTS:
        raise SandboxResultError("El resultado debe incluir entre 1 y 50 pruebas.")

    conn = sqlite3.connect(database_path); conn.row_factory = sqlite3.Row
    try:
        request_row = conn.execute(
            "SELECT request_id,status FROM lia_dev_change_requests WHERE request_id=? AND fundacion_id=? AND usuario_id=?",
            (request_id, tenant_id, user_id),
        ).fetchone()
        if not request_row:
            raise SandboxResultError("No se encontró la solicitud en la sesión activa.", 404)
        plan_row = conn.execute(
            "SELECT content_json,content_sha256 FROM lia_dev_change_artifacts WHERE request_id=? AND fundacion_id=? AND usuario_id=? AND artifact_type='SANDBOX_PLAN'",
            (request_id, tenant_id, user_id),
        ).fetchone()
        if not plan_row:
            raise SandboxResultError("La solicitud no tiene un plan de sandbox vigente.", 409)
        if not hmac.compare_digest(str(plan_row["content_sha256"]).lower(), plan_sha):
            raise SandboxResultError("El resultado no corresponde al plan de sandbox vigente.", 409)
        plan = json.loads(plan_row["content_json"])
        allowed_paths = set(plan.get("architecture", {}).get("files") or [])
        generated_test = str(plan.get("generated_test_path") or "")
        if generated_test:
            allowed_paths.add(generated_test)
        changed_paths = _diff_paths(diff)
        unexpected = sorted(set(changed_paths) - allowed_paths)
        if unexpected:
            raise SandboxResultError("El diff modifica rutas fuera del alcance aprobado: " + ", ".join(unexpected[:5]))
        allowed_tests = set(plan.get("tests") or [])
        if generated_test:
            allowed_tests.add(generated_test)
        normalized_tests = []
        for item in tests:
            if not isinstance(item, dict) or set(item) - {"test", "status", "duration_ms"}:
                raise SandboxResultError("Una prueba contiene campos no permitidos.")
            name = _safe_path(item.get("test"))
            status = str(item.get("status") or "").upper()
            try:
                duration = max(0, min(int(item.get("duration_ms") or 0), 3_600_000))
            except (TypeError, ValueError):
                raise SandboxResultError("La duración de una prueba no es válida.")
            if name not in allowed_tests:
                raise SandboxResultError("El runner reportó una prueba fuera del plan aprobado.")
            if status not in {"PASS", "FAIL"}:
                raise SandboxResultError("El estado de una prueba no es válido.")
            normalized_tests.append({"test": name, "status": status, "duration_ms": duration})
        reported_tests = [item["test"] for item in normalized_tests]
        if len(reported_tests) != len(set(reported_tests)) or set(reported_tests) != allowed_tests:
            raise SandboxResultError("El runner debe reportar exactamente todas las pruebas del plan aprobado.")
        passed = diff_check == "PASS" and all(item["status"] == "PASS" for item in normalized_tests)
        runner = re.sub(r"[^a-zA-Z0-9._-]", "", str(payload.get("runner") or "external-isolated"))[:80] or "external-isolated"
        base_commit = str(payload.get("base_commit") or "").lower()
        if base_commit and not re.fullmatch(r"[a-f0-9]{40}", base_commit):
            raise SandboxResultError("El commit base reportado por el runner no es válido.")
        content = {
            "request_id": request_id,
            "plan_sha256": plan_sha,
            "runner": runner,
            "base_commit": base_commit or None,
            "changed_paths": changed_paths,
            "git_diff_check": diff_check,
            "tests": normalized_tests,
            "diff": diff,
            "production_execution": False,
            "deployment_started": False,
        }
        encoded = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        artifact_id = "ART-" + uuid.uuid4().hex[:12].upper()
        status = "PASSED" if passed else "FAILED"
        request_status = "TESTED" if passed else "TEST_FAILED"
        now = datetime.now(ZoneInfo("America/Bogota")).isoformat(timespec="seconds")
        conn.execute(
            """INSERT INTO lia_dev_change_artifacts(artifact_id,request_id,fundacion_id,usuario_id,artifact_type,content_json,content_sha256,status,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(fundacion_id,usuario_id,request_id,artifact_type) DO UPDATE SET
               artifact_id=excluded.artifact_id,content_json=excluded.content_json,content_sha256=excluded.content_sha256,status=excluded.status,updated_at=excluded.updated_at""",
            (artifact_id, request_id, tenant_id, user_id, "SANDBOX_RESULT", encoded, digest, status, now, now),
        )
        conn.execute(
            "UPDATE lia_dev_change_requests SET status=?,updated_at=? WHERE request_id=? AND fundacion_id=? AND usuario_id=?",
            (request_status, now, request_id, tenant_id, user_id),
        )
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        conn.close()
    return {
        "request_id": request_id,
        "artifact_id": artifact_id,
        "artifact_sha256": digest,
        "status": status,
        "tests": normalized_tests,
        "changed_paths": changed_paths,
        "git_diff_check": diff_check,
        "production_execution": False,
        "deployment_started": False,
        "approval_required": True,
    }


def signing_key() -> str:
    return str(os.environ.get("LIAM_DEV_SANDBOX_SIGNING_KEY") or "")
