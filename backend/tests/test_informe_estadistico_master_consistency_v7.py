import sqlite3

import pandas as pd

from modules.cruce_bases.informe_estadistico import _movimientos_version_maestra, _preparar_df_maestro


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


if __name__ == '__main__':
    test_report_rejects_header_row_as_child()
    test_report_uses_movements_from_same_master_version_and_tenant()
    print('2 master report consistency tests passed')
