from __future__ import annotations

import sqlite3

from modules.salud_nutricion.tematicas import SCHEMA_SQL, SCHEMA_VERSION, _approved_health_template, _audit, _can_access_unit, _institutional_product, _report_snapshot, _theme_candidates


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
    require(_can_access_unit('UCA 1',{'rol':'NUTRICIONISTA','unidades':['UCA 1']}), 'Bloqueó una unidad asignada.')
    require(not _can_access_unit('UCA 2',{'rol':'NUTRICIONISTA','unidades':['UCA 1']}), 'Permitió una unidad no asignada.')
    require(_can_access_unit('UCA 2',{'rol':'COORDINADOR','unidades':[]}), 'Restringió incorrectamente coordinación.')

    empty, empty_refs = _theme_candidates({'texto':'Documento administrativo sin contenido relacionado'})
    require(empty == [] and empty_refs == [], 'Un archivo sin temáticas produjo contenido inventado.')

    db=sqlite3.connect(':memory:')
    db.executescript('''CREATE TABLE idp_documentos(id INTEGER PRIMARY KEY);
      CREATE TABLE master_unidades(id INTEGER PRIMARY KEY);
      CREATE TABLE sn_actividades_integrales(id INTEGER PRIMARY KEY,fundacion_id INTEGER,unidad_nombre TEXT,fecha_ejecucion TEXT,metodologia TEXT,resultados TEXT,requiere_evidencias INTEGER);
      CREATE TABLE sn_actividad_participantes(id INTEGER PRIMARY KEY,fundacion_id INTEGER,actividad_id INTEGER,documento TEXT,nombre_completo TEXT,convocado INTEGER,asistio INTEGER,firma_estado TEXT,observaciones TEXT);
      CREATE TABLE sn_evidencias_integrales(id INTEGER PRIMARY KEY,fundacion_id INTEGER,actividad_id INTEGER,tipo TEXT,titulo TEXT,nombre_original TEXT,sha256 TEXT,fecha_carga TEXT,activo INTEGER);
      CREATE TABLE sn_productos_actividad(id INTEGER PRIMARY KEY);''')
    db.executescript(SCHEMA_SQL)
    db.executescript(SCHEMA_SQL)
    tables={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    require({'sn_materiales_tematicos','sn_temas','sn_tema_correcciones','sn_tema_asignaciones','sn_actividad_temas','sn_actividad_calendario','sn_informes_tematicos'} <= tables, 'Migración temática incompleta.')
    report_columns={row[1] for row in db.execute('PRAGMA table_info(sn_informes_tematicos)')}
    require({'plantilla_codigo','plantilla_version','producto_sha256'} <= report_columns,'El informe no congela plantilla e integridad del producto.')
    db.row_factory=sqlite3.Row
    db.execute("INSERT INTO sn_actividades_integrales VALUES(1,1,'UCA 1',NULL,NULL,NULL,1)")
    class Repo:
        def fetch_one(self,sql,params=()):
            row=db.execute(sql,params).fetchone();return dict(row) if row else None
        def fetch_all(self,sql,params=()):return [dict(row) for row in db.execute(sql,params).fetchall()]
    snapshot,digest,missing=_report_snapshot(Repo(),1,1)
    require(snapshot['conteos']['asistentes']==0 and len(digest)==64,'Instantánea determinística inválida.')
    require('fecha real de ejecución' in missing and 'listado de participantes vinculado' in missing and 'evidencias auténticas' in missing,'El borrador incompleto ocultó faltantes.')
    require(_approved_health_template(Repo(),1) is None,'Una plantilla inexistente no puede declararse institucional.')
    class TemplateRepo:
        def __init__(self): self.params=None
        def fetch_one(self,sql,params=()):
            self.params=params
            require("v.fundacion_id=?" in sql and "p.scope='GLOBAL'" in sql,'La plantilla no quedó aislada por tenant/global.')
            require("v.estado IN ('APROBADA','ACTIVA')" in sql,'Se aceptó una plantilla sin aprobación.')
            return {'plantilla_version_id':7,'codigo':'INFORME_SALUD_NUTRICION'}
    template_repo=TemplateRepo(); selected=_approved_health_template(template_repo,9)
    require(selected['plantilla_version_id']==7 and template_repo.params==(9,9,'INFORME_SALUD_NUTRICION','INFORME_SALUD_NUTRICION',9),'La selección no priorizó el tenant autenticado.')
    require(not _institutional_product({'plantilla_codigo':'SN-INFORME','plantilla_version':'INTERNA-1','nombre_archivo':'informe.pdf'}),'El PDF interno fue tratado como institucional.')
    require(_institutional_product({'plantilla_codigo':'INFORME_SALUD_NUTRICION','plantilla_version':'2026.1','nombre_archivo':'informe.docx'}),'No reconoció un informe generado con plantilla institucional versionada.')
    class AuditRepo:
        def __init__(self): self.event=None
        def log(self,*args,**kwargs): self.event=(args,kwargs)
    audit_repo=AuditRepo(); _audit(audit_repo,'PUBLICAR_TEMATICAS_SALUD','sn_materiales_tematicos',4,{'username':'revisor'}, {'periodo':'2026-09','asignaciones_creadas':3})
    require(audit_repo.event[0][:3]==('PUBLICAR_TEMATICAS_SALUD','sn_materiales_tematicos',4) and audit_repo.event[1]['usuario']=='revisor','La auditoría temática no registró actor y recurso.')
    db.close()
    print('PASS test_salud_tematicas_phase1_v1 (fixture textual; prueba visual real NO VERIFICADA)')


if __name__ == '__main__':
    main()
