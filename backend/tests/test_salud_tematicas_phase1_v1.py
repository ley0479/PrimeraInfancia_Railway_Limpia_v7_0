from __future__ import annotations

import sqlite3

from modules.salud_nutricion.tematicas import SCHEMA_SQL, SCHEMA_VERSION, _theme_candidates


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    # Fixture textual: valida el contrato, no sustituye la prueba visual del afiche real.
    raw = {
        'motor': 'FIXTURE_TEXTUAL_NO_VISUAL',
        'texto': '''Pequeñas acciones, grandes cambios en la salud, la inocuidad y el cuidado del ambiente
Lactancia materna: técnicas de amamantamiento
Contaminación cruzada: situaciones que la favorecen y prevención
Código de colores para la separación de residuos sólidos
Resolución 2184 de 2019''',
        'paginas': [{'pagina': 1}],
    }
    themes, references = _theme_candidates(raw)
    require(SCHEMA_VERSION == '1.0', 'Cambió el contrato sin versionarlo.')
    require(len(themes) == 3, 'El fixture temático no produjo tres temas revisables.')
    require({x['categoria_sugerida'] for x in themes} == {'LACTANCIA_MATERNA','INOCUIDAD_ALIMENTARIA','GESTION_AMBIENTAL'}, 'Categorías propuestas incorrectas.')
    require(all(x['procedencia']['titulo_original'] == 'EXTRAIDO' for x in themes), 'No se distinguió contenido extraído.')
    require(all(x['procedencia']['titulo_normalizado'] == 'PROPUESTO_IA' for x in themes), 'No se distinguió contenido propuesto.')
    require(references == [{'texto':'Resolución 2184 de 2019','tipo':'REFERENCIA_DOCUMENTAL_EXTRAIDA','vigencia_verificada':False}], 'La referencia normativa no quedó explícita y sin certificar.')
    require(not any('fecha' in x for x in themes), '2019 se convirtió indebidamente en fecha de actividad.')
    require(not any(key in raw for key in ('periodo','unidad','asistentes','resultados','ejecucion')), 'El fixture inventó hechos operativos.')

    empty, empty_refs = _theme_candidates({'texto':'Documento administrativo sin contenido relacionado'})
    require(empty == [] and empty_refs == [], 'Un archivo sin temáticas produjo contenido inventado.')

    db=sqlite3.connect(':memory:')
    db.executescript('CREATE TABLE idp_documentos(id INTEGER PRIMARY KEY); CREATE TABLE master_unidades(id INTEGER PRIMARY KEY); CREATE TABLE sn_actividades_integrales(id INTEGER PRIMARY KEY);')
    db.executescript(SCHEMA_SQL)
    db.executescript(SCHEMA_SQL)
    tables={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    require({'sn_materiales_tematicos','sn_temas','sn_tema_correcciones','sn_tema_asignaciones','sn_actividad_temas'} <= tables, 'Migración temática incompleta.')
    db.close()
    print('PASS test_salud_tematicas_phase1_v1 (fixture textual; prueba visual real NO VERIFICADA)')


if __name__ == '__main__':
    main()
