import sqlite3

from modules.asistente_capacitacion.action_intents import propose_action, propose_read_actions
from modules.asistente_capacitacion.tool_registry import execute


def _database(path):
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE fundaciones(id INTEGER PRIMARY KEY, nombre TEXT);
        CREATE TABLE usuarios_app(id INTEGER PRIMARY KEY, username TEXT, email TEXT, rol TEXT,
          nombre_completo TEXT, activo INTEGER, estado TEXT, fecha_ultima_conexion TEXT, fundacion_id INTEGER);
        CREATE TABLE master_ninos(id INTEGER PRIMARY KEY, documento TEXT, nombre_completo TEXT,
          fecha_nacimiento TEXT, edad_meses INTEGER, grupo_etario TEXT, sexo TEXT, unidad_servicio TEXT,
          codigo_unidad TEXT, coordinador TEXT, docente TEXT, modalidad TEXT, estado TEXT, activo INTEGER, fundacion_id INTEGER);
        CREATE TABLE master_unidades(id INTEGER PRIMARY KEY, nombre TEXT, codigo_unidad TEXT, coordinador TEXT,
          total_ninos INTEGER,total_talento INTEGER,modalidad TEXT,activo INTEGER, fundacion_id INTEGER);
        CREATE TABLE master_versiones(id INTEGER PRIMARY KEY,estado TEXT,fecha_publicacion TEXT,activa INTEGER,fundacion_id INTEGER);
        CREATE TABLE master_talento_humano(id INTEGER PRIMARY KEY,nombre_completo TEXT,cargo TEXT,rol_normalizado TEXT,
          unidad_servicio TEXT,coordinador TEXT,estado TEXT,activo INTEGER,fundacion_id INTEGER);
        CREATE TABLE cargas_archivos(id INTEGER PRIMARY KEY,tipo_fuente TEXT,nombre_archivo_original TEXT,fecha_carga TEXT,
          total_registros INTEGER,registros_validos INTEGER,registros_error INTEGER,estado TEXT,fundacion_id INTEGER);
        CREATE TABLE master_movimientos(id INTEGER PRIMARY KEY,version_id INTEGER,tipo_movimiento TEXT,fundacion_id INTEGER);
        CREATE TABLE sn_valoraciones(id INTEGER PRIMARY KEY, estado TEXT, fundacion_id INTEGER);
        """
    )
    conn.executemany("INSERT INTO fundaciones VALUES(?,?)", [(1, "Uno"), (2, "Dos")])
    conn.executemany(
        "INSERT INTO usuarios_app VALUES(?,?,?,?,?,?,?,?,?)",
        [(1,"coord1","c1@example.test","COORDINADOR","Coord Uno",1,"ACTIVO",None,1),
         (2,"doc1","d1@example.test","DOCENTE","Doc Uno",1,"ACTIVO",None,1),
         (3,"coord2","c2@example.test","COORDINADOR","Coord Dos",1,"ACTIVO",None,2)],
    )
    conn.executemany(
        "INSERT INTO master_ninos VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [(1,"101","Niño Uno","2022-01-01",48,"3 A 5 AÑOS","M","UDS Norte","N","Coord Uno","Doc Uno","FAMILIAR","ACTIVO",1,1),
         (2,"102","Niña Dos",None,10,"6 A 11 MESES","F","UDS Sur","S","Coord Uno","Doc Uno","FAMILIAR","ACTIVO",1,1),
         (3,"999","Otro Tenant","2021-01-01",60,"3 A 5 AÑOS","M","UDS Ajena","X","Coord Dos","Doc Dos","FAMILIAR","ACTIVO",1,2)],
    )
    conn.executemany("INSERT INTO master_unidades VALUES(?,?,?,?,?,?,?,?,?)", [(1,"UDS Norte","N","Coord Uno",1,2,"FAMILIAR",1,1),(2,"UDS Sur","S","Coord Tres",1,1,"FAMILIAR",1,1),(3,"UDS Ajena","X","Coord Dos",1,1,"FAMILIAR",1,2)])
    conn.executemany("INSERT INTO master_versiones VALUES(?,?,?,?,?)",[(8,"PUBLICADA","2026-09-14",1,1),(9,"PUBLICADA","2026-09-14",1,2)])
    conn.executemany("INSERT INTO master_talento_humano VALUES(?,?,?,?,?,?,?,?,?)",[(1,"Coord Cuatro","Coordinador","COORDINADOR","UDS Norte","Coord Cuatro","ACTIVO",1,1),(2,"Psicóloga Uno","Psicología","PSICOSOCIAL","UDS Norte","Coord Cuatro","ACTIVO",1,1),(3,"Ajeno","Docente","DOCENTE","UDS Ajena","Coord Dos","ACTIVO",1,2)])
    conn.executemany("INSERT INTO cargas_archivos VALUES(?,?,?,?,?,?,?,?,?)",[(1,"cuentame","ninos.xlsx","2026-09-14",2,2,0,"validado",1),(2,"talento_humano","talento.xlsx","2026-09-14",2,2,0,"validado",1)])
    conn.executemany("INSERT INTO master_movimientos VALUES(?,?,?,?)",[(1,8,"NUEVO",1),(2,8,"PERMANECE",1),(3,9,"NUEVO",2)])
    conn.executemany("INSERT INTO sn_valoraciones VALUES(?,?,?)", [(1,"VALIDADA",1),(2,"PENDIENTE",1),(3,"CRITICA",2)])
    conn.commit();conn.close()


def test_summary_is_strictly_scoped_to_authenticated_foundation(tmp_path):
    db=tmp_path/'liam.db';_database(db)
    result=execute('get_foundation_data_summary',args={'foundation_id':2},database_path=str(db),tenant_id=1,user={'rol':'DOCENTE'})
    assert result['scope']=={'foundation_id':1,'foundation_name':'Uno','source':'authenticated_session','cross_foundation':False}
    assert result['profiles']['total']==2
    assert result['profiles']['coordinators']==3
    assert result['beneficiaries']['total']==2
    assert result['units']['registered_active']==2
    assert {x['unit'] for x in result['units']['items']}=={'UDS Norte','UDS Sur'}
    assert result['data_quality']['incomplete_fields']['fecha_nacimiento']==1


def test_summary_maps_coordinators_teams_sources_and_movements(tmp_path):
    db=tmp_path/'liam-complete.db';_database(db)
    result=execute('get_foundation_data_summary',args={},database_path=str(db),tenant_id=1,user={'rol':'SUPERADMIN'})
    assert result['profiles']['coordinators']==3
    assert {x['name'] for x in result['profiles']['coordinator_items']}=={'Coord Uno','Coord Tres','Coord Cuatro'}
    assert result['profiles']['interdisciplinary_team_total']==2
    assert result['units']['registered_active']==2
    assert result['sources']['total_sources']==2
    assert result['movements']['total']==2
    assert result['master_version']['id']==8


def test_profiles_are_scoped_filterable_and_paginated(tmp_path):
    db=tmp_path/'liam.db';_database(db)
    result=execute('list_foundation_profiles',args={'foundation_id':2,'role':'DOCENTE','limit':10},database_path=str(db),tenant_id=1,user={'rol':'NUTRICIONISTA'})
    assert result['total']==1
    assert result['profiles'][0]['username']=='doc1'
    assert all(row['username']!='coord2' for row in result['profiles'])


def test_foundation_questions_route_to_read_only_tools():
    assert propose_action('¿Cuántos niños hay por grupo etario?')['server_tool']=='get_foundation_data_summary'
    assert propose_action('Muéstrame los perfiles de la fundación')['server_tool']=='list_foundation_profiles'


def test_beneficiary_search_and_multitask_plan_are_tenant_scoped(tmp_path):
    db=tmp_path/'liam.db';_database(db)
    found=execute('search_foundation_beneficiaries',args={'query':'Niño','foundation_id':2},database_path=str(db),tenant_id=1,user={'rol':'DOCENTE'})
    assert found['total']==1 and found['beneficiaries'][0]['documento']=='101'
    assert all(item['documento']!='999' for item in found['beneficiaries'])
    plan=propose_read_actions('¿Cuántos niños hay y cuáles son mis tareas pendientes?')
    assert [item['server_tool'] for item in plan]==['get_foundation_data_summary','get_pending_activities_summary']


def test_module_summary_is_scoped_and_can_join_multitask_plan(tmp_path):
    db=tmp_path/'liam.db';_database(db)
    result=execute('get_platform_module_summary',args={'module':'salud-nutricion','foundation_id':2},database_path=str(db),tenant_id=1,user={'rol':'DOCENTE'})
    assert result['datasets'][0]['total']==2
    assert sum(x['total'] for x in result['datasets'][0]['by_status'])==2
    plan=propose_read_actions('Dime cuántos niños hay y el resumen de salud y nutrición')
    assert {x['server_tool'] for x in plan}=={'get_foundation_data_summary','get_platform_module_summary'}


def test_health_annex_reports_overweight_and_malnutrition_without_crossing_tenants(tmp_path):
    db=tmp_path/'health.db';conn=sqlite3.connect(db)
    conn.executescript('''CREATE TABLE master_ninos(id INTEGER,documento TEXT,tipo_documento TEXT,nombre_completo TEXT,grupo_etario TEXT,unidad_servicio TEXT,carne_salud TEXT,control_crecimiento TEXT,carne_crecimiento TEXT,perimetro_braquial REAL,diagnostico_nutricional TEXT,estado_nutricional TEXT,datos_json TEXT,activo INTEGER,fundacion_id INTEGER);
      CREATE TABLE sn_valoraciones(id INTEGER,documento TEXT,diagnostico_global TEXT,clasificacion_profesional TEXT,nivel_alerta TEXT,perimetro_braquial_cm REAL,fecha_valoracion TEXT,fundacion_id INTEGER);''')
    conn.executemany('INSERT INTO master_ninos VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',[(1,'1','RC','Ana','3 A 5','UDS 1','SI','SI','SI',14,'Sobrepeso','Sobrepeso','{}',1,1),(2,'2','RC','Beto','3 A 5','UDS 1','NO','NO','NO',12,'Desnutrición moderada','Desnutrición','{}',1,1),(3,'3','RC','Ajeno','3 A 5','UDS X','SI','SI','SI',15,'Obesidad','Obesidad','{}',1,2)])
    conn.commit();conn.close()
    result=execute('get_monthly_health_indicators',args={},database_path=str(db),tenant_id=1,user={'rol':'NUTRICIONISTA'})
    assert result['indicators']['total']==2
    assert result['indicators']['sobrepeso']==1 and result['indicators']['desnutricion']==1
    assert {x['name'] for x in result['nutritional_annex']}=={'Ana','Beto'}
