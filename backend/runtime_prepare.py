#!/usr/bin/env python3
"""Prepara únicamente archivos del volumen antes de iniciar Gunicorn.

Este proceso no conecta a la base ni ejecuta DDL. Las migraciones pertenecen
exclusivamente al Pre-deploy Command de Railway.
"""
from __future__ import annotations

import os
from pathlib import Path

from config import get_config
from init_hosting import verify_seed_manifest
from services.seed_sync import sync_managed_seed_tree


def main() -> int:
    config = get_config(os.getenv("APP_ENV", "production"))
    data_dir = Path(config.DATA_DIR)
    directories = (
        data_dir,
        Path(config.UPLOAD_FOLDER),
        Path(config.TEMPLATES_FOLDER),
        Path(config.OUTPUT_FOLDER),
        Path(config.BACKUPS_FOLDER),
        Path(config.DOCUMENTOS_FOLDER),
        Path(config.CUENTAS_COBRO_FOLDER),
        Path(config.LOCAL_STORAGE_PATH),
        Path(config.LOG_FOLDER),
        data_dir / "tenants",
        data_dir / "integrity",
        data_dir / "migration_reports",
    )
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    seed_dir = Path(config.SEED_TEMPLATES_FOLDER)
    verify_seed_manifest(seed_dir)
    report = sync_managed_seed_tree(
        seed_dir,
        Path(config.TEMPLATES_FOLDER),
        data_dir=data_dir,
        backups_dir=Path(config.BACKUPS_FOLDER),
        allow_updates=str(os.getenv("SYNC_MANAGED_TEMPLATES", "1")).lower()
        not in {"0", "false", "no", "off"},
    )
    print(
        "[RUNTIME] Volumen preparado: "
        f"nuevas={len(report.get('copied') or [])}, "
        f"actualizadas={len(report.get('updated') or [])}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
