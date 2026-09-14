"""Alertas tempranas: datos verificables, lenguaje de riesgo y tenant."""
from pathlib import Path
import sys,tempfile
BACKEND=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BACKEND))
from modules.asistente_capacitacion.orchestrator import LiamOrchestrator
from modules.dbapi_compat import sqlite3

with tempfile.TemporaryDirectory() as tmp:
    db=str(Path(tmp)/'warnings.db');c=sqlite3.connect(db)
    c.execute('''CREATE TABLE calendario_entregables(id INTEGER PRIMARY KEY,fundacion_id INTEGER,titulo TEXT,fecha_limite TEXT,modulo TEXT,responsable_nombre TEXT,coordinador TEXT,unidad TEXT,estado TEXT,prioridad TEXT,requiere_evidencia INTEGER,archivo_evidencia TEXT,fecha_entrega TEXT,clave_unica TEXT)''')
    c.executemany('INSERT INTO calendario_entregables VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',[(1,1,'Vencido','2020-01-01','x','Dora','Ana','UDS A','pendiente','Alta',0,None,None,'a'),(2,1,'Pendiente','2099-01-01','x','Dora','Ana','UDS A','pendiente','Media',0,None,None,'b'),(3,2,'Ajeno','2020-01-01','x','Dora','Ana','UDS Z','pendiente','Alta',0,None,None,'c')])
    c.execute('''CREATE TABLE master_ninos(id INTEGER PRIMARY KEY,fundacion_id INTEGER,activo INTEGER,documento TEXT,nombre_completo TEXT,fecha_nacimiento TEXT,grupo_etario TEXT,unidad_servicio TEXT,codigo_unidad TEXT,coordinador TEXT,docente TEXT)''')
    c.executemany('INSERT INTO master_ninos VALUES(?,?,?,?,?,?,?,?,?,?,?)',[(1,1,1,'D1','Uno','2021-01-01','3 a 5','UDS A','A','Ana','Dora'),(2,1,1,'D1','','','','UDS X','X','Ana','Dora'),(3,2,1,'D1','Ajeno','2021-01-01','3 a 5','UDS Z','Z','Ana','Dora')])
    c.execute('CREATE TABLE master_unidades(id INTEGER PRIMARY KEY,fundacion_id INTEGER,activo INTEGER,nombre TEXT,codigo_unidad TEXT,coordinador TEXT)');c.execute("INSERT INTO master_unidades VALUES(1,1,1,'UDS A','A','Ana')")
    c.execute('CREATE TABLE master_talento_humano(id INTEGER PRIMARY KEY,fundacion_id INTEGER,activo INTEGER,rol_normalizado TEXT,cargo TEXT,unidad_servicio TEXT,coordinador TEXT)')
    c.execute('CREATE TABLE master_inconsistencias(id INTEGER PRIMARY KEY,fundacion_id INTEGER,resuelta INTEGER)');c.commit();c.close()
    data=LiamOrchestrator(db).run('get_early_warnings',args={},tenant_id=1,user={'id':1,'rol':'COORDINADOR','nombre_completo':'Ana'}).result
    assert data['summary']=={'total_warnings':5,'critico':2,'alto':2,'preventivo':1}
    assert data['predictive_language']=='risk_only' and 'no son predicciones' in data['disclaimer']
    assert data['scope']['cross_foundation'] is False and data['role_scope']=='assigned_records'
    assert all(item['source'] in data['sources'] for item in data['warnings'])
    assert data['read_only'] is True and 'Ajeno' not in str(data)

print('LIAM_EARLY_WARNINGS_V7_PASS')
