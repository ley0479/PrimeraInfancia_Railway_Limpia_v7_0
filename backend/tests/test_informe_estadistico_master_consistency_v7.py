import sqlite3
import tempfile
from pathlib import Path

import pandas as pd

from modules.cruce_bases.informe_estadistico import (
    _cargar_base_maestra,
    _cargar_base_actual_cruce,
    _movimientos_version_maestra,
    _preparar_df_maestro,
)


def test_report_rejects_header_row_as_child():
    frame = pd.DataFrame([{
        'documento': 'documento', 'nombre_completo': 'NOMBRE_COMPLETO',
        'unidad_servicio': 'UNIDAD SERVICIO', 'estado': 'ESTADO',
    }])
    try:
        _preparar_df_maestro(frame, 'master_ninos')
    except ValueError as exc:
        assert 'fila de encabezados' in str(exc)
    else:
        raise AssertionError('Una fila de encabezados fue contada como niño.')


def test_report_uses_movements_from_same_master_version_and_tenant():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute('''CREATE TABLE master_movimientos(
        id INTEGER, version_id INTEGER, fundacion_id INTEGER, tipo_movimiento TEXT,
        documento TEXT, unidad_anterior TEXT, unidad_nueva TEXT)''')
    conn.executemany('INSERT INTO master_movimientos VALUES(?,?,?,?,?,?,?)', [
        (1, 8, 2, 'NUEVO', 'A', None, 'U1'),
        (2, 8, 2, 'PERMANECE', 'B', 'U1', 'U1'),
        (3, 7, 2, 'RETIRADO', 'OLD', 'U1', None),
        (4, 8, 3, 'NUEVO', 'OTHER-TENANT', None, 'UX'),
    ])
    movements = _movimientos_version_maestra(conn, 8, 2)
    assert [row['documento'] for row in movements['nuevos']] == ['A']
    assert [row['documento'] for row in movements['permanecen']] == ['B']
    assert movements['retirados'] == []


def test_report_reads_real_rows_from_active_master_version():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute('''CREATE TABLE master_versiones(
        id INTEGER, fundacion_id INTEGER, activa INTEGER, fecha_publicacion TEXT)''')
    conn.execute('''CREATE TABLE master_ninos(
        id INTEGER, version_id INTEGER, fundacion_id INTEGER, activo INTEGER,
        documento TEXT, nombres TEXT, apellidos TEXT, unidad_servicio TEXT)''')
    conn.execute("INSERT INTO master_versiones VALUES(25,2,1,'2026-09-21T19:59:25')")
    conn.executemany('INSERT INTO master_ninos VALUES(?,?,?,?,?,?,?,?)', [
        (1, 25, 2, 1, '1022172262', 'EMANUEL', 'RODRIGUEZ', 'BAJO PACURITA'),
        (2, 25, 2, 1, '1077487980', 'KYLIAN', 'FIGUEROA', 'BENDICION 1'),
    ])
    frame, duplicados, fuente = _cargar_base_maestra(conn, 2, False)
    assert fuente == 'master_ninos'
    assert duplicados == []
    assert frame['documento'].tolist() == ['1022172262', '1077487980']
    assert frame['unidad'].tolist() == ['BAJO PACURITA', 'BENDICION 1']


def test_report_scopes_units_to_current_cross_file():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'base_actual.csv'
        path.write_text(
            'Documento del beneficiario;Nombre;Nombre de la unidad de servicio\n'
            '10001;NIÑO UNO;PROGRAMA NUEVO A\n'
            '10002;NIÑO DOS;PROGRAMA NUEVO B\n',
            encoding='utf-8',
        )
        loaded = _cargar_base_actual_cruce({'ruta_actual': str(path)})
        assert loaded is not None
        frame, _, fuente = loaded
        assert fuente == 'base_actual_cruce'
        assert set(frame['unidad']) == {'PROGRAMA NUEVO A', 'PROGRAMA NUEVO B'}
        assert 'UCA ALTO NECORA' not in set(frame['unidad'])


if __name__ == '__main__':
    test_report_rejects_header_row_as_child()
    test_report_uses_movements_from_same_master_version_and_tenant()
    test_report_reads_real_rows_from_active_master_version()
    test_report_scopes_units_to_current_cross_file()
    print('4 master report consistency tests passed')
