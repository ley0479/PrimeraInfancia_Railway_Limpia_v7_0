#!/usr/bin/env python3
"""Validador reproducible del paquete PrimeraInfancia para Railway.

No requiere Flask ni las dependencias pesadas de producción. Comprueba contenido,
sintaxis, manifiestos, esquema SQLite y comportamiento crítico de bootstrap con
módulos mínimos de prueba. La prueba integral del contenedor sigue siendo obligatoria.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import types
import zipfile
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"

RESULTS: list[dict[str, Any]] = []


def is_release_path(path: Path) -> bool:
    """Indica si el archivo pertenece al paquete distribuible.

    El repositorio de trabajo puede contener ``.git`` mientras se desarrolla, pero
    ese directorio nunca forma parte del ZIP ni de su manifiesto.
    """
    try:
        relative = path.relative_to(ROOT)
    except ValueError:
        return False
    return ".git" not in relative.parts


def release_files() -> list[Path]:
    return [path for path in ROOT.rglob("*") if path.is_file() and is_release_path(path)]


def record(name: str, passed: bool, detail: str = "", *, skipped: bool = False) -> None:
    status = "SKIP" if skipped else ("PASS" if passed else "FAIL")
    RESULTS.append({"name": name, "status": status, "detail": detail})
    print(f"[{status}] {name}" + (f": {detail}" if detail else ""))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def text_files() -> list[Path]:
    allowed = {
        ".py", ".js", ".html", ".css", ".json", ".md", ".txt", ".sh",
        ".toml", ".yml", ".yaml", ".ini", ".mako", ".example",
    }
    special = {"Dockerfile", ".gitignore", ".dockerignore", ".env.example"}
    return [
        path for path in release_files()
        if path.suffix.lower() in allowed or path.name in special
    ]


def check_layout() -> None:
    required = [
        "Dockerfile", "railway.json", "start_hosting.sh", ".env.example",
        "README_RAILWAY.md", "VALIDACION_Y_CAMBIOS.md", "MANIFEST_SHA256.txt",
        "INFORME_IMPLEMENTACION_GESTION_INTEGRAL_UCA_v2_5_0.md",
        "GUIA_PRUEBA_GESTION_INTEGRAL_UCA_v2_5_0.md",
        "PLAN_EVOLUCION_PRIMERA_INFANCIA_POST_v2_5_0.md",
        "ARCHIVOS_MODIFICADOS_PRIMERA_INFANCIA_v2_5_0.md",
        "PRIVACIDAD_PRIMERA_INFANCIA_v2_5_0.json",
        "INFORME_AUDITORIA_AUTENTICACION_v2_5_1.md",
        "GUIA_PRUEBAS_AUTENTICACION_v2_5_1.md",
        "ARCHIVOS_MODIFICADOS_PRIMERA_INFANCIA_v2_5_1.md",
        "RESULTADOS_AUTH_CONCURRENCIA_v2_5_1.json",
        "PRIVACIDAD_PRIMERA_INFANCIA_v2_5_1.json",
        "INFORME_IMPLEMENTACION_EXPEDIENTE_UCA_CENTRAL_v2_5_2.md",
        "GUIA_PRUEBA_EXPEDIENTE_UCA_CENTRAL_v2_5_2.md",
        "ARQUITECTURA_EXPEDIENTE_UCA_CENTRAL_v2_5_2.md",
        "ARCHIVOS_MODIFICADOS_PRIMERA_INFANCIA_v2_5_2.md",
        "PRIVACIDAD_PRIMERA_INFANCIA_v2_5_2.json",
        "INFORME_IMPLEMENTACION_BIBLIOTECA_MOTOR_GESTION_v2_5_3.md",
        "ARQUITECTURA_BIBLIOTECA_MOTOR_GESTION_v2_5_3.md",
        "GUIA_PRUEBA_BIBLIOTECA_MOTOR_GESTION_v2_5_3.md",
        "ARCHIVOS_MODIFICADOS_PRIMERA_INFANCIA_v2_5_3.md",
        "RESULTADOS_BIBLIOTECA_MOTOR_GESTION_v2_5_3.json",
        "PRIVACIDAD_PRIMERA_INFANCIA_v2_5_3.json",
        "INFORME_IMPLEMENTACION_SUPERVISION_FAMILIAS_REDES_v2_5_4.md",
        "ARQUITECTURA_SUPERVISION_FAMILIAS_REDES_v2_5_4.md",
        "GUIA_PRUEBA_SUPERVISION_FAMILIAS_REDES_v2_5_4.md",
        "ARCHIVOS_MODIFICADOS_PRIMERA_INFANCIA_v2_5_4.md",
        "RESULTADOS_SUPERVISION_FAMILIAS_REDES_v2_5_4.json",
        "PRIVACIDAD_PRIMERA_INFANCIA_v2_5_4.json",
        "INFORME_IMPLEMENTACION_SALUD_NUTRICION_POSTGRES_v2_6_0.md",
        "ARQUITECTURA_POSTGRES_SALUD_NUTRICION_v2_6_0.md",
        "GUIA_MIGRACION_SQLITE_POSTGRES_v2_6_0.md",
        "GUIA_PRUEBAS_SCRIPTS_SALUD_POSTGRES_v2_6_0.md",
        "PLAN_REVERSION_Y_CONTINGENCIA_v2_6_0.md",
        "ARCHIVOS_MODIFICADOS_PRIMERA_INFANCIA_v2_6_0.md",
        "RESULTADOS_PRUEBAS_PRIMERA_INFANCIA_v2_6_0.json",
        "PRIVACIDAD_PRIMERA_INFANCIA_v2_6_0.json",
        "INFORME_MIGRACION_POSTGRES_INTEGRIDAD_v2_6_1.md",
        "ARQUITECTURA_MOTOR_INTEGRIDAD_v2_6_1.md",
        "GUIA_MIGRACION_COMPLETA_POSTGRES_v2_6_1.md",
        "GUIA_CI_OBSERVABILIDAD_POSTGRES_v2_6_1.md",
        "PLAN_ROLLBACK_POSTGRES_v2_6_1.md",
        "ARCHIVOS_MODIFICADOS_PRIMERA_INFANCIA_v2_6_1.md",
        "RESULTADOS_PRUEBAS_PRIMERA_INFANCIA_v2_6_1.json",
        "PRIVACIDAD_PRIMERA_INFANCIA_v2_6_1.json",
        "VALIDACION_PRIMERA_INFANCIA_v2_6_1.json",
        "VALIDACION_ZIP_EXTRAIDO_PRIMERA_INFANCIA_v2_6_1.json",
        "SOURCE_ARCHIVE_SHA256.txt",
        ".github/workflows/integrity-ci.yml",
        "EJECUTAR_GATE_INTEGRIDAD.bat",
        "REPARACION_SEGURA.bat",
        "MONITOREAR_PLATAFORMA.bat",
        "MIGRAR_COMPLETO_A_POSTGRESQL.bat",
        "VERIFICAR_MIGRACION_POSTGRESQL.bat",
        "scripts_windows/ejecutar_gate_integridad.ps1",
        "scripts_windows/reparacion_segura.ps1",
        "scripts_windows/monitorear_plataforma.ps1",
        "scripts_windows/migrar_completo_postgresql.ps1",
        "integrity/baseline_v2_7_0.json",
        "integrity/critical_tests.json",
        "integrity/safe_autofix_policy.json",
        "backend/services/observability.py",
        "backend/modules/integrity_stability/__init__.py",
        "backend/modules/integrity_stability/service.py",
        "backend/modules/integrity_stability/routes.py",
        "backend/tools/integrity_gate.py",
        "backend/tools/safe_repair.py",
        "backend/tools/postgresql_preflight.py",
        "backend/tools/postgresql_runtime_audit.py",
        "backend/tools/postgresql_cutover.py",
        "backend/tools/verify_sqlite_postgresql.py",
        "backend/tools/runtime_monitor.py",
        "backend/tools/capture_integrity_baseline.py",
        "backend/tests/test_integrity_postgresql_v2_6_1.py",
        "frontend/js/modules/integrity-stability.js",
        "frontend/css/integrity-stability.css",
        "INFORME_IMPLEMENTACION_CENTRO_PLANEACION_PSICOSOCIAL_v2_7_0.md",
        "ARQUITECTURA_CENTRO_PLANEACION_PSICOSOCIAL_v2_7_0.md",
        "GUIA_PRUEBA_CENTRO_PLANEACION_PSICOSOCIAL_v2_7_0.md",
        "ARCHIVOS_MODIFICADOS_PRIMERA_INFANCIA_v2_7_0.md",
        "RESULTADOS_PRUEBAS_PRIMERA_INFANCIA_v2_7_0.json",
        "VALIDACION_PRIMERA_INFANCIA_v2_7_0.json",
        "VALIDACION_ZIP_EXTRAIDO_PRIMERA_INFANCIA_v2_7_0.json",
        "PRIVACIDAD_PRIMERA_INFANCIA_v2_7_0.json",
        "backend/modules/centro_planeacion/__init__.py",
        "backend/modules/centro_planeacion/schema.py",
        "backend/modules/centro_planeacion/services.py",
        "backend/modules/centro_planeacion/repository.py",
        "backend/modules/centro_planeacion/routes.py",
        "backend/modules/componente_psicosocial/__init__.py",
        "backend/modules/componente_psicosocial/schema.py",
        "backend/modules/componente_psicosocial/services.py",
        "backend/modules/componente_psicosocial/repository.py",
        "backend/modules/componente_psicosocial/routes.py",
        "backend/tests/test_centro_planeacion_psicosocial_v2_7_0.py",
        "frontend/js/modules/centro-planeacion.js",
        "frontend/js/modules/componente-psicosocial.js",
        "frontend/css/centro-planeacion.css",
        "frontend/css/componente-psicosocial.css",
        "CONFIGURAR_POSTGRESQL_LOCAL.bat",
        "MIGRAR_SQLITE_A_POSTGRESQL.bat",
        "RESPALDAR_POSTGRESQL.bat",
        "RESTAURAR_POSTGRESQL.bat",
        "DIAGNOSTICAR_INICIO_WINDOWS.bat",
        "scripts_windows/iniciar_plataforma.ps1",
        "scripts_windows/detener_plataforma.ps1",
        "scripts_windows/diagnosticar_inicio_windows.ps1",
        "scripts_windows/configurar_postgresql_local.ps1",
        "scripts_windows/migrar_sqlite_postgresql.ps1",
        "scripts_windows/respaldar_postgresql.ps1",
        "scripts_windows/restaurar_postgresql.ps1",
        "backend/modules/dbapi_compat.py",
        "backend/modules/salud_nutricion/integral.py",
        "backend/tools/check_database.py",
        "backend/tools/migrate_sqlite_to_postgresql.py",
        "backend/tests/test_postgresql_compat_v2_6_0.py",
        "backend/tests/test_windows_launchers_v2_6_0.py",
        "backend/tests/test_salud_nutricion_integral_v2_6_0.py",
        "backend/tests/test_migration_tool_v2_6_0.py",
        "backend/app.py", "backend/wsgi.py", "backend/init_hosting.py",
        "backend/requirements-production.txt", "frontend/index.html",
        "frontend/js/config.js", "frontend/js/app.js",
        "backend/config/uds_catalog.json",
        "backend/seed_data/config/rpp_minuta_base_2026_05.json",
        "backend/seed_data/templates_originales/oficiales/plantilla_ram_oficial_v2_historica.xlsx",
        "backend/services/uds_catalog.py", "backend/services/seed_sync.py",
        "backend/services/ram_historical_service.py",
        "backend/tests/test_operational_release_v2_3_7.py",
        "backend/tests/test_multitenant_phase3.py",
        "backend/tests/test_multitenant_release_v2_4_0.py",
        "backend/tests/test_tunnel_admin_recovery_v2_4_1.py",
        "backend/tests/test_tunnel_login_logging_v2_4_2.py",
        "backend/tests/test_tunnel_cloudflare_v2_4_3.py",
        "backend/tests/test_gestion_integral_uca_v2_5_0.py",
        "backend/tests/test_auth_concurrency_v2_5_1.py",
        "backend/modules/gestion_integral_uca/__init__.py",
        "backend/modules/gestion_integral_uca/schema.py",
        "backend/modules/gestion_integral_uca/services.py",
        "backend/modules/gestion_integral_uca/repository.py",
        "backend/modules/gestion_integral_uca/routes.py",
        "backend/modules/gestion_integral_uca/integrations.py",
        "backend/tests/test_expediente_uca_central_v2_5_2.py",
        "frontend/js/modules/gestion-integral-uca.js",
        "frontend/css/gestion-integral-uca.css",
        "backend/modules/motor_gestion_proyecto/__init__.py",
        "backend/modules/motor_gestion_proyecto/schema.py",
        "backend/modules/motor_gestion_proyecto/services.py",
        "backend/modules/motor_gestion_proyecto/repository.py",
        "backend/modules/motor_gestion_proyecto/routes.py",
        "backend/modules/gestion_integral_uca/library_updates.py",
        "backend/tests/test_biblioteca_motor_gestion_v2_5_3.py",
        "frontend/js/modules/motor-gestion-proyecto.js",
        "frontend/css/motor-gestion-proyecto.css",
        "backend/modules/supervision_calidad/__init__.py",
        "backend/modules/supervision_calidad/schema.py",
        "backend/modules/supervision_calidad/services.py",
        "backend/modules/supervision_calidad/repository.py",
        "backend/modules/supervision_calidad/routes.py",
        "backend/modules/familias_redes/__init__.py",
        "backend/modules/familias_redes/schema.py",
        "backend/modules/familias_redes/services.py",
        "backend/modules/familias_redes/repository.py",
        "backend/modules/familias_redes/routes.py",
        "backend/tests/test_supervision_familias_redes_v2_5_4.py",
        "frontend/js/modules/supervision-calidad.js",
        "frontend/js/modules/familias-redes.js",
        "frontend/css/supervision-calidad.css",
        "frontend/css/familias-redes.css",
        "scripts_windows/iniciar_tunel_cloudflare.ps1",
        "scripts_windows/diagnosticar_login_tunel.ps1",
        "DIAGNOSTICAR_LOGIN_TUNEL.bat",
        "DIAGNOSTICAR_TUNEL_CLOUDFLARE.bat",
        "ABRIR_LOGS_ERRORES.bat",
        "README_SCRIPTS_LOCAL_TUNEL.md",
        "GUIA_PRUEBAS_TUNEL_USUARIOS_RECUPERACION_v2_4_1.md",
        "INFORME_CORRECCION_LOGIN_TUNEL_Y_LOGS_v2_4_2.md",
        "GUIA_PRUEBA_LOGIN_TUNEL_v2_4_2.md",
        "ARCHIVOS_MODIFICADOS_PRIMERA_INFANCIA_v2_4_2.md",
        "INFORME_CORRECCION_TUNEL_CLOUDFLARE_v2_4_3.md",
        "GUIA_PRUEBA_TUNEL_CLOUDFLARE_v2_4_3.md",
        "ARCHIVOS_MODIFICADOS_PRIMERA_INFANCIA_v2_4_3.md",
        "backend/migrations/migrate_multitenant_phase3.py",
        "backend/modules/seguridad/tenant_context.py",
        "backend/modules/seguridad/tenant_sql_guard.py",
    ]
    missing = [item for item in required if not (ROOT / item).is_file()]
    manifest_errors: list[str] = []
    manifest_path = ROOT / "MANIFEST_SHA256.txt"
    if manifest_path.is_file():
        listed: dict[str, str] = {}
        for number, line in enumerate(manifest_path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip() or line.startswith("#"):
                continue
            match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
            if not match:
                manifest_errors.append(f"línea {number} inválida")
                continue
            digest, rel = match.groups()
            if rel.startswith("/") or "\\" in rel or ".." in Path(rel).parts:
                manifest_errors.append(f"ruta insegura: {rel}")
                continue
            listed[rel] = digest
        expected = {
            path.relative_to(ROOT).as_posix()
            for path in release_files()
            if path != manifest_path
        }
        missing_from_manifest = sorted(expected - set(listed))
        extra_in_manifest = sorted(set(listed) - expected)
        if missing_from_manifest:
            manifest_errors.append("faltan hashes: " + ", ".join(missing_from_manifest[:5]))
        if extra_in_manifest:
            manifest_errors.append("sobran hashes: " + ", ".join(extra_in_manifest[:5]))
        for rel in sorted(expected & set(listed)):
            if sha256_file(ROOT / rel) != listed[rel]:
                manifest_errors.append(f"hash inválido: {rel}")
                if len(manifest_errors) >= 10:
                    break
    detail = []
    if missing:
        detail.append("faltan: " + ", ".join(missing))
    detail.extend(manifest_errors)
    if not detail:
        detail.append(f"{len(required)} presentes; manifiesto íntegro")
    record("Archivos obligatorios", not missing and not manifest_errors, " | ".join(detail))

    symlinks = [str(path.relative_to(ROOT)) for path in ROOT.rglob("*") if path.is_symlink() and is_release_path(path)]
    record("Sin enlaces simbólicos", not symlinks, ", ".join(symlinks[:10]))

    bytecode = [
        str(path.relative_to(ROOT)) for path in ROOT.rglob("*")
        if is_release_path(path) and (path.name == "__pycache__" or path.suffix.lower() in {".pyc", ".pyo"})
    ]
    record("Sin bytecode ni cachés Python", not bytecode, ", ".join(bytecode[:10]))

    forbidden_names = {".env", "database.sqlite3", "database.db", "database.sqlite"}
    forbidden_suffixes = {".sqlite", ".sqlite3", ".db", ".log", ".bak", ".rar", ".7z"}
    forbidden = []
    for path in release_files():
        if path.name.lower() in forbidden_names or path.suffix.lower() in forbidden_suffixes:
            forbidden.append(str(path.relative_to(ROOT)))
    record("Sin bases, .env, logs ni respaldos operativos", not forbidden, ", ".join(forbidden[:10]))

    runtime_dirs = [
        "backend/uploads", "backend/archivos_actualizados", "backend/backups",
        "backend/logs", "backend/templates_originales", "backend/documentos_institucionales",
        "backend/cuentas_cobro_plantillas", "backend/storage",
    ]
    dirty: list[str] = []
    for rel in runtime_dirs:
        directory = ROOT / rel
        files = sorted(path.name for path in directory.iterdir() if path.is_file()) if directory.is_dir() else []
        dirs = sorted(path.name for path in directory.iterdir() if path.is_dir()) if directory.is_dir() else []
        if files not in ([".gitkeep"], []) or dirs:
            dirty.append(f"{rel}: files={files}, dirs={dirs}")
    record("Directorios runtime vacíos", not dirty, "; ".join(dirty[:5]))


def check_syntax() -> None:
    failures = []
    python_files = sorted(path for path in ROOT.rglob("*.py") if is_release_path(path))
    for path in python_files:
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{path.relative_to(ROOT)}: {exc}")
    record("Sintaxis Python", not failures, f"{len(python_files)} archivos" if not failures else " | ".join(failures[:5]))

    json_failures = []
    json_files = sorted(path for path in ROOT.rglob("*.json") if is_release_path(path))
    for path in json_files:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            json_failures.append(f"{path.relative_to(ROOT)}: {exc}")
    record("JSON válido", not json_failures, f"{len(json_files)} archivos" if not json_failures else " | ".join(json_failures[:5]))

    shell_files = sorted(path for path in ROOT.rglob("*.sh") if is_release_path(path))
    shell_failures = []
    bash = shutil.which("bash")
    if bash:
        try:
            for path in shell_files:
                result = subprocess.run([bash, "-n", str(path)], capture_output=True, text=True, check=False)
                if result.returncode:
                    shell_failures.append(f"{path.relative_to(ROOT)}: {result.stderr.strip()}")
            record("Sintaxis Bash", not shell_failures, f"{len(shell_files)} scripts" if not shell_failures else " | ".join(shell_failures[:5]))
        except OSError as exc:
            record("Sintaxis Bash", True, f"bash no ejecutable en este host: {type(exc).__name__}", skipped=True)
    else:
        record("Sintaxis Bash", True, "bash no disponible", skipped=True)

    js_files = sorted(path for path in ROOT.rglob("*.js") if is_release_path(path))
    node = shutil.which("node")
    js_failures = []
    if node:
        try:
            for path in js_files:
                result = subprocess.run([node, "--check", str(path)], capture_output=True, text=True, check=False)
                if result.returncode:
                    js_failures.append(f"{path.relative_to(ROOT)}: {result.stderr.strip()}")
            record("Sintaxis JavaScript", not js_failures, f"{len(js_files)} archivos" if not js_failures else " | ".join(js_failures[:5]))
        except OSError as exc:
            record("Sintaxis JavaScript", True, f"node no ejecutable en este host: {type(exc).__name__}", skipped=True)
    else:
        record("Sintaxis JavaScript", True, "node no disponible", skipped=True)


def check_manifests_and_office_files() -> None:
    seed_dir = BACKEND / "seed_data" / "templates_originales"
    manifest_path = seed_dir / "seed_manifest.json"
    failures: list[str] = []
    count = 0
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("sanitizada") is not True or manifest.get("contiene_datos_reales") is not False:
            failures.append("banderas de sanitización inválidas")
        records = manifest.get("plantillas") or []
        for entry in records:
            count += 1
            rel = entry.get("archivo")
            target = (seed_dir / str(rel)).resolve()
            if seed_dir.resolve() not in target.parents:
                failures.append(f"ruta insegura: {rel}")
                continue
            if not target.is_file():
                failures.append(f"archivo ausente: {rel}")
                continue
            if sha256_file(target) != str(entry.get("sha256") or "").lower():
                failures.append(f"hash distinto: {rel}")
            if target.stat().st_size != int(entry.get("bytes") or -1):
                failures.append(f"tamaño distinto: {rel}")
    except Exception as exc:  # noqa: BLE001
        failures.append(str(exc))
    record("Manifiesto SHA-256 de plantillas sanitizadas", not failures, f"{count} archivos" if not failures else " | ".join(failures[:8]))

    office_failures = []
    office_files = sorted(path for path in seed_dir.rglob("*") if path.suffix.lower() in {".xlsx", ".docx", ".pptx"})
    for path in office_files:
        try:
            with zipfile.ZipFile(path) as archive:
                bad = archive.testzip()
                if bad:
                    office_failures.append(f"{path.name}: miembro corrupto {bad}")
                for member in archive.namelist():
                    if member.endswith(".rels"):
                        rels = archive.read(member).decode("utf-8", "ignore")
                        if re.search(r"TargetMode=['\"]External['\"]", rels, re.I):
                            office_failures.append(f"{path.name}: relación externa en {member}")
        except Exception as exc:  # noqa: BLE001
            office_failures.append(f"{path.name}: {exc}")
    record("Integridad Office y sin relaciones externas", not office_failures, f"{len(office_files)} archivos" if not office_failures else " | ".join(office_failures[:8]))


def check_operational_assets() -> None:
    failures: list[str] = []
    try:
        catalog = json.loads((BACKEND / "config" / "uds_catalog.json").read_text(encoding="utf-8"))
        units = catalog.get("unidades") or []
        names = [str(item.get("nombre") or "").strip() for item in units]
        codes = [str(item.get("codigo_interno") or "").strip() for item in units]
        if len(units) != 32 or len(set(names)) != 32 or len(set(codes)) != 32:
            failures.append("el catálogo UDS no contiene 32 nombres y códigos únicos")
        if catalog.get("contiene_datos_personales") is not False:
            failures.append("el catálogo UDS no declara ausencia de datos personales")
        aliases = {
            str(alias).strip().upper(): str(item.get("nombre") or "").strip().upper()
            for item in units
            for alias in (item.get("alias") or [])
        }
        uds_service_text = (BACKEND / "services" / "uds_catalog.py").read_text(encoding="utf-8")
        demo_migration_present = "UNIDAD DEMO {index:02d}" in uds_service_text and "enumerate(canonical_units()" in uds_service_text
        if not demo_migration_present or aliases.get("EYAZAKE") != "EYASAKE":
            failures.append("faltan alias de migración UDS críticos")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"catálogo UDS: {exc}")

    try:
        rpp_seed = json.loads((BACKEND / "seed_data" / "config" / "rpp_minuta_base_2026_05.json").read_text(encoding="utf-8"))
        groups = rpp_seed.get("grupos") or []
        product_count = sum(len(group.get("productos") or []) for group in groups)
        if len(groups) != 4 or product_count != 49:
            failures.append(f"semilla RPP incompleta: {len(groups)} grupos, {product_count} productos")
        if rpp_seed.get("contiene_datos_personales") is not False:
            failures.append("semilla RPP no declara ausencia de datos personales")
        rpp_service_text = (BACKEND / "services" / "rpp_minutas_service.py").read_text(encoding="utf-8")
        tree = ast.parse(rpp_service_text)
        equivalence_count = None
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "DEFAULT_EQUIVALENCIAS" for target in node.targets):
                if isinstance(node.value, ast.Dict):
                    equivalence_count = len(node.value.keys)
                break
        if equivalence_count != 17:
            failures.append(f"se esperaban 17 equivalencias RPP y hay {equivalence_count}")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"semilla RPP: {exc}")

    try:
        templates = json.loads((BACKEND / "seed_data" / "templates_originales" / "oficiales" / "templates_manifest.json").read_text(encoding="utf-8"))
        versions = ((templates.get("ram") or {}).get("versiones") or [])
        by_version = {str(item.get("version")): item for item in versions}
        if set(by_version) != {"2", "3"}:
            failures.append("RAM no declara exactamente las versiones V2 y V3")
        elif by_version["2"].get("fecha_vigencia_fin") != "2026-07-31" or by_version["3"].get("fecha_vigencia") != "2026-08-01":
            failures.append("vigencias RAM V2/V3 incorrectas")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"versionado RAM: {exc}")

    app_text = (BACKEND / "app.py").read_text(encoding="utf-8", errors="ignore")
    frontend_text = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8", errors="ignore")
    frontend_js = (ROOT / "frontend" / "js" / "app.js").read_text(encoding="utf-8", errors="ignore")
    for token, label in [
        ("def resolver_url_publica", "resolución Railway"),
        ("/api/acceso/storage-health", "diagnóstico /data"),
        ("/api/formatos/diagnostico", "diagnóstico previo de formatos"),
    ]:
        if token not in app_text:
            failures.append(f"falta {label}")
    access_js = (ROOT / "frontend" / "js" / "modules" / "acceso-compartido.js").read_text(encoding="utf-8", errors="ignore")
    if "Diagnóstico previo de formatos" not in frontend_text or "diagnosticarFormatosSeleccionados" not in frontend_js:
        failures.append("el diagnóstico previo no está conectado en la interfaz")
    if "Comprobar /data" not in frontend_text or "accesoProbarAlmacenamiento" not in access_js:
        failures.append("el diagnóstico de volumen no está conectado en Acceso Compartido")

    record(
        "Activos operativos UDS/RPP/RAM y diagnósticos",
        not failures,
        "32 UDS, 4 grupos/49 productos/17 equivalencias RPP, RAM V2/V3 y UI diagnóstica" if not failures else " | ".join(failures),
    )


def extract_routes() -> tuple[list[tuple[str, str, str, int]], list[str]]:
    routes: list[tuple[str, str, str, int]] = []
    parse_errors: list[str] = []
    for path in sorted(BACKEND.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except Exception as exc:  # noqa: BLE001
            parse_errors.append(f"{path.relative_to(ROOT)}: {exc}")
            continue
        blueprints: dict[str, str] = {}
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            value = node.value
            if not isinstance(value, ast.Call) or not isinstance(value.func, ast.Name) or value.func.id != "Blueprint":
                continue
            prefix = ""
            for keyword in value.keywords:
                if keyword.arg == "url_prefix" and isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
                    prefix = keyword.value.value
            for target in targets:
                if isinstance(target, ast.Name):
                    blueprints[target.id] = prefix
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                    continue
                route_method = decorator.func.attr
                if route_method not in {"route", "get", "post", "put", "patch", "delete"}:
                    continue
                if not decorator.args or not isinstance(decorator.args[0], ast.Constant) or not isinstance(decorator.args[0].value, str):
                    continue
                owner = decorator.func.value.id if isinstance(decorator.func.value, ast.Name) else "?"
                route = decorator.args[0].value
                if owner != "app":
                    route = blueprints.get(owner, "") + route
                methods: list[str] = []
                if route_method == "route":
                    for keyword in decorator.keywords:
                        if keyword.arg == "methods" and isinstance(keyword.value, (ast.List, ast.Tuple)):
                            methods = [str(item.value) for item in keyword.value.elts if isinstance(item, ast.Constant)]
                else:
                    methods = [route_method.upper()]
                routes.append((route, ",".join(methods or ["GET"]), str(path.relative_to(ROOT)), node.lineno))
    return routes, parse_errors


def declared_role_prefixes() -> list[str]:
    path = BACKEND / "modules" / "seguridad" / "services.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "PATH_ROLE_RULES" for target in node.targets):
            continue
        call = node.value
        sequence = call.args[0] if isinstance(call, ast.Call) and call.args else None
        if not isinstance(sequence, (ast.List, ast.Tuple)):
            return []
        return [
            str(item.elts[0].value)
            for item in sequence.elts
            if isinstance(item, (ast.Tuple, ast.List)) and item.elts and isinstance(item.elts[0], ast.Constant)
        ]
    return []


def declared_public_routes() -> tuple[set[str], tuple[str, ...]]:
    """Lee las excepciones públicas reales sin importar Flask ni la aplicación."""
    path = BACKEND / "modules" / "seguridad" / "services.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    exact: set[str] = set()
    prefixes: tuple[str, ...] = ()
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        names = {target.id for target in node.targets if isinstance(target, ast.Name)}
        if "PUBLIC_PATHS" in names and isinstance(node.value, (ast.Set, ast.List, ast.Tuple)):
            exact = {str(item.value) for item in node.value.elts if isinstance(item, ast.Constant) and isinstance(item.value, str)}
        if "PUBLIC_PATH_PREFIXES" in names and isinstance(node.value, (ast.List, ast.Tuple)):
            prefixes = tuple(str(item.value) for item in node.value.elts if isinstance(item, ast.Constant) and isinstance(item.value, str))
    return exact, prefixes


def check_route_authorization() -> None:
    routes, parse_errors = extract_routes()
    prefixes = sorted(declared_role_prefixes(), key=len, reverse=True)
    public_exact, public_prefixes = declared_public_routes()

    def covered(route: str) -> str | None:
        normalized = route.rstrip("/") or "/"
        return next((prefix for prefix in prefixes if normalized == prefix or normalized.startswith(prefix + "/")), None)

    api_routes = [item for item in routes if item[0].startswith("/api/")]
    unknown = [item for item in api_routes if item[0] not in public_exact and not any(item[0].startswith(prefix) for prefix in public_prefixes) and not covered(item[0])]
    detail = f"{len(api_routes)} rutas API, {len(prefixes)} familias y {len(public_exact)+len(public_prefixes)} excepciones públicas declaradas"
    if parse_errors:
        detail += "; errores AST: " + " | ".join(parse_errors[:3])
    if unknown:
        detail += "; sin regla: " + " | ".join(f"{r[0]} ({r[2]}:{r[3]})" for r in unknown[:10])
    record("Cobertura de autorización por roles", not parse_errors and not unknown, detail)


def install_test_stubs() -> None:
    """Instala únicamente las superficies usadas por services.py en pruebas SQLite."""
    flask = types.ModuleType("flask")

    class DummyCurrentApp:
        config: dict[str, Any] = {}

    class DummyRequest:
        headers: dict[str, str] = {}
        args: dict[str, str] = {}
        form: dict[str, str] = {}
        cookies: dict[str, str] = {}
        remote_addr = "127.0.0.1"
        path = "/"
        method = "GET"
        is_secure = False

    flask.current_app = DummyCurrentApp()
    flask.g = types.SimpleNamespace()
    flask.has_request_context = lambda: False
    flask.jsonify = lambda value=None, **kwargs: value if value is not None else kwargs
    flask.redirect = lambda location, code=302: (location, code)
    flask.request = DummyRequest()
    sys.modules["flask"] = flask

    werkzeug = types.ModuleType("werkzeug")
    security = types.ModuleType("werkzeug.security")

    def generate_password_hash(password: str) -> str:
        # Suficiente para comprobar que bootstrap no guarda texto plano.
        return "test-pbkdf2$" + hashlib.pbkdf2_hmac("sha256", password.encode(), b"release-validator", 1000).hex()

    security.generate_password_hash = generate_password_hash
    werkzeug.security = security
    sys.modules["werkzeug"] = werkzeug
    sys.modules["werkzeug.security"] = security


def check_config_and_security_bootstrap() -> None:
    failures: list[str] = []
    backend_str = str(BACKEND)
    if backend_str not in sys.path:
        sys.path.insert(0, backend_str)

    try:
        config_module = importlib.import_module("config")
        with tempfile.TemporaryDirectory(prefix="pi-release-config-") as tmp:
            data_dir = Path(tmp)
            valid = {
                "APP_ENV": "production",
                "SECRET_KEY": "S" * 64,
                "JWT_SECRET_KEY": "J" * 64,
                "INITIAL_ADMIN_USERNAME": "operador_prueba_2026",
                "INITIAL_ADMIN_EMAIL": "administrador@example.invalid",
                "INITIAL_ADMIN_PASSWORD": "R3lease!Password#2026",
                "MIN_PASSWORD_LENGTH": 12,
                "DATA_DIR": str(data_dir),
                "DATABASE_PATH": str(data_dir / "database.sqlite3"),
                "DATABASE_URL": "postgresql+psycopg://release:secret@example.invalid:5432/primera_infancia",
                "REQUIRE_POSTGRESQL_IN_PRODUCTION": True,
                "STORAGE_BACKEND": "local",
                "ALLOWED_ORIGINS": "",
                "ALLOW_LEGACY_QUERY_TOKENS": False,
                "ALLOW_PASSWORD_RESET_TOKEN_RESPONSE": False,
                "SINGLE_TENANT_MODE": False,
                "ALLOW_EXPERIMENTAL_MULTI_TENANT": True,
                "MULTI_TENANT_STRICT": True,
                "TENANT_STORAGE_ISOLATION": True,
                "MULTI_TENANT_SCHEMA_VERSION": 3,
            }
            config_module.validate_runtime_config(valid)
            # El modo single continúa siendo un fallback seguro y válido.
            config_module.validate_runtime_config(dict(
                valid,
                SINGLE_TENANT_MODE=True,
                ALLOW_EXPERIMENTAL_MULTI_TENANT=False,
            ))

            bad = dict(valid, SECRET_KEY="short")
            try:
                config_module.validate_runtime_config(bad)
                failures.append("configuración débil no fue rechazada")
            except RuntimeError:
                pass

            invalid_multi_cases = [
                ("confirmación experimental", dict(valid, ALLOW_EXPERIMENTAL_MULTI_TENANT=False)),
                ("guard estricto", dict(valid, MULTI_TENANT_STRICT=False)),
                ("almacenamiento aislado", dict(valid, TENANT_STORAGE_ISOLATION=False)),
                ("esquema tenant v3", dict(valid, MULTI_TENANT_SCHEMA_VERSION=2)),
            ]
            for label, bad_multi in invalid_multi_cases:
                try:
                    config_module.validate_runtime_config(bad_multi)
                    failures.append(f"multi-fundación sin {label} no fue rechazada")
                except RuntimeError:
                    pass

            (data_dir / "database.sqlite3").touch()
            (data_dir / ".primera_infancia_initialized.json").write_text("{}", encoding="utf-8")
            retired = dict(valid, INITIAL_ADMIN_USERNAME="", INITIAL_ADMIN_EMAIL="", INITIAL_ADMIN_PASSWORD="")
            config_module.validate_runtime_config(retired)
    except Exception as exc:  # noqa: BLE001
        failures.append(f"validación de config: {exc}")

    try:
        install_test_stubs()
        # Evita módulos importados de una ejecución previa con dependencias reales/parciales.
        for name in ["modules.seguridad.services", "modules.seguridad.schema", "modules.seguridad"]:
            sys.modules.pop(name, None)
        models = importlib.import_module("models")
        services = importlib.import_module("modules.seguridad.services")
        init_hosting = importlib.import_module("init_hosting")

        with tempfile.TemporaryDirectory(prefix="pi-release-db-") as tmp:
            db_path = Path(tmp) / "database.sqlite3"
            conn = sqlite3.connect(db_path)
            conn.executescript(models.Schema.get_schema_sql())
            conn.close()
            services.ensure_security_schema(str(db_path))

            bootstrap_config = {
                "INITIAL_ADMIN_USERNAME": "supervisor_prueba_2026",
                "INITIAL_ADMIN_EMAIL": "supervisor@example.invalid",
                "INITIAL_ADMIN_PASSWORD": "R3lease!Password#2026",
                "INITIAL_ADMIN_NAME": "Supervisor de prueba",
                "INITIAL_ADMIN_FORCE_PASSWORD_CHANGE": True,
                "INITIAL_FOUNDATION_NAME": "Entorno de pruebas",
                "MIN_PASSWORD_LENGTH": 12,
            }
            first = services.bootstrap_initial_admin(str(db_path), bootstrap_config)
            second = services.bootstrap_initial_admin(str(db_path), bootstrap_config)
            mismatch = services.bootstrap_initial_admin(
                str(db_path),
                dict(bootstrap_config, INITIAL_ADMIN_USERNAME="otro_supervisor", INITIAL_ADMIN_EMAIL="otro@example.invalid"),
            )
            retired = services.bootstrap_initial_admin(
                str(db_path),
                {"INITIAL_ADMIN_USERNAME": "", "INITIAL_ADMIN_EMAIL": "", "INITIAL_ADMIN_PASSWORD": ""},
            )

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            admin_rows = conn.execute("SELECT * FROM usuarios_app WHERE rol='SUPERADMIN'").fetchall()
            beneficiary_count = conn.execute("SELECT COUNT(*) FROM beneficiarios").fetchone()[0]
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            conn.close()

            if not first.get("created"):
                failures.append("bootstrap no creó la cuenta inicial")
            if second.get("created"):
                failures.append("bootstrap no fue idempotente")
            if not mismatch.get("configuration_mismatch"):
                failures.append("cambio de variables creó o modificó silenciosamente una cuenta")
            if not retired.get("initial_credentials_retired"):
                failures.append("retiro de credenciales iniciales no fue aceptado")
            if len(admin_rows) != 1:
                failures.append(f"se esperaban 1 SUPERADMIN y hay {len(admin_rows)}")
            if beneficiary_count != 0:
                failures.append(f"base nueva contiene {beneficiary_count} beneficiarios")
            if integrity != "ok":
                failures.append(f"integridad SQLite: {integrity}")
            if bootstrap_config["INITIAL_ADMIN_PASSWORD"] in str(admin_rows[0]["password_hash"]):
                failures.append("contraseña inicial almacenada en texto plano")
            if services.role_allowed_for_path("/api/usuarios", "DOCENTE"):
                failures.append("DOCENTE obtuvo acceso a /api/usuarios")
            if services.role_allowed_for_path("/api/ruta-no-declarada", "SUPERADMIN"):
                failures.append("ruta no declarada no fue denegada")
            if not services.role_allowed_for_path("/api/talento-core/estado", "GERENTE"):
                failures.append("ruta talento-core no está cubierta para GERENTE")

            current_app = sys.modules["flask"].current_app
            current_app.config = {
                "PASSWORD_RESET_PUBLIC_URL": "https://example.invalid",
                "PUBLIC_APP_URL": "https://example.invalid",
            }
            reset_url = services.build_password_reset_url("token-seguro")
            if "#restablecer?reset_token=" not in reset_url or "/?reset_token=" in reset_url:
                failures.append("token de recuperación no está protegido en fragmento")

            init_hosting.verify_seed_manifest(BACKEND / "seed_data" / "templates_originales")

        # Una identidad existente sin privilegios nunca debe ser promovida.
        with tempfile.TemporaryDirectory(prefix="pi-release-no-promote-") as tmp:
            db_path = Path(tmp) / "database.sqlite3"
            conn = sqlite3.connect(db_path)
            conn.executescript(models.Schema.get_schema_sql())
            conn.close()
            services.ensure_security_schema(str(db_path))
            conn = sqlite3.connect(db_path)
            conn.execute(
                "INSERT INTO usuarios_app (username,email,password_hash,rol,fundacion_id,activo,estado,fecha_creacion) "
                "VALUES (?,?,?,?,1,1,'ACTIVO','2026-08-01T00:00:00')",
                ("usuario_existente", "existente@example.invalid", "hash", "DOCENTE"),
            )
            conn.commit()
            conn.close()
            try:
                services.bootstrap_initial_admin(
                    str(db_path),
                    {
                        "INITIAL_ADMIN_USERNAME": "usuario_existente",
                        "INITIAL_ADMIN_EMAIL": "existente@example.invalid",
                        "INITIAL_ADMIN_PASSWORD": "R3lease!Password#2026",
                        "MIN_PASSWORD_LENGTH": 12,
                    },
                )
                failures.append("una cuenta existente fue promovida o aceptada como SUPERADMIN")
            except RuntimeError:
                pass
    except Exception as exc:  # noqa: BLE001
        failures.append(f"bootstrap/esquema: {type(exc).__name__}: {exc}")

    record("Configuración productiva y bootstrap seguro", not failures, " | ".join(failures) if failures else "config multi-fundación, bootstrap, roles e integridad OK")


def check_security_text_invariants() -> None:
    failures: list[str] = []
    content = {path: path.read_text(encoding="utf-8", errors="ignore") for path in text_files()}
    # El validador contiene deliberadamente las firmas que busca. Excluir únicamente
    # su propio código evita falsos positivos sin omitir ningún artefacto del producto.
    validator_path = Path(__file__).resolve()
    scan_content = {path: text for path, text in content.items() if path.resolve() != validator_path}

    internal_paths = [str(path.relative_to(ROOT)) for path, text in scan_content.items() if "/mnt/data/" in text]
    if internal_paths:
        failures.append("rutas internas: " + ", ".join(internal_paths[:5]))

    real_terms = re.compile(
        r"manos abiertas|cdmac|quibd[oó]|pacurita|bendici[oó]n|necora|kilometro|playa alta|"
        r"pueblo nuevo|eyasake|eyazake|kipara|kiphara|conondo|korede|mungarado|jampapa|"
        r"vive la|vive el amor|vive en hogar",
        re.I,
    )
    allowed_operational_catalog_paths = {
        "backend/config/uds_catalog.json",
        "backend/services/uds_catalog.py",
        "frontend/index.html",
    }
    term_hits = [
        path.relative_to(ROOT).as_posix()
        for path, text in scan_content.items()
        if real_terms.search(text)
        and path.relative_to(ROOT).as_posix() not in allowed_operational_catalog_paths
        and "backend/tests/" not in path.relative_to(ROOT).as_posix()
    ]
    if term_hits:
        failures.append("identificadores operativos fuera del catálogo autorizado: " + ", ".join(term_hits[:5]))

    # La firma de la credencial histórica puede permanecer únicamente en la
    # validación de configuración que la rechaza explícitamente. Nunca en UI,
    # documentación, archivos de entorno ni rutas de autenticación.
    rejected_default = re.compile(r"admin(?:/|:|\s+)(?:admin123|admin)", re.I)
    default_credential_hits = [
        str(path.relative_to(ROOT))
        for path, text in scan_content.items()
        if path != ROOT / "backend" / "config.py" and rejected_default.search(text)
    ]
    if default_credential_hits:
        failures.append("credencial predeterminada expuesta: " + ", ".join(default_credential_hits[:5]))

    frontend_modules = [path for path in (ROOT / "frontend" / "js" / "modules").rglob("*.js")]
    localhost_hits = [str(path.relative_to(ROOT)) for path in frontend_modules if re.search(r"https?://(?:127\.0\.0\.1|localhost):5000", path.read_text(encoding="utf-8", errors="ignore"))]
    if localhost_hits:
        failures.append("fallback localhost en módulos: " + ", ".join(localhost_hits[:8]))

    combined_frontend = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in list((ROOT / "frontend").rglob("*.js")) + list((ROOT / "frontend").rglob("*.html"))
    )
    if re.search(r"[?&](?:token|auth_token|_auth_token)=", combined_frontend, re.I):
        failures.append("token de sesión construido en URL del frontend")
    if re.search(r"(?:unpkg|jsdelivr)[^\"']*@latest", combined_frontend, re.I):
        failures.append("dependencia frontend externa sin versión fija")

    env_text = (ROOT / ".env.example").read_text(encoding="utf-8")
    for required_line in [
        "ALLOW_LEGACY_QUERY_TOKENS=false",
        "ALLOW_PASSWORD_RESET_TOKEN_RESPONSE=false",
        "ALLOW_LOCAL_RECOVERY_CODE=false",
        "LOCAL_RECOVERY_CODE_LENGTH=10",
        "RESET_MAX_ATTEMPTS=8",
        "ENABLE_LEGACY_TENANT_BACKFILL=false",
        "SINGLE_TENANT_MODE=false",
        "FORCE_HTTPS=true",
        "ALLOW_EXPERIMENTAL_MULTI_TENANT=true",
        "MULTI_TENANT_STRICT=true",
        "TENANT_STORAGE_ISOLATION=true",
        "MULTI_TENANT_SCHEMA_VERSION=3",
        "SYNC_MANAGED_TEMPLATES=true",
        "APP_VERSION=2.7.2-document-center",
        "REQUIRE_POSTGRESQL_IN_PRODUCTION=true",
        "INTEGRITY_ENGINE_ENABLED=true",
        "METRICS_ENABLED=true",
        "READINESS_MAX_DB_LATENCY_MS=2000",
        "BIBLIOTECA_REMOTE_CHECKS_ENABLED=false",
        "BIBLIOTECA_ALLOWED_DOMAINS=icbf.gov.co,www.icbf.gov.co",
        "MOTOR_GESTION_ENABLED=true",
        "LOGIN_DB_RETRY_ATTEMPTS=4",
        "LOGIN_DB_BUSY_TIMEOUT_MS=150",
        "LOGIN_DB_RETRY_BASE_MS=50",
        "LOGIN_DB_RETRY_BUDGET_MS=1200",
        "LOGIN_SLOW_THRESHOLD_MS=1500",
        "RAILWAY_PUBLIC_DOMAIN=",
    ]:
        if required_line not in env_text:
            failures.append(f"falta {required_line} en .env.example")

    if re.search(r"INITIAL_ADMIN_PASSWORD=(?!REEMPLAZAR_).+", env_text):
        failures.append(".env.example contiene una contraseña inicial utilizable")

    config_text = (BACKEND / "config.py").read_text(encoding="utf-8")
    services_text = (BACKEND / "modules" / "seguridad" / "services.py").read_text(encoding="utf-8")
    routes_text = (BACKEND / "modules" / "seguridad" / "routes.py").read_text(encoding="utf-8")
    app_text = (BACKEND / "app.py").read_text(encoding="utf-8")
    tunnel_text = (ROOT / "scripts_windows" / "iniciar_tunel_cloudflare.ps1").read_text(encoding="utf-8")
    frontend_app_text = (ROOT / "frontend" / "js" / "app.js").read_text(encoding="utf-8")
    if "return False" not in services_text[services_text.find("def role_allowed_for_path"):services_text.find("def _rate_key")]:
        failures.append("autorización no evidencia denegación por defecto")
    if "development_reset_token" not in routes_text or "app.config.get('APP_ENV') != 'production'" not in routes_text:
        failures.append("respuesta de token de recuperación no está limitada a desarrollo")
    for required in [
        "local_recovery_code", "PASSWORD_RESTABLECIDO", "ADMIN_RESTABLECER_PASSWORD",
        "ELIMINAR_USUARIO_LOGICO", "ELIMINAR_FUNDACION_LOGICA", "LAST_SUPERADMIN_PROTECTED",
    ]:
        if required not in routes_text:
            failures.append(f"seguridad/administración no contiene {required}")
    for required in [
        "/api/health", "RedirectStandardError", "cloudflared_tunnel.pid",
        "public_tunnel_mode", "Stop-VerifiedLocalBackend", "trycloudflare.com",
        "ExpectedInstanceId", "project_instance_id", "Test-ExpectedBackend",
        "cloudflared_home_aislado", "Invoke-CurlDownload", "Tls12",
        "Protocol = 'auto'", "Protocol = 'http2'", "ULTIMO_COMANDO_CLOUDFLARED.txt",
    ]:
        if required not in tunnel_text:
            failures.append(f"script de túnel no contiene {required}")
    argument_start = tunnel_text.find("$cloudflaredArgs = @(")
    argument_end = tunnel_text.find("# El proceso hereda", argument_start)
    argument_block = tunnel_text[argument_start:argument_end] if argument_start >= 0 and argument_end > argument_start else ""
    if "--config" in argument_block or "$QuickConfig" in tunnel_text:
        failures.append("Quick Tunnel continúa usando --config/configuración nombrada")
    local_bat_text = (ROOT / "INICIAR_PLATAFORMA_LOCAL.bat").read_text(encoding="utf-8-sig")
    launcher_text = (ROOT / "scripts_windows" / "iniciar_plataforma.ps1").read_text(encoding="utf-8-sig")
    if "iniciar_plataforma.ps1" not in local_bat_text or "-Mode Local" not in local_bat_text:
        failures.append("el BAT local no delega al lanzador PowerShell robusto")
    if "/api/acceso/ping" in launcher_text:
        failures.append("inicio local continúa usando ping autenticado")
    for forbidden in ["AdminLocal2026*", "local-dev-secret-key", "local-dev-jwt-secret-key"]:
        if forbidden in launcher_text:
            failures.append(f"inicio local conserva secreto/credencial fija: {forbidden}")
    for required in [
        "CREDENCIALES_INICIALES_LOCAL.txt", "secrets.token_urlsafe(64)",
        "INITIAL_ADMIN_FORCE_PASSWORD_CHANGE", "PROJECT_INSTANCE_ID",
        "ExpectedTunnel", "project_instance_id", "data\\logs", "/api/health",
        "postgresql+psycopg://", "DB_POOL_SIZE",
    ]:
        if required not in launcher_text:
            failures.append(f"lanzador local no contiene protección requerida: {required}")
    if "public_tunnel_mode" not in app_text or "server_mode" not in app_text or "project_instance_id" not in app_text:
        failures.append("healthcheck no informa modo local/túnel e instancia")
    for required in ["X-Client-Request-ID", "trace_id", "log_file", "LOGIN_DATABASE_BUSY"]:
        if required not in frontend_app_text:
            failures.append(f"frontend login no contiene {required}")
    diagnostics_text = (BACKEND / "modules" / "seguridad" / "runtime_diagnostics.py").read_text(encoding="utf-8")
    for required in ["RotatingFileHandler", "os.fsync", "logs_fallback", "[REDACTED]"]:
        if required not in diagnostics_text:
            failures.append(f"logging robusto no contiene {required}")
    diagnostic_script = (ROOT / "scripts_windows" / "diagnosticar_login_tunel.ps1").read_text(encoding="utf-8-sig")
    if (
        "DIAGNOSTICO DE TUNEL Y LOGIN" not in diagnostic_script
        or "data\\logs" not in diagnostic_script
        or "logs_tunel" not in diagnostic_script
        or "7844" not in diagnostic_script
        or "HTTP/2/TCP" not in diagnostic_script
    ):
        failures.append("diagnóstico de login/túnel incompleto")
    for required in ["Editar", "Eliminar", "Restablecer clave", "local_recovery_code"]:
        if required not in frontend_app_text:
            failures.append(f"frontend administrativo/recuperación no contiene {required}")
    if "raise RuntimeError('La capa de seguridad no pudo registrarse" not in app_text:
        failures.append("producción no falla cerrada si seguridad no registra")
    if "ALLOW_LEGACY_QUERY_TOKENS debe permanecer desactivado" not in config_text:
        failures.append("configuración productiva no rechaza tokens legacy")
    for required in [
        "ALLOW_EXPERIMENTAL_MULTI_TENANT=true como confirmación explícita",
        "MULTI_TENANT_STRICT debe permanecer activado",
        "TENANT_STORAGE_ISOLATION debe permanecer activado",
        "MULTI_TENANT_SCHEMA_VERSION debe ser 3 o superior",
    ]:
        if required not in config_text:
            failures.append(f"configuración multi-fundación no contiene: {required}")
    guard_text = (BACKEND / "modules" / "seguridad" / "tenant_sql_guard.py").read_text(encoding="utf-8")
    migration_text = (BACKEND / "migrations" / "migrate_multitenant_phase3.py").read_text(encoding="utf-8")
    sqlalchemy_text = (BACKEND / "modules" / "sqlalchemy_compat.py").read_text(encoding="utf-8")
    if "class TenantIsolationError" not in guard_text or "install_sqlite_tenant_guard" not in guard_text:
        failures.append("cortafuegos SQL tenant ausente")
    if "SCHEMA_VERSION = 3" not in migration_text or "UNIQUE(fundacion_id, documento, unidad)" not in migration_text:
        failures.append("migración tenant v3 incompleta")
    if "guarded_sql = _guard_core_sql" not in sqlalchemy_text:
        failures.append("SQLAlchemy Core no evidencia guard tenant")
    if "LAST_SUPERADMIN_PROTECTED" not in routes_text or "sesiones_invalidadas" not in routes_text:
        failures.append("administración de usuarios no protege SUPERADMIN/sesiones")
    for required in [
        "def resolver_url_publica",
        "RAILWAY_PUBLIC_DOMAIN",
        "@app.route('/api/acceso/storage-health'",
        "@app.route('/api/formatos/diagnostico'",
    ]:
        if required not in app_text:
            failures.append(f"app.py no contiene {required}")

    giu_repository = (BACKEND / "modules" / "gestion_integral_uca" / "repository.py").read_text(encoding="utf-8")
    giu_routes = (BACKEND / "modules" / "gestion_integral_uca" / "routes.py").read_text(encoding="utf-8")
    giu_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    giu_js = (ROOT / "frontend" / "js" / "modules" / "gestion-integral-uca.js").read_text(encoding="utf-8")
    for required in [
        "giu_expedientes_uca", "giu_ruta_instancias", "giu_planes_uca",
        "biblioteca_icbf_documentos", "build_supervision_package",
        "Esta actividad exige al menos una evidencia",
        "allowed_keys is not None",
        "archivos_actualizados",
    ]:
        if required not in giu_repository:
            failures.append(f"Gestión Integral UCA no contiene {required}")
    for required in [
        "/api/gestion-integral-uca", "paquete-supervision",
        "/biblioteca/documentos", "tenant_storage_root",
        "_safe_tenant_file", "DESCARGAR_EVIDENCIA_RUTA",
    ]:
        if required not in giu_routes and required not in (BACKEND / "modules" / "seguridad" / "services.py").read_text(encoding="utf-8"):
            failures.append(f"rutas Gestión Integral UCA no contienen {required}")
    for required in ["expediente-operativo-uca", "biblioteca-icbf", "gestion-integral-uca.js"]:
        if required not in giu_html:
            failures.append(f"interfaz Gestión Integral UCA no contiene {required}")
    for required in ["giuInit", "bibliotecaIcbfInit", "Paquete supervisión", "Ocho planes"]:
        if required not in giu_js:
            failures.append(f"frontend Gestión Integral UCA no contiene {required}")

    giu_integrations = (BACKEND / "modules" / "gestion_integral_uca" / "integrations.py").read_text(encoding="utf-8")
    giu_schema = (BACKEND / "modules" / "gestion_integral_uca" / "schema.py").read_text(encoding="utf-8")
    giu_test = (BACKEND / "tests" / "test_expediente_uca_central_v2_5_2.py").read_text(encoding="utf-8")
    for required in [
        "class UCAIntegrationEngine", "def build_view", "def documents", "def alerts",
        "def schedule", "Lectura integrada y referencias; no se duplican registros operativos",
    ]:
        if required not in giu_integrations:
            failures.append(f"Expediente UCA central 2.5.2 no contiene {required}")
    for required in ["SCHEMA_VERSION = 3", "giu_vinculos_documentales", "giu_paquetes_supervision", "biblioteca_icbf_fuentes", "biblioteca_icbf_candidatos", "biblioteca_icbf_notificaciones", "biblioteca_icbf_historial"]:
        if required not in giu_schema:
            failures.append(f"esquema GIU 2.5.3 no contiene {required}")
    for required in ["vista-unica", "preparacion-supervision", "documentos/<int:link_id>/descargar"]:
        if required not in giu_routes:
            failures.append(f"rutas Expediente UCA central no contienen {required}")
    for required in ["Centro operativo", "Componentes", "Documentos", "Alertas", "Cronograma", "Indicadores"]:
        if required not in giu_js:
            failures.append(f"interfaz Expediente UCA central no contiene {required}")
    if "test_expediente_uca_central_v2_5_2" not in giu_test and "componentes_integrados" not in giu_test:
        failures.append("suite 2.5.2 no cubre la vista única por UCA")

    library_update_text = (BACKEND / "modules" / "gestion_integral_uca" / "library_updates.py").read_text(encoding="utf-8")
    motor_schema_text = (BACKEND / "modules" / "motor_gestion_proyecto" / "schema.py").read_text(encoding="utf-8")
    motor_repo_text = (BACKEND / "modules" / "motor_gestion_proyecto" / "repository.py").read_text(encoding="utf-8")
    motor_routes_text = (BACKEND / "modules" / "motor_gestion_proyecto" / "routes.py").read_text(encoding="utf-8")
    motor_js_text = (ROOT / "frontend" / "js" / "modules" / "motor-gestion-proyecto.js").read_text(encoding="utf-8")
    v253_test = (BACKEND / "tests" / "test_biblioteca_motor_gestion_v2_5_3.py").read_text(encoding="utf-8")
    for required in ["biblioteca_icbf_fuentes", "biblioteca_icbf_candidatos", "biblioteca_icbf_notificaciones", "biblioteca_icbf_historial"]:
        if required not in giu_schema:
            failures.append(f"Biblioteca 2.5.3 no contiene {required}")
    for required in ["BIBLIOTECA_REMOTE_CHECKS_ENABLED", "CATALOGO_JSON", "allow_redirects=False", "_reject_private_resolution"]:
        if required not in library_update_text:
            failures.append(f"verificación controlada Biblioteca no contiene {required}")
    for required in ["mgp_tareas", "mgp_dependencias", "mgp_recordatorios", "mgp_productos", "mgp_cierres_mensuales", "mgp_auditoria"]:
        if required not in motor_schema_text:
            failures.append(f"Motor de Gestión 2.5.3 no contiene {required}")
    for required in ["def synchronize", "prepare_monthly_products", "BORRADOR", "recalculate_priorities", "generate_reminders"]:
        if required not in motor_repo_text:
            failures.append(f"repositorio Motor de Gestión no contiene {required}")
    for required in ["/api/motor-gestion-proyecto", "/productos/preparar", "/cierres", "/recordatorios"]:
        if required not in motor_routes_text and required not in services_text:
            failures.append(f"rutas Motor de Gestión no contienen {required}")
    for required in ["Motor Inteligente de Gestión del Proyecto", "prepareProducts", "prepareClosure", "motorGestionProyectoInit"]:
        if required not in motor_js_text and required not in giu_html:
            failures.append(f"frontend Motor de Gestión no contiene {required}")
    for required in ["fuentes remotas cerradas", "productos borrador", "aislamiento multi-fundación"]:
        if required not in v253_test:
            failures.append(f"suite 2.5.3 no cubre {required}")

    csc_schema_text = (BACKEND / "modules" / "supervision_calidad" / "schema.py").read_text(encoding="utf-8")
    csc_repo_text = (BACKEND / "modules" / "supervision_calidad" / "repository.py").read_text(encoding="utf-8")
    csc_routes_text = (BACKEND / "modules" / "supervision_calidad" / "routes.py").read_text(encoding="utf-8")
    fcr_schema_text = (BACKEND / "modules" / "familias_redes" / "schema.py").read_text(encoding="utf-8")
    fcr_repo_text = (BACKEND / "modules" / "familias_redes" / "repository.py").read_text(encoding="utf-8")
    fcr_routes_text = (BACKEND / "modules" / "familias_redes" / "routes.py").read_text(encoding="utf-8")
    csc_js_text = (ROOT / "frontend" / "js" / "modules" / "supervision-calidad.js").read_text(encoding="utf-8")
    fcr_js_text = (ROOT / "frontend" / "js" / "modules" / "familias-redes.js").read_text(encoding="utf-8")
    v254_test = (BACKEND / "tests" / "test_supervision_familias_redes_v2_5_4.py").read_text(encoding="utf-8")
    for required in [
        "csc_checklist_catalogo", "csc_supervisiones", "csc_verificaciones",
        "csc_hallazgos", "csc_planes_mejora", "csc_acciones_mejora",
        "csc_seguimientos", "csc_evidencias", "csc_productos", "csc_auditoria",
    ]:
        if required not in csc_schema_text:
            failures.append(f"esquema Supervisión/Calidad 2.5.4 no contiene {required}")
    for required in [
        "build_products", "Carga la evidencia requerida antes de validar la acción.",
        "Todos los planes asociados deben estar cerrados y validados.",
        "tenant_storage_root", "BORRADOR",
    ]:
        if required not in csc_repo_text:
            failures.append(f"repositorio Supervisión/Calidad 2.5.4 no contiene {required}")
    for required in ["/api/supervision-calidad", "/supervisiones", "/hallazgos", "/planes", "/productos"]:
        if required not in csc_routes_text and required not in services_text:
            failures.append(f"rutas Supervisión/Calidad no contienen {required}")
    for required in [
        "fcr_expedientes_familiares", "fcr_actividades", "fcr_asistencias",
        "fcr_compromisos", "fcr_seguimientos", "fcr_redes_apoyo",
        "fcr_alertas", "fcr_evidencias", "fcr_documentos_generados", "fcr_auditoria",
    ]:
        if required not in fcr_schema_text:
            failures.append(f"esquema Familias/Redes 2.5.4 no contiene {required}")
    for required in [
        "sync_family_records", "prepare_activity_documents", "_write_activity_pdf",
        "_write_attendance", "prepare_summary_package", "tenant_storage_root",
    ]:
        if required not in fcr_repo_text:
            failures.append(f"repositorio Familias/Redes 2.5.4 no contiene {required}")
    for required in [
        "/api/familias-redes", "/expedientes/sincronizar",
        "/actividades", "/compromisos", "/alertas", "/reportes/preparar",
    ]:
        if required not in fcr_routes_text and required not in services_text:
            failures.append(f"rutas Familias/Redes no contienen {required}")
    for required in ["Centro Inteligente de Supervisión", "createPlan", "prepareProducts"]:
        if required not in csc_js_text and required not in giu_html:
            failures.append(f"frontend Supervisión/Calidad no contiene {required}")
    for required in ["Gestión Integral de Familias", "prepareDocs", "prepareReport"]:
        if required not in fcr_js_text and required not in giu_html:
            failures.append(f"frontend Familias/Redes no contiene {required}")
    for required in [
        "expedientes familiares idempotentes", "acta y listado automáticos",
        "compromisos y alertas con cierre humano", "Motor idempotente",
        "aislamiento multi-fundación",
    ]:
        if required not in v254_test:
            failures.append(f"suite 2.5.4 no cubre {required}")

    cpo_schema_text = (BACKEND / "modules" / "centro_planeacion" / "schema.py").read_text(encoding="utf-8")
    cpo_repo_text = (BACKEND / "modules" / "centro_planeacion" / "repository.py").read_text(encoding="utf-8")
    cpo_routes_text = (BACKEND / "modules" / "centro_planeacion" / "routes.py").read_text(encoding="utf-8")
    ps_schema_text = (BACKEND / "modules" / "componente_psicosocial" / "schema.py").read_text(encoding="utf-8")
    ps_repo_text = (BACKEND / "modules" / "componente_psicosocial" / "repository.py").read_text(encoding="utf-8")
    ps_routes_text = (BACKEND / "modules" / "componente_psicosocial" / "routes.py").read_text(encoding="utf-8")
    cpo_js_text = (ROOT / "frontend" / "js" / "modules" / "centro-planeacion.js").read_text(encoding="utf-8")
    ps_js_text = (ROOT / "frontend" / "js" / "modules" / "componente-psicosocial.js").read_text(encoding="utf-8")
    v270_test = (BACKEND / "tests" / "test_centro_planeacion_psicosocial_v2_7_0.py").read_text(encoding="utf-8")
    for required in [
        "cpo_reglas_operativas", "cpo_actividad_metadata", "cpo_dependencias",
        "cpo_documentos_preparados", "cpo_notificaciones", "cpo_auditoria",
    ]:
        if required not in cpo_schema_text:
            failures.append(f"esquema Centro Planeación 2.7.0 no contiene {required}")
    for required in [
        "synchronize", "prepare_documents", "export_monthly_package",
        "fuente_tabla", "fuente_clave", "ON CONFLICT", "BORRADOR",
    ]:
        if required not in cpo_repo_text:
            failures.append(f"repositorio Centro Planeación 2.7.0 no contiene {required}")
    for required in [
        "ps_expedientes", "ps_caracterizaciones", "ps_planes_acompanamiento",
        "ps_acciones_plan", "ps_vinculos_actividad", "ps_seguimientos",
        "ps_documentos", "ps_auditoria_accesos",
    ]:
        if required not in ps_schema_text:
            failures.append(f"esquema Psicosocial 2.7.0 no contiene {required}")
    for required in [
        "sync_expedientes", "create_characterization", "review_characterization",
        "create_plan", "create_action", "close_plan", "prepare_report",
        "RESTRINGIDO", "La acción requiere evidencia.",
    ]:
        if required not in ps_repo_text:
            failures.append(f"repositorio Psicosocial 2.7.0 no contiene {required}")
    for required in ["/api/centro-planeacion", "/dashboard", "/sincronizar", "/paquetes/mensual"]:
        if required not in cpo_routes_text and required not in services_text:
            failures.append(f"rutas Centro Planeación no contienen {required}")
    for required in ["/api/psicosocial", "/expedientes", "/caracterizaciones", "/planes", "/seguimientos"]:
        if required not in ps_routes_text and required not in services_text:
            failures.append(f"rutas Psicosocial no contienen {required}")
    for required in ["Centro Inteligente de Planeación", "sincronizar", "paquete"]:
        if required.lower() not in cpo_js_text.lower() and required not in giu_html:
            failures.append(f"frontend Centro Planeación no contiene {required}")
    for required in ["Componente Psicosocial", "caracterización", "plan", "informe"]:
        if required.lower() not in ps_js_text.lower() and required not in giu_html:
            failures.append(f"frontend Psicosocial no contiene {required}")
    for required in [
        "Sincronización del centro no idempotente", "El Motor de Gestión duplicó actividades",
        "Escalamiento de vista por parámetro", "Aislamiento psicosocial",
        "evidencia", "dependencia", "paquete mensual",
    ]:
        if required.lower() not in v270_test.lower():
            failures.append(f"suite 2.7.0 no cubre {required}")
    if "('/api/centro-planeacion', ALL_ROLES)" not in services_text or "('/api/psicosocial', FAMILY_SOCIAL)" not in services_text:
        failures.append("matriz de roles no cubre Centro Planeación y Psicosocial")

    auth_test = (BACKEND / "tests" / "test_auth_concurrency_v2_5_1.py").read_text(encoding="utf-8")
    auth_services = (BACKEND / "modules" / "seguridad" / "services.py").read_text(encoding="utf-8")
    auth_routes = (BACKEND / "modules" / "seguridad" / "routes.py").read_text(encoding="utf-8")
    billing_services = (BACKEND / "modules" / "facturacion_suscripcion" / "services.py").read_text(encoding="utf-8")
    for required in [
        "create_login_session_atomic", "record_login_failure_atomic", "load_login_state",
        "BEGIN IMMEDIATE", "LOGIN_DB_RETRY_BUDGET_MS",
    ]:
        if required not in auth_services and required not in auth_routes:
            failures.append(f"autenticación 2.5.1 no contiene {required}")
    for required in [
        "let loginEnCurso = false", "new AbortController()", "LOGIN_DATABASE_BUSY",
        "Reintentando automáticamente",
    ]:
        if required not in frontend_app_text:
            failures.append(f"frontend login 2.5.1 no contiene {required}")
    if "trusted_internal=True" not in auth_routes or "g.current_user = user_payload" in auth_routes:
        failures.append("login no mantiene aislado el contexto previo a autenticación")
    if "get_subscription_snapshot" not in billing_services or "_INITIALIZED_DATABASES" not in billing_services:
        failures.append("facturación no evidencia snapshot de lectura e inicialización única")
    if "test_parallel_sessions" not in auth_test or "false_rate_limit_rows" not in auth_test:
        failures.append("suite 2.5.1 no cubre sesiones concurrentes y falsos bloqueos")

    integrity_routes = (BACKEND / "modules" / "integrity_stability" / "routes.py").read_text(encoding="utf-8")
    integrity_service = (BACKEND / "modules" / "integrity_stability" / "service.py").read_text(encoding="utf-8")
    observability_text = (BACKEND / "services" / "observability.py").read_text(encoding="utf-8")
    workflow_text = (ROOT / ".github" / "workflows" / "integrity-ci.yml").read_text(encoding="utf-8")
    migration_text_v261 = (BACKEND / "tools" / "migrate_sqlite_to_postgresql.py").read_text(encoding="utf-8")
    cutover_text = (BACKEND / "tools" / "postgresql_cutover.py").read_text(encoding="utf-8")
    runtime_audit_text = (BACKEND / "tools" / "postgresql_runtime_audit.py").read_text(encoding="utf-8")
    safe_repair_text = (BACKEND / "tools" / "safe_repair.py").read_text(encoding="utf-8")
    for required in ["/api/ready", 'url_prefix="/api/integrity"', '@bp.get("/status")', '@bp.post("/run")', '@bp.get("/metrics")']:
        if required not in integrity_routes:
            failures.append(f"Motor de Integridad no contiene {required}")
    for required in ["X-Metrics-Token", "METRICS_TOKEN", "integrity_gate", "safe_repair"]:
        if required not in integrity_routes + integrity_service:
            failures.append(f"Motor de Integridad no contiene {required}")
    if "metrics_token" in integrity_routes.lower() and "request.args" in integrity_routes:
        failures.append("el token de métricas no debe aceptarse por query string")
    for required in ["X-Request-ID", "Server-Timing", "http_request", "def prometheus"]:
        if required not in observability_text:
            failures.append(f"observabilidad no contiene {required}")
    for required in ["postgres:16-alpine", "Integrity Gate + PostgreSQL Migration", "Deployment Gate", "upload-artifact@v4"]:
        if required not in workflow_text:
            failures.append(f"CI de integridad no contiene {required}")
    for required in ["sqlite_consistent_backup", "table_fingerprint", "reset_sequences", "cleanup-on-error"]:
        if required not in migration_text_v261:
            failures.append(f"migración PostgreSQL no contiene {required}")
    for required in ["postgresql_preflight", "postgresql_runtime_audit", "verify_after_migration", "activation_completed"]:
        if required not in cutover_text:
            failures.append(f"corte PostgreSQL no contiene {required}")
    if "unsupported_constructs" not in runtime_audit_text or "direct_sqlite_imports" not in runtime_audit_text:
        failures.append("auditoría SQL runtime incompleta")
    for forbidden in ["change_business_rules", "auto_apply_database_migrations_in_production"]:
        if forbidden not in safe_repair_text and forbidden not in (ROOT / "integrity" / "safe_autofix_policy.json").read_text(encoding="utf-8"):
            failures.append(f"política de autocorrección no protege {forbidden}")

    source_hash = (ROOT / "SOURCE_ARCHIVE_SHA256.txt").read_text(encoding="utf-8").strip()
    expected_source = "37dde6dd72b64fc4a98dc6ca70ac68efba2c111b3fc225f7445baacf5e521f4d  PrimeraInfancia_v2_6_1_POSTGRES_INTEGRIDAD_ESTABILIDAD.zip"
    if not re.fullmatch(r"[0-9a-f]{64}  [^/\\]+\.zip", source_hash):
        failures.append("SOURCE_ARCHIVE_SHA256.txt tiene formato o ruta insegura")
    elif source_hash != expected_source:
        failures.append("SOURCE_ARCHIVE_SHA256.txt no corresponde a la base estable 2.6.1 declarada")

    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    start_script = (ROOT / "start_hosting.sh").read_text(encoding="utf-8")
    if "COPY --chown=appuser:appuser" not in dockerfile or "gosu appuser" not in start_script:
        failures.append("el proceso de aplicación no abandona privilegios root")
    if 'GUNICORN_WORKERS' not in start_script or '--workers "${GUNICORN_WORKERS:-1}"' not in start_script:
        failures.append("Gunicorn no conserva un worker seguro por defecto y parametrización PostgreSQL")

    record("Invariantes de privacidad y seguridad", not failures, " | ".join(failures) if failures else "sin datos runtime, secretos, tokens en URL ni fallbacks públicos a localhost")


def check_multitenant_isolation() -> None:
    failures: list[str] = []
    tests = [
        BACKEND / "tests" / "test_multitenant_phase3.py",
        BACKEND / "tests" / "test_multitenant_release_v2_4_0.py",
        BACKEND / "tests" / "test_tunnel_admin_recovery_v2_4_1.py",
        BACKEND / "tests" / "test_tunnel_login_logging_v2_4_2.py",
        BACKEND / "tests" / "test_tunnel_cloudflare_v2_4_3.py",
        BACKEND / "tests" / "test_gestion_integral_uca_v2_5_0.py",
        BACKEND / "tests" / "test_auth_concurrency_v2_5_1.py",
        BACKEND / "tests" / "test_expediente_uca_central_v2_5_2.py",
        BACKEND / "tests" / "test_biblioteca_motor_gestion_v2_5_3.py",
        BACKEND / "tests" / "test_supervision_familias_redes_v2_5_4.py",
        BACKEND / "tests" / "test_postgresql_compat_v2_6_0.py",
        BACKEND / "tests" / "test_windows_launchers_v2_6_0.py",
        BACKEND / "tests" / "test_salud_nutricion_integral_v2_6_0.py",
        BACKEND / "tests" / "test_migration_tool_v2_6_0.py",
        BACKEND / "tests" / "test_integrity_postgresql_v2_6_1.py",
        BACKEND / "tests" / "test_centro_planeacion_psicosocial_v2_7_0.py",
    ]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(BACKEND)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for test in tests:
        result = subprocess.run(
            [sys.executable, str(test)],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            detail = (result.stderr or result.stdout).strip().replace("\n", " | ")
            failures.append(f"{test.name}: {detail[:700]}")
    record(
        "Aislamiento multi-fundación fail-closed",
        not failures,
        "migración, SQLite, Core, JOIN, storage, administración, recuperación, Quick Tunnel, autenticación, Expediente UCA central, Biblioteca y Motor 2.5.3, Supervisión/Familias 2.5.4, Salud Integral/PostgreSQL/scripts 2.6.0, Integridad/PostgreSQL 2.6.1 y Planeación/Psicosocial 2.7.0 OK" if not failures else " | ".join(failures),
    )


def check_railway_config() -> None:
    failures: list[str] = []
    try:
        cfg = json.loads((ROOT / "railway.json").read_text(encoding="utf-8"))
        deploy = cfg.get("deploy") or {}
        if deploy.get("startCommand") != "./start_hosting.sh":
            failures.append("startCommand")
        if deploy.get("healthcheckPath") != "/api/health":
            failures.append("healthcheckPath")
        if deploy.get("restartPolicyType") != "ON_FAILURE":
            failures.append("restartPolicyType")
    except Exception as exc:  # noqa: BLE001
        failures.append(str(exc))
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8", errors="ignore")
    for required in ["python:3.12-slim", "requirements-production.txt", "tesseract-ocr-spa", "poppler-utils"]:
        if required not in dockerfile:
            failures.append(f"Dockerfile sin {required}")
    if "AS postgres_client" not in dockerfile or "COPY --from=postgres_client" not in dockerfile:
        failures.append("Dockerfile sin cliente PostgreSQL multi-stage")
    record("Configuración Railway/Docker", not failures, ", ".join(failures) if failures else "Dockerfile, PostgreSQL Client, healthcheck, reinicio y OCR presentes")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", dest="json_path", help="Guardar resultados JSON en esta ruta")
    args = parser.parse_args()

    print(f"Validando: {ROOT}")
    check_layout()
    check_syntax()
    check_manifests_and_office_files()
    check_operational_assets()
    check_route_authorization()
    check_config_and_security_bootstrap()
    check_security_text_invariants()
    check_multitenant_isolation()
    check_railway_config()

    failures = [item for item in RESULTS if item["status"] == "FAIL"]
    skipped = [item for item in RESULTS if item["status"] == "SKIP"]
    summary = {
        "root": ROOT.name,
        "version": "2.7.1-universal-data-mapper",
        "generated_at": "2026-08-06",
        "checks": len(RESULTS),
        "passed": sum(item["status"] == "PASS" for item in RESULTS),
        "failed": len(failures),
        "skipped": len(skipped),
        "results": RESULTS,
    }
    if args.json_path:
        output = Path(args.json_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nResultado: {summary['passed']} PASS, {summary['failed']} FAIL, {summary['skipped']} SKIP")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
