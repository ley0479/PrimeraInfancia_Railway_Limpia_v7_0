from __future__ import annotations

import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))

from modules.base_maestra.repository import BaseMaestraRepository


def stamp(days: int = 0, hours: int = 0) -> str:
    return (datetime(2026, 9, 23, 12, 0, 0) - timedelta(days=days, hours=hours)).isoformat(timespec='seconds')


def main() -> None:
    with tempfile.TemporaryDirectory(prefix='pi-retention-') as tmp:
        db = Path(tmp) / 'retention.sqlite3'
        repo = BaseMaestraRepository(str(db))
        repo.init_schema()
        with repo.connect() as conn:
            versions = [
                (1, 1, 'ARCHIVADA', 0, stamp(90), stamp(60)),
                (2, 1, 'ARCHIVADA', 0, stamp(50), stamp(20)),
                (3, 1, 'ACTIVA', 1, stamp(1), None),
                (4, 2, 'ACTIVA', 1, stamp(100), None),
                (5, 1, 'BORRADOR', 0, stamp(hours=72), None),
            ]
            conn.executemany(
                'INSERT INTO master_versiones(id,version_numero,fundacion_id,estado,activa,fecha_creacion,fecha_archivada) '
                'VALUES(?,?,1,?,?,?,?)',
                [(vid, number, state, active, created, archived) for vid, number, state, active, created, archived in versions if vid != 4],
            )
            conn.execute(
                "INSERT INTO master_versiones(id,version_numero,fundacion_id,estado,activa,fecha_creacion) VALUES(4,1,2,'ACTIVA',1,?)",
                (stamp(100),),
            )
            for vid in (1, 2, 3, 5):
                conn.execute(
                    'INSERT INTO master_ninos(version_id,activo,documento,fundacion_id,fecha_consolidacion) VALUES(?,?,?,?,?)',
                    (vid, 1 if vid == 3 else 0, f'DOC-{vid}', 1, stamp()),
                )
            conn.execute(
                "INSERT INTO cargas_archivos(id,tipo_fuente,fecha_carga,fundacion_id) VALUES(10,'cuentame',?,1)",
                (stamp(hours=72),),
            )
            conn.execute(
                'INSERT INTO staging_cuentame(carga_id,fundacion_id,fecha_creacion) VALUES(10,1,?)',
                (stamp(hours=72),),
            )
            conn.commit()

        result = repo.aplicar_retencion(1, ahora=datetime(2026, 9, 23, 12, 0, 0))
        assert result['version_activa_protegida'] == 3
        assert result['version_anterior_conservada'] == 2
        assert result['versiones_eliminadas'] == [1, 5]
        with repo.connect() as conn:
            assert [row[0] for row in conn.execute('SELECT id FROM master_versiones WHERE fundacion_id=1 ORDER BY id')] == [2, 3]
            assert conn.execute('SELECT COUNT(*) FROM master_ninos WHERE version_id IN (1,5)').fetchone()[0] == 0
            assert conn.execute('SELECT COUNT(*) FROM staging_cuentame WHERE carga_id=10').fetchone()[0] == 0
            assert conn.execute('SELECT COUNT(*) FROM master_versiones WHERE fundacion_id=2 AND activa=1').fetchone()[0] == 1
            assert conn.execute('SELECT COUNT(*) FROM master_retention_runs WHERE fundacion_id=1').fetchone()[0] == 1
        repeated = repo.aplicar_retencion(1, ahora=datetime(2026, 9, 23, 12, 0, 0))
        assert repeated['cargas_temporales_depuradas'] == 0
        with repo.connect() as conn:
            assert conn.execute('SELECT COUNT(*) FROM master_retention_runs WHERE fundacion_id=1').fetchone()[0] == 1
        print('OK: retención 30 días, máximo dos versiones, staging 48 horas y aislamiento tenant')


if __name__ == '__main__':
    main()
