import json

from modules.base_maestra.services import asignaciones_talento_por_unidad, latest_rows_for_type, map_staging_row


def test_mapea_denominacion_cargo_y_coordinador_a_cargo():
    row = map_staging_row(
        'talento_humano',
        {
            'Número de documento': '12345',
            'Nombre completo': 'Ana Prueba',
            'Denominación del cargo': 'Profesional psicosocial',
            'Coordinador a cargo': 'María Coordinadora',
            'Nombre de la unidad de servicio': 'UCA Ejemplo',
        },
        2,
        10,
        {'fundacion_id': 1, 'corporacion_id': 1},
    )
    assert row['cargo'] == 'PROFESIONAL PSICOSOCIAL'
    assert row['rol_normalizado'] == 'PSICOSOCIAL'
    assert row['coordinador'] == 'MARÍA COORDINADORA'
    assert row['unidad_servicio'] == 'UCA EJEMPLO'


def test_recupera_cargo_de_una_carga_anterior():
    class Repo:
        def ultima_carga(self, *args, **kwargs):
            return {'id': 7}

        def staging_rows(self, *args, **kwargs):
            return [{'cargo': '', 'coordinador': '', 'unidad_servicio': '', 'datos_json': json.dumps({
                'denominacion_del_cargo': 'Nutricionista dietista',
                'coordinador_a_cargo': 'Coordinadora Uno',
                'nombre_de_la_unidad_de_servicio': 'UCA Norte',
            })}]

    rows, _ = latest_rows_for_type(Repo(), 'talento_humano', 1)
    assert rows[0]['cargo'] == 'NUTRICIONISTA DIETISTA'
    assert rows[0]['rol_normalizado'] == 'NUTRICIONISTA'
    assert rows[0]['coordinador'] == 'COORDINADORA UNO'
    assert rows[0]['unidad_servicio'] == 'UCA NORTE'


def test_no_confunde_componente_con_cargo():
    row = map_staging_row(
        'talento_humano',
        {'Documento': '9', 'Nombre': 'Persona', 'Componente': 'Administrativo'},
        2,
        11,
        {'fundacion_id': 1},
    )
    assert row['cargo'] == ''
    assert row['rol_normalizado'] == 'TALENTO_HUMANO'


def test_resuelve_asignaciones_unicas_por_unidad_sin_inventar_ambiguas():
    asignaciones = asignaciones_talento_por_unidad([
        {'documento': '1', 'nombre_completo': 'Coordinadora Uno', 'cargo': 'Coordinador técnico', 'unidad_servicio': 'UCA Norte'},
        {'documento': '2', 'nombre_completo': 'Docente Uno', 'cargo': 'Agente educativo', 'unidad_servicio': 'UCA Norte', 'coordinador': 'Coordinadora Uno'},
        {'documento': '3', 'nombre_completo': 'Docente Dos', 'cargo': 'Docente', 'unidad_servicio': 'UCA Sur'},
        {'documento': '4', 'nombre_completo': 'Docente Tres', 'cargo': 'Docente', 'unidad_servicio': 'UCA Sur'},
        {'documento': '5', 'nombre_completo': 'Nutricionista', 'cargo': 'Nutricionista', 'unidad_servicio': 'UCA Talento'},
    ])
    assert asignaciones['UCA NORTE']['docente'] == 'DOCENTE UNO'
    assert asignaciones['UCA NORTE']['coordinador'] == 'COORDINADORA UNO'
    assert asignaciones['UCA SUR']['docente'] is None
    assert asignaciones['UCA SUR']['ambigua_docente'] is True
    assert asignaciones['UCA TALENTO']['total_talento'] == 1


if __name__ == '__main__':
    test_mapea_denominacion_cargo_y_coordinador_a_cargo()
    test_recupera_cargo_de_una_carga_anterior()
    test_no_confunde_componente_con_cargo()
    test_resuelve_asignaciones_unicas_por_unidad_sin_inventar_ambiguas()
    print('BASE_MAESTRA_TALENTO_MAPPING_PASS')
