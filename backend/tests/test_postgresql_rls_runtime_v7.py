"""Prueba RLS PostgreSQL transaccional; no persiste tablas ni datos."""
from __future__ import annotations

import os
import uuid


def main() -> None:
    url = str(os.getenv("DATABASE_URL") or "").strip()
    if not url.startswith(("postgres://", "postgresql://")):
        print("POSTGRESQL_RLS_RUNTIME_V7_SKIP")
        return
    import psycopg

    table = f"rls_probe_{uuid.uuid4().hex[:12]}"
    policy = f"{table}_tenant_policy"
    with psycopg.connect(url) as connection:
        with connection.transaction(force_rollback=True):
            with connection.cursor() as cursor:
                cursor.execute(f"CREATE TABLE {table}(id BIGSERIAL PRIMARY KEY,fundacion_id INTEGER NOT NULL,valor TEXT)")
                cursor.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
                cursor.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
                predicate = "(fundacion_id = NULLIF(current_setting('app.current_fundacion_id', true), '')::integer OR current_setting('app.allow_global', true) = 'true')"
                cursor.execute(f"CREATE POLICY {policy} ON {table} FOR ALL USING {predicate} WITH CHECK {predicate}")
                cursor.execute("SELECT set_config('app.current_fundacion_id','101',true),set_config('app.allow_global','false',true)")
                cursor.execute(f"INSERT INTO {table}(fundacion_id,valor) VALUES(101,'visible')")
                cursor.execute("SELECT set_config('app.current_fundacion_id','202',true)")
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                assert cursor.fetchone()[0] == 0
                cursor.execute("SELECT set_config('app.allow_global','true',true)")
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                assert cursor.fetchone()[0] == 1
    print("POSTGRESQL_RLS_RUNTIME_V7_PASS")


if __name__ == "__main__":
    main()
