"""Borrador de comunicación: audiencia derivada, sin envío y con alcance."""
from pathlib import Path
import sys,tempfile
BACKEND=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BACKEND))
from modules.asistente_capacitacion.orchestrator import LiamOrchestrator
from modules.dbapi_compat import sqlite3

with tempfile.TemporaryDirectory() as tmp:
    db=str(Path(tmp)/'draft.db');c=sqlite3.connect(db)
    c.execute('''CREATE TABLE calendario_entregables(id INTEGER PRIMARY KEY,fundacion_id INTEGER,titulo TEXT,fecha_limite TEXT,modulo TEXT,responsable_nombre TEXT,coordinador TEXT,unidad TEXT,estado TEXT,prioridad TEXT,requiere_evidencia INTEGER,archivo_evidencia TEXT,fecha_entrega TEXT,clave_unica TEXT)''')
    c.executemany('INSERT INTO calendario_entregables VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',[(1,1,'Pendiente','2099-09-20','x','Dora','Ana','UDS A','pendiente','Media',0,None,None,'a'),(2,1,'Vencido','2020-09-01','x','Dora','Ana','UDS B','pendiente','Alta',0,None,None,'b'),(3,1,'Otro equipo','2020-09-01','x','Diego','Bea','UDS C','pendiente','Alta',0,None,None,'c'),(4,2,'Otro tenant','2020-09-01','x','Dora','Ana','UDS Z','pendiente','Alta',0,None,None,'d')]);c.commit();c.close()
    o=LiamOrchestrator(db);data=o.run('prepare_communication_draft',args={'audience':'pending_deliverables'},tenant_id=1,user={'id':1,'rol':'COORDINADOR','nombre_completo':'Ana'}).result
    assert data['recipient_count']==1 and data['pending_count']==2
    assert data['recipients']==[{'responsible':'Dora','units':['UDS A','UDS B'],'pending':2,'overdue':1}]
    assert data['draft_only'] is True and data['send_enabled'] is False and data['requires_approval_before_send'] is True
    assert data['scope']['cross_foundation'] is False and data['read_only'] is True
    assert 'Diego' not in str(data) and 'UDS Z' not in str(data)
    try:o.run('prepare_communication_draft',args={'audience':'pending_deliverables'},tenant_id=1,user={'id':2,'rol':'DOCENTE','nombre_completo':'Dora'})
    except PermissionError:pass
    else:raise AssertionError('Un docente preparó una comunicación masiva.')

print('LIAM_COMMUNICATION_DRAFT_V7_PASS')
