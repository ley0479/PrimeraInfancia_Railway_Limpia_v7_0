"""Herencia global/fundación y frontera de DDL de identidad v7."""
from pathlib import Path
import sys
import tempfile

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from migrations.migrate_identidad_global_v7 import migrate
from modules.dbapi_compat import sqlite3
from modules.institucional_normativo import init_schema, resolver_identidad_efectiva


def main():
    with tempfile.TemporaryDirectory() as tmp:
        database = str(Path(tmp) / 'identity.db')
        migrate(database)
        init_schema(database)  # Preparación controlada de la base temporal.
        conn = sqlite3.connect(database)
        now = '2026-08-18T00:00:00+00:00'
        conn.execute(
            '''UPDATE configuracion_global_plataforma SET nombre_plataforma=?, sigla_plataforma=?,
               nombre_administrador_general=?, cargo_administrador_general=?,
               color_primario_global=?, color_secundario_global=?, updated_at=? WHERE id=1''',
            ('Plataforma Global', 'PG', 'Admin Global', 'Dirección General', '#112233', '#445566', now),
        )
        conn.execute(
            '''INSERT INTO configuracion_institucional
               (corporacion_id,fundacion_id,nombre_corporacion,sigla,color_primario,activo,created_at,updated_at)
               VALUES (7,7,?,?,?,?,?,?)''',
            ('Fundación Siete', '', '#abcdef', 1, now, now),
        )
        conn.execute(
            '''UPDATE configuracion_institucional SET nombre_admin=?, cargo_admin=?, foto_admin_path=?
               WHERE fundacion_id=7''',
            ('Admin Local Antiguo', 'Cargo Local', str(Path(tmp) / 'foto-local.png')),
        )
        conn.commit()
        conn.close()

        global_only = resolver_identidad_efectiva(database, str(BACKEND), None, tmp)
        assert global_only['nombre_plataforma'] == 'Plataforma Global'
        assert global_only['administrador_general']['nombre'] == 'Admin Global'

        inherited = resolver_identidad_efectiva(database, str(BACKEND), 8, tmp)
        assert inherited['nombre_plataforma'] == 'Plataforma Global'
        assert inherited['sigla'] == 'PG'
        assert inherited['color_secundario'] == '#445566'

        mixed = resolver_identidad_efectiva(database, str(BACKEND), 7, tmp)
        assert mixed['nombre_corporacion'] == 'Fundación Siete'
        assert mixed['sigla'] == 'PG'
        assert mixed['color_primario'] == '#abcdef'
        assert mixed['cargo_admin'] == 'Dirección General'
        assert mixed['nombre_admin'] == 'Admin Global'
        assert mixed['foto_admin_url'] is None
        assert mixed['administrador_fundacion']['nombre'] == 'Admin Local Antiguo'

    source = (BACKEND / 'modules' / 'institucional_normativo.py').read_text(encoding='utf-8')
    register_body = source.split('def register_institucional_normativo', 1)[1]
    assert 'init_schema(database_path)' not in register_body
    print('Identidad efectiva global/fundación/fallback y DDL boundary: PASS')


if __name__ == '__main__':
    main()
