"""Migración aditiva para solicitudes ADMIN/DEV controladas de LIAM."""
from __future__ import annotations
from datetime import datetime,timezone
from database import get_db_connection

VERSION=1

def migrate(_database_path:str|None=None)->dict:
    with get_db_connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS lia_dev_change_requests (
          id INTEGER PRIMARY KEY AUTOINCREMENT,request_id TEXT NOT NULL UNIQUE,fundacion_id INTEGER NOT NULL,
          usuario_id INTEGER NOT NULL,module TEXT NOT NULL,objective TEXT NOT NULL,impact_summary TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'DRAFT',created_at TEXT NOT NULL,updated_at TEXT NOT NULL)''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_lia_dev_change_scope ON lia_dev_change_requests(fundacion_id,usuario_id,status,created_at)')
        conn.execute('CREATE TABLE IF NOT EXISTS lia_schema_version(componente TEXT PRIMARY KEY,version INTEGER NOT NULL,updated_at TEXT NOT NULL)')
        now=datetime.now(timezone.utc).isoformat(timespec='seconds');conn.execute("""INSERT INTO lia_schema_version(componente,version,updated_at) VALUES('dev_change_requests',?,?) ON CONFLICT(componente) DO UPDATE SET version=excluded.version,updated_at=excluded.updated_at""",(VERSION,now));conn.commit()
    return {'status':'PASS','component':'dev_change_requests','version':VERSION}
