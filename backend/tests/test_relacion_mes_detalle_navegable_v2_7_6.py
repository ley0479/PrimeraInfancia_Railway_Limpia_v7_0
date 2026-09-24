from backend.services.relacion_mes_service import detallar_por_unidad


def test_detalle_usa_la_misma_clasificacion_y_conserva_identidad():
    rows = [
        {
            'unidad': 'UCA NECORA', 'nombre_completo': 'Gestante Uno', 'documento': '101',
            'grupo_etario': 'Gestante', 'estado': 'ACTIVO', 'docente': 'Docente A',
            'fecha_nacimiento': '', 'datos_json': '{}',
        },
        {
            'unidad': 'UCA NECORA', 'nombre_completo': 'Niña Uno', 'documento': '202',
            'grupo_etario': '', 'estado': 'ACTIVO', 'docente': 'Docente A',
            'fecha_nacimiento': '2026-06-10', 'datos_json': '{}',
        },
    ]

    detalle = detallar_por_unidad(rows, 2026, 9)

    assert [item['nombre'] for item in detalle['UCA NECORA']['gestantes']] == ['Gestante Uno']
    assert detalle['UCA NECORA']['menores_6'][0]['documento'] == '202'
    assert detalle['UCA NECORA']['menores_6'][0]['edad_meses'] == 2


def test_detalle_excluye_retirados():
    detalle = detallar_por_unidad([
        {'unidad': 'UCA NECORA', 'nombre_completo': 'Retirado', 'grupo_etario': 'Gestante', 'estado': 'RETIRADO'},
    ], 2026, 9)

    assert detalle == {}
