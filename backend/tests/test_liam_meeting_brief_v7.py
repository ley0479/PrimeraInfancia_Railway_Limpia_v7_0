"""Resumen de reunión: solo lectura, rol y tenant."""
from pathlib import Path
import sys,tempfile
BACKEND=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BACKEND))
from modules.dbapi_compat import sqlite3
from modules.asistente_capacitacion.tool_registry import execute

with tempfile.TemporaryDirectory() as tmp:
    database=str(Path(tmp)/'meeting.db');conn=sqlite3.connect(database)
    conn.execute('''CREATE TABLE calendario_entregables(id INTEGER PRIMARY KEY,fundacion_id INTEGER,titulo TEXT,fecha_limite TEXT,modulo TEXT,responsable_nombre TEXT,coordinador TEXT,unidad TEXT,estado TEXT,prioridad TEXT,requiere_evidencia INTEGER,archivo_evidencia TEXT,fecha_entrega TEXT,clave_unica TEXT)''')
    conn.executemany('INSERT INTO calendario_entregables VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',[(1,1,'Informe propio','2026-09-01','reportes','Dora','Ana','UDS A','pendiente','Alta',0,None,None,'a'),(2,2,'Informe ajeno','2026-09-01','reportes','Dora','Ana','UDS X','pendiente','Alta',0,None,None,'b')])
    conn.commit();conn.close()
    result=execute('prepare_meeting_brief',args={'period':'2026-09'},database_path=database,tenant_id=1,user={'id':4,'rol':'COORDINADOR','nombre_completo':'Ana'})
    assert result['draft_only'] is True and result['tasks_created'] is False and result['read_only'] is True
    assert result['scope']['foundation_id']==1 and result['sections']['dashboard']['sections']['deliverables']['summary']['expected']==1
    assert 'Informe ajeno' not in str(result)
    try:execute('prepare_meeting_brief',args={},database_path=database,tenant_id=1,user={'id':5,'rol':'DOCENTE'})
    except PermissionError:pass
    else:raise AssertionError('Un rol no autorizado preparó un resumen gerencial.')
print('LIAM_MEETING_BRIEF_V7_PASS')
