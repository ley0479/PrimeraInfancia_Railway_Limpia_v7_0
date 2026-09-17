#!/usr/bin/env python3
"""Comprueba respaldo reciente sin revelar conexión, ruta ni nombre de archivo."""
from __future__ import annotations

from datetime import datetime, timezone
import os

from sqlalchemy import create_engine, text


def main() -> None:
    url=(os.environ.get("DATABASE_PUBLIC_URL") or os.environ.get("POSTGRES_PUBLIC_URL") or
         os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_PRIVATE_URL"))
    if not url or not str(url).startswith(("postgresql://","postgres://","postgresql+psycopg://")):
        raise SystemExit("BACKUP_CHECK_FAIL: PostgreSQL no configurado")
    normalized=str(url).replace("postgres://","postgresql+psycopg://",1).replace("postgresql://","postgresql+psycopg://",1)
    engine=create_engine(normalized,pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            row=connection.execute(text("""SELECT id,motivo,estado,integridad,tamano_bytes,sha256,fecha_creacion,fecha_validacion
              FROM backups_sistema WHERE estado='VALIDO' AND integridad='OK' ORDER BY id DESC LIMIT 1""")).mappings().first()
    finally:
        engine.dispose()
    if not row:
        raise SystemExit("BACKUP_CHECK_FAIL: no existe respaldo válido")
    created=datetime.fromisoformat(str(row["fecha_creacion"]).replace("Z","+00:00"))
    if created.tzinfo is None: created=created.replace(tzinfo=timezone.utc)
    age_hours=(datetime.now(timezone.utc)-created.astimezone(timezone.utc)).total_seconds()/3600
    if age_hours > 48:
        raise SystemExit(f"BACKUP_CHECK_FAIL: respaldo válido con antigüedad de {age_hours:.1f} horas")
    digest=str(row.get("sha256") or "")
    print({"status":"BACKUP_CHECK_PASS","id":int(row["id"]),"motivo":row["motivo"],"tamano_bytes":int(row.get("tamano_bytes") or 0),"sha256_prefix":digest[:12],"edad_horas":round(age_hours,1),"validado":bool(row.get("fecha_validacion"))})


if __name__=="__main__": main()
