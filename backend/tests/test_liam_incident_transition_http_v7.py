"""Flujo HTTP completo: orden, propuesta, confirmación y auditoría."""
from pathlib import Path
import os,sys,tempfile
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from flask import Flask,g
from modules.asistente_capacitacion.routes import register_asistente_capacitacion
from modules.dbapi_compat import sqlite3

os.environ['ENABLE_LIA_ASSISTANT']='true';os.environ['ENABLE_LIAM_ASSISTANT']='true';os.environ['LIAM_ACTIONS_ENABLED']='true'
with tempfile.TemporaryDirectory() as tmp:
    db=str(Path(tmp)/'transition-http.db');app=Flask(__name__)
    @app.before_request
    def identity():g.current_user={'id':99,'fundacion_id':1,'rol':'GERENTE','username':'gerencia'}
    register_asistente_capacitacion(app,db);conn=sqlite3.connect(db)
    conn.execute('''INSERT INTO lia_error_incidents(incident_id,fundacion_id,usuario_id,module,action,http_status,error_code,error_type,technical_message_redacted,cause,solution,severity,safe_retry,auto_correctable,status,request_id,context_redacted,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',('INC-20260914-170000-AAAAAA',1,10,'rpp','generar',500,'RPP_X','error_backend','x','Causa','Pendiente','high',0,0,'IN_PROGRESS','trace','{}','2026-09-14','2026-09-14'));conn.commit();conn.close()
    client=app.test_client();question='Liam marca el incidente INC-20260914-170000-AAAAAA como resuelto. Solución: validación administrativa completada'
    proposed=client.post('/api/asistente-capacitacion/chat',json={'message':question,'module':'administracion'});assert proposed.status_code==200,proposed.get_data(as_text=True)
    body=proposed.get_json();assert body['confirmation_required'] is True and body['action_proposal']['id']=='transition_incident'
    proposal_id=body['action_proposal']['proposal_id'];confirmed=client.post(f'/api/asistente-capacitacion/actions/confirm/{proposal_id}');assert confirmed.status_code==200,confirmed.get_data(as_text=True)
    conn=sqlite3.connect(db);incident=conn.execute("SELECT status FROM lia_error_incidents WHERE incident_id='INC-20260914-170000-AAAAAA'").fetchone();audit=conn.execute('SELECT result,before_state,after_state,resource_id FROM liam_action_audit WHERE trace_id=?',(proposal_id,)).fetchone();conn.close()
    assert incident[0]=='RESOLVED' and audit[0]=='COMPLETED'
    assert 'IN_PROGRESS' in audit[1] and 'RESOLVED' in audit[2]
    assert audit[3]=='INC-20260914-170000-AAAAAA'

print('LIAM_INCIDENT_TRANSITION_HTTP_V7_PASS')
