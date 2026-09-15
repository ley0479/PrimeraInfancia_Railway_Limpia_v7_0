"""Migración aditiva para artefactos verificables ADMIN/DEV."""
from datetime import datetime,timezone
from database import get_db_connection
VERSION=1
DDL="""CREATE TABLE IF NOT EXISTS lia_dev_change_artifacts (id INTEGER PRIMARY KEY AUTOINCREMENT,artifact_id TEXT NOT NULL UNIQUE,request_id TEXT NOT NULL,fundacion_id INTEGER NOT NULL,usuario_id INTEGER NOT NULL,artifact_type TEXT NOT NULL,content_json TEXT NOT NULL,content_sha256 TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,UNIQUE(fundacion_id,usuario_id,request_id,artifact_type))"""
def migrate(_database_path=None):
    with get_db_connection() as conn:
        conn.execute(DDL);conn.execute('CREATE INDEX IF NOT EXISTS idx_lia_dev_artifact_scope ON lia_dev_change_artifacts(fundacion_id,usuario_id,request_id,created_at)');conn.execute('CREATE TABLE IF NOT EXISTS lia_schema_version(componente TEXT PRIMARY KEY,version INTEGER NOT NULL,updated_at TEXT NOT NULL)')
        now=datetime.now(timezone.utc).isoformat(timespec='seconds');conn.execute("""INSERT INTO lia_schema_version(componente,version,updated_at) VALUES('dev_change_artifacts',?,?) ON CONFLICT(componente) DO UPDATE SET version=excluded.version,updated_at=excluded.updated_at""",(VERSION,now));conn.commit()
    return {'status':'PASS','component':'dev_change_artifacts','version':VERSION}
