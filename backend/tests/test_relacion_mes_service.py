from services.relacion_mes_service import cantidades, consolidar_por_unidad


def test_clasifica_todos_los_rangos_sin_convertir_vacios_en_cero():
    rows = [
        {'unidad': 'UCA 1', 'grupo_etario': 'GESTANTE', 'edad_meses': None, 'estado': 'ACTIVO', 'docente': 'ANA'},
        {'unidad': 'UCA 1', 'grupo_etario': '0 A 6 MESES Y GESTANTES', 'edad_meses': 4, 'estado': 'ACTIVO', 'docente': 'ANA'},
        {'unidad': 'UCA 1', 'grupo_etario': '6 A 11 MESES 29 DIAS', 'edad_meses': 6, 'estado': 'ACTIVO'},
        {'unidad': 'UCA 1', 'grupo_etario': '6 A 11 MESES 29 DIAS', 'edad_meses': 11, 'estado': 'ACTIVO'},
        {'unidad': 'UCA 1', 'grupo_etario': '1 A 2 AÑOS 11 MESES', 'edad_meses': 35, 'estado': 'ACTIVO'},
        {'unidad': 'UCA 1', 'grupo_etario': '3 A 5 AÑOS 11 MESES', 'edad_meses': 71, 'estado': 'ACTIVO'},
        {'unidad': 'UCA 1', 'grupo_etario': 'MADRE LACTANTE', 'edad_meses': 20, 'estado': 'ACTIVO'},
        {'unidad': 'UCA 1', 'grupo_etario': '', 'edad_meses': None, 'estado': 'ACTIVO'},
    ]

    item = consolidar_por_unidad(rows, 2026, 8)['UCA 1']

    assert item['gestantes'] == 1
    assert item['menores_6'] == 1
    assert item['seis_11'] == 2
    assert item['uno_2'] == 2
    assert item['tres_5'] == 1
    assert item['sin_clasificar'] == 1
    assert item['verduras_dobles'] == 2
    assert item['_docentes'].most_common(1)[0] == ('ANA', 2)


def test_calcula_huevos_cubetas_y_paquetes_de_siete():
    item = {
        'gestantes': 1,
        'menores_6': 1,
        'seis_11': 2,
        'uno_2': 1,
        'tres_5': 1,
        'sin_clasificar': 1,
        'verduras_dobles': 2,
    }

    qty = cantidades(item)

    assert qty == {
        'total': 7,
        'huevos_30': 150,
        'huevos_15': 30,
        'total_huevos': 180,
        'cubetas_30': 6,
        'paquetes_7': 0,
        'cubetas_sueltas': 6,
        'verduras': 9,
        'olla_comunitaria': 1,
        'bienestarina': 7,
    }

    veinte = cantidades({'gestantes': 0, 'menores_6': 0, 'seis_11': 0, 'uno_2': 20, 'tres_5': 0})
    assert veinte['total_huevos'] == 600
    assert veinte['cubetas_30'] == 20
    assert veinte['paquetes_7'] == 2
    assert veinte['cubetas_sueltas'] == 6


if __name__ == '__main__':
    test_clasifica_todos_los_rangos_sin_convertir_vacios_en_cero()
    test_calcula_huevos_cubetas_y_paquetes_de_siete()
    print('OK: relación del mes')
