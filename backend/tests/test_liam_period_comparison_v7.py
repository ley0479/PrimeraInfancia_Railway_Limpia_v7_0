"""Comparación mensual real, de solo lectura y aislada por fundación."""
from pathlib import Path
import sys
import tempfile

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from modules.asistente_capacitacion.orchestrator import LiamOrchestrator
from modules.cruce_bases.schema import SCHEMA_SQL
from modules.dbapi_compat import sqlite3


with tempfile.TemporaryDirectory() as tmp:
    database_path = str(Path(tmp) / 'comparison.db')
    connection = sqlite3.connect(database_path)
    connection.executescript(SCHEMA_SQL)
    connection.executemany(
        '''INSERT INTO cb_cruces(
            fundacion_id,periodo,total_actual,nuevos,retirados,cambios_unidad,
            cambios_docente,cambios_total,fecha_cruce
        ) VALUES(?,?,?,?,?,?,?,?,?)''',
        [
            (1, '2026-08', 100, 8, 3, 2, 1, 3, '2026-08-31T12:00:00'),
            (1, '2026-09', 110, 14, 4, 5, 2, 7, '2026-09-14T12:00:00'),
            (2, '2026-08', 900, 80, 30, 20, 10, 30, '2026-08-31T12:00:00'),
            (2, '2026-09', 990, 140, 40, 50, 20, 70, '2026-09-14T12:00:00'),
        ],
    )
    connection.commit()
    connection.close()

    result = LiamOrchestrator(database_path).run(
        'compare_periods',
        args={'period_a': '2026-08', 'period_b': '2026-09'},
        tenant_id=1,
        user={'id': 7, 'rol': 'COORDINADOR'},
    )
    assert result.result['scope']['foundation_id'] == 1
    assert result.result['scope']['cross_foundation'] is False
    assert result.result['snapshots'][0]['total_actual'] == 100
    assert result.result['snapshots'][1]['total_actual'] == 110
    assert result.result['comparison'][0]['variation'] == 10
    assert result.result['read_only'] is True
    assert result.telemetry['tool'] == 'compare_periods'

    missing = LiamOrchestrator(database_path).run(
        'compare_periods',
        args={'period_a': '2026-07', 'period_b': '2026-09'},
        tenant_id=1,
        user={'id': 7, 'rol': 'COORDINADOR'},
    )
    assert missing.result['complete'] is False
    assert all(item['variation'] is None for item in missing.result['comparison'])
    assert 'no se estiman' in missing.result['disclaimer']

print('LIAM_PERIOD_COMPARISON_V7_PASS')
