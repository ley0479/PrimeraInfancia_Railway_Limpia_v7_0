"""Centro de incidencias: usuario propio, administración tenant y sanitización."""
from pathlib import Path
import sys,tempfile
BACKEND=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BACKEND))
from modules.asistente_capacitacion.orchestrator import LiamOrchestrator
from modules.asistente_capacitacion.schema import SCHEMA_SQL
from modules.dbapi_compat import sqlite3

with tempfile.TemporaryDirectory() as tmp:
    db=str(Path(tmp)/'incidents.db');c=sqlite3.connect(db);c.executescript(SCHEMA_SQL)
    sql='''INSERT INTO lia_error_incidents(incident_id,fundacion_id,usuario_id,module,action,http_status,error_code,error_type,technical_message_redacted,cause,solution,severity,safe_retry,auto_correctable,status,request_id,context_redacted,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'''
    rows=[('INC-20260914-120000-AAAAAA',1,10,'rpp','generar',500,'RPP_1','error_backend','password=oculta','Faltan datos','Revisar','high',0,0,'OPEN','r1','{}','2026-09-14','2026-09-14'),('INC-20260914-120001-BBBBBB',1,11,'ram','generar',422,'RAM_1','error_datos','token=oculto','Dato inválido','Corregir','medium',1,0,'RESOLVED','r2','{}','2026-09-14','2026-09-14'),('INC-20260914-120002-CCCCCC',2,10,'rpp','generar',500,'RPP_2','error_backend','secreto','Otro tenant','Revisar','high',0,0,'OPEN','r3','{}','2026-09-14','2026-09-14')]
    c.executemany(sql,rows);c.commit();c.close();o=LiamOrchestrator(db)
    own=o.run('get_incident_center',args={},tenant_id=1,user={'id':10,'rol':'DOCENTE'}).result
    assert own['summary']['total']==1 and own['role_scope']=='own_user'
    assert own['incidents'][0]['incident_id'].endswith('AAAAAA')
    assert 'password' not in str(own).lower() and 'technical_message' not in str(own)
    manager=o.run('get_incident_center',args={},tenant_id=1,user={'id':20,'rol':'GERENTE'}).result
    assert manager['summary']['total']==2 and manager['role_scope']=='foundation'
    assert 'CCCCCC' not in str(manager)
    filtered=o.run('get_incident_center',args={'status':'OPEN'},tenant_id=1,user={'id':20,'rol':'GERENTE'}).result
    assert filtered['summary']['total']==1 and filtered['summary']['open']==1

print('LIAM_INCIDENT_CENTER_V7_PASS')
