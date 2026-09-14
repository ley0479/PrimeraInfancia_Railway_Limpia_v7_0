import sqlite3

from modules.asistente_capacitacion.action_intents import propose_action
from modules.asistente_capacitacion.tool_registry import execute


def _database(path):
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE fundaciones(id INTEGER PRIMARY KEY, nombre TEXT);
        CREATE TABLE usuarios_app(id INTEGER PRIMARY KEY, username TEXT, email TEXT, rol TEXT,
          nombre_completo TEXT, activo INTEGER, estado TEXT, fecha_ultima_conexion TEXT, fundacion_id INTEGER);
        CREATE TABLE master_ninos(id INTEGER PRIMARY KEY, documento TEXT, nombre_completo TEXT,
          fecha_nacimiento TEXT, edad_meses INTEGER, grupo_etario TEXT, unidad_servicio TEXT,
          codigo_unidad TEXT, estado TEXT, activo INTEGER, fundacion_id INTEGER);
        CREATE TABLE master_unidades(id INTEGER PRIMARY KEY, nombre TEXT, activo INTEGER, fundacion_id INTEGER);
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
        "INSERT INTO master_ninos VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        [(1,"101","Niño Uno","2022-01-01",48,"3 A 5 AÑOS","UDS Norte","N", "ACTIVO",1,1),
         (2,"102","Niña Dos",None,10,"6 A 11 MESES","UDS Sur","S","ACTIVO",1,1),
         (3,"999","Otro Tenant","2021-01-01",60,"3 A 5 AÑOS","UDS Ajena","X","ACTIVO",1,2)],
    )
    conn.executemany("INSERT INTO master_unidades VALUES(?,?,?,?)", [(1,"UDS Norte",1,1),(2,"UDS Sur",1,1),(3,"UDS Ajena",1,2)])
    conn.commit();conn.close()


def test_summary_is_strictly_scoped_to_authenticated_foundation(tmp_path):
    db=tmp_path/'liam.db';_database(db)
    result=execute('get_foundation_data_summary',args={'foundation_id':2},database_path=str(db),tenant_id=1,user={'rol':'DOCENTE'})
    assert result['scope']=={'foundation_id':1,'foundation_name':'Uno','source':'authenticated_session','cross_foundation':False}
    assert result['profiles']['total']==2
    assert result['profiles']['coordinators']==1
    assert result['beneficiaries']['total']==2
    assert result['units']['registered_active']==2
    assert {x['unit'] for x in result['units']['items']}=={'UDS Norte','UDS Sur'}
    assert result['data_quality']['incomplete_fields']['fecha_nacimiento']==1


def test_profiles_are_scoped_filterable_and_paginated(tmp_path):
    db=tmp_path/'liam.db';_database(db)
    result=execute('list_foundation_profiles',args={'foundation_id':2,'role':'DOCENTE','limit':10},database_path=str(db),tenant_id=1,user={'rol':'NUTRICIONISTA'})
    assert result['total']==1
    assert result['profiles'][0]['username']=='doc1'
    assert all(row['username']!='coord2' for row in result['profiles'])


def test_foundation_questions_route_to_read_only_tools():
    assert propose_action('¿Cuántos niños hay por grupo etario?')['server_tool']=='get_foundation_data_summary'
    assert propose_action('Muéstrame los perfiles de la fundación')['server_tool']=='list_foundation_profiles'
