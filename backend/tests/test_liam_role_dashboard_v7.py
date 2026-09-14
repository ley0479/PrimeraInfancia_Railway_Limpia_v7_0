"""Tablero por rol con degradación segura y aislamiento institucional."""
from pathlib import Path
import sys,tempfile
BACKEND=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BACKEND))
from modules.dbapi_compat import sqlite3
from modules.asistente_capacitacion.tool_registry import execute

with tempfile.TemporaryDirectory() as tmp:
    database=str(Path(tmp)/'role-dashboard.db');conn=sqlite3.connect(database)
    conn.execute('''CREATE TABLE calendario_entregables(id INTEGER PRIMARY KEY,fundacion_id INTEGER,titulo TEXT,fecha_limite TEXT,modulo TEXT,responsable_nombre TEXT,coordinador TEXT,unidad TEXT,estado TEXT,prioridad TEXT,requiere_evidencia INTEGER,archivo_evidencia TEXT,fecha_entrega TEXT,clave_unica TEXT)''')
    conn.executemany('INSERT INTO calendario_entregables VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',[(1,1,'Pendiente propio','2099-09-20','reportes','Dora','Ana','UDS A','pendiente','Alta',0,None,None,'a'),(2,2,'Otro tenant','2020-01-01','reportes','Dora','Ana','UDS X','pendiente','Alta',0,None,None,'b')])
    conn.commit();conn.close()
    result=execute('get_role_dashboard',args={},database_path=database,tenant_id=1,user={'id':4,'rol':'DOCENTE','nombre_completo':'Dora'})
    assert result['role']=='DOCENTE' and result['scope']['foundation_id']==1
    assert result['sections']['deliverables']['summary']['expected']==1
    assert 'Otro tenant' not in str(result)
    assert result['partial'] is True and result['read_only'] is True
    metrics={item['label']:item['value'] for item in result['metrics']}
    assert metrics['Entregables pendientes']==1
    assert metrics['Tareas pendientes']=='NO DISPONIBLE'
print('LIAM_ROLE_DASHBOARD_V7_PASS')
