"""Migración aditiva para trazabilidad estructurada de acciones LIAM."""
from __future__ import annotations
from datetime import datetime,timezone
from database import get_db_connection

VERSION=1
DDL='''CREATE TABLE IF NOT EXISTS liam_action_audit (id INTEGER PRIMARY KEY AUTOINCREMENT,action_key TEXT NOT NULL UNIQUE,fundacion_id INTEGER NOT NULL,usuario_id INTEGER NOT NULL,session_id TEXT,trace_id TEXT,intent TEXT NOT NULL,requested_action TEXT NOT NULL,approved_action TEXT,risk_level TEXT,resource TEXT,resource_id TEXT,before_state TEXT NOT NULL DEFAULT '{}',after_state TEXT NOT NULL DEFAULT '{}',result TEXT NOT NULL,error TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL)'''

def migrate(_database_path=None):
    with get_db_connection() as conn:
        conn.execute(DDL);conn.execute('CREATE INDEX IF NOT EXISTS idx_liam_action_audit_scope ON liam_action_audit(fundacion_id,usuario_id,created_at)')
        conn.execute('CREATE TABLE IF NOT EXISTS lia_schema_version(componente TEXT PRIMARY KEY,version INTEGER NOT NULL,updated_at TEXT NOT NULL)')
        now=datetime.now(timezone.utc).isoformat(timespec='seconds');conn.execute("""INSERT INTO lia_schema_version(componente,version,updated_at) VALUES('action_audit',?,?) ON CONFLICT(componente) DO UPDATE SET version=excluded.version,updated_at=excluded.updated_at""",(VERSION,now));conn.commit()
    return {'status':'PASS','component':'action_audit','version':VERSION}
