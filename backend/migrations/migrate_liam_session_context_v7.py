"""Migración aditiva e idempotente para contexto efímero de LIAM."""
from __future__ import annotations
from datetime import datetime, timezone
from database import get_db_connection

CONTEXT_SCHEMA_VERSION=1


def migrate(_database_path: str|None=None) -> dict:
    with get_db_connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS lia_session_context (
          id INTEGER PRIMARY KEY AUTOINCREMENT,fundacion_id INTEGER NOT NULL,usuario_id INTEGER NOT NULL,
          context_json TEXT NOT NULL DEFAULT '{}',active_task TEXT,updated_at TEXT NOT NULL,expires_at TEXT NOT NULL,
          UNIQUE(fundacion_id,usuario_id))''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_lia_context_tenant_user_expiry ON lia_session_context(fundacion_id,usuario_id,expires_at)')
        conn.execute('CREATE TABLE IF NOT EXISTS lia_schema_version(componente TEXT PRIMARY KEY,version INTEGER NOT NULL,updated_at TEXT NOT NULL)')
        now=datetime.now(timezone.utc).isoformat(timespec='seconds')
        conn.execute("""INSERT INTO lia_schema_version(componente,version,updated_at) VALUES('session_context',?,?) ON CONFLICT(componente) DO UPDATE SET version=excluded.version,updated_at=excluded.updated_at""",(CONTEXT_SCHEMA_VERSION,now));conn.commit()
    return {'status':'PASS','component':'session_context','version':CONTEXT_SCHEMA_VERSION}
