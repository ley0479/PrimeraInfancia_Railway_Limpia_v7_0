"""Migración aditiva e idempotente para comandos favoritos de LIAM."""
from __future__ import annotations
from datetime import datetime, timezone
from database import get_db_connection

FAVORITES_SCHEMA_VERSION = 1


def migrate(_database_path: str | None = None) -> dict:
    with get_db_connection() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS lia_command_favorites (
          id INTEGER PRIMARY KEY AUTOINCREMENT,fundacion_id INTEGER NOT NULL,
          usuario_id INTEGER NOT NULL,nombre TEXT NOT NULL,comando TEXT NOT NULL,
          created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
          UNIQUE(fundacion_id,usuario_id,nombre))''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_lia_favorites_tenant_user ON lia_command_favorites(fundacion_id,usuario_id,updated_at)')
        conn.execute('CREATE TABLE IF NOT EXISTS lia_schema_version(componente TEXT PRIMARY KEY,version INTEGER NOT NULL,updated_at TEXT NOT NULL)')
        now=datetime.now(timezone.utc).isoformat(timespec='seconds')
        conn.execute("""INSERT INTO lia_schema_version(componente,version,updated_at) VALUES('command_favorites',?,?) ON CONFLICT(componente) DO UPDATE SET version=excluded.version,updated_at=excluded.updated_at""",(FAVORITES_SCHEMA_VERSION,now))
        conn.commit()
    return {'status':'PASS','component':'command_favorites','version':FAVORITES_SCHEMA_VERSION}


if __name__=='__main__':
    from config import get_config
    print(migrate(str(get_config().DATABASE_PATH)))
