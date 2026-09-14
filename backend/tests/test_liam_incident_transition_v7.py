"""Transiciones confirmables de incidencias con tenant, rol y concurrencia."""
from pathlib import Path
import sys,tempfile
BACKEND=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BACKEND))
from modules.asistente_capacitacion.error_center import create_transition_proposal,confirm_transition
from modules.asistente_capacitacion.schema import SCHEMA_SQL
from modules.dbapi_compat import sqlite3

with tempfile.TemporaryDirectory() as tmp:
    db=str(Path(tmp)/'transition.db');conn=sqlite3.connect(db);conn.executescript(SCHEMA_SQL)
    sql='''INSERT INTO lia_error_incidents(incident_id,fundacion_id,usuario_id,module,action,http_status,error_code,error_type,technical_message_redacted,cause,solution,severity,safe_retry,auto_correctable,status,request_id,context_redacted,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'''
    incident=('INC-20260914-160000-AAAAAA',1,10,'rpp','generar',500,'RPP_X','error_backend','x','Causa','Pendiente','high',0,0,'IN_PROGRESS','trace','{}','2026-09-14','2026-09-14')
    other=('INC-20260914-160001-BBBBBB',2,20,'ram','generar',500,'RAM_X','error_backend','x','Causa','Pendiente','high',0,0,'IN_PROGRESS','trace','{}','2026-09-14','2026-09-14')
    conn.executemany(sql,[incident,other]);conn.commit();conn.close();ctx={'fundacion_id':1,'usuario_id':99,'rol':'GERENTE'}
    proposal=create_transition_proposal(db,ctx,incident[0],'RESOLVED','Se validaron los datos obligatorios.')
    assert proposal['confirmation_required'] is True and proposal['server_confirmation'] is True
    conn=sqlite3.connect(db);assert conn.execute('SELECT status FROM lia_error_incidents WHERE incident_id=?',(incident[0],)).fetchone()[0]=='IN_PROGRESS';conn.close()
    try:confirm_transition(db,proposal['proposal_id'],{'fundacion_id':1,'usuario_id':98,'rol':'GERENTE'})
    except PermissionError:pass
    else:raise AssertionError('Otra sesión confirmó la propuesta.')
    result=confirm_transition(db,proposal['proposal_id'],ctx);assert result['incident']['status']=='RESOLVED'
    conn=sqlite3.connect(db);row=conn.execute('SELECT status,solution FROM lia_error_incidents WHERE incident_id=?',(incident[0],)).fetchone();other_status=conn.execute('SELECT status FROM lia_error_incidents WHERE incident_id=?',(other[0],)).fetchone()[0];conn.close()
    assert row==('RESOLVED','Se validaron los datos obligatorios.') and other_status=='IN_PROGRESS'
    try:confirm_transition(db,proposal['proposal_id'],ctx)
    except ValueError:pass
    else:raise AssertionError('La propuesta se reutilizó.')
    try:create_transition_proposal(db,ctx,other[0],'RESOLVED','No debe cambiar.')
    except LookupError:pass
    else:raise AssertionError('Se preparó una transición para otro tenant.')

print('LIAM_INCIDENT_TRANSITION_V7_PASS')
