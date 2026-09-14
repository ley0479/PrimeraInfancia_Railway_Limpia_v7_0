"""Contrato HTTP del ciclo propuesta -> evento del ejecutor cliente."""
from pathlib import Path
import os,sys,tempfile
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from flask import Flask,g
from modules.asistente_capacitacion.routes import register_asistente_capacitacion
from modules.dbapi_compat import sqlite3

os.environ['ENABLE_LIA_ASSISTANT']='true';os.environ['ENABLE_LIAM_ASSISTANT']='true';os.environ['LIAM_ACTIONS_ENABLED']='true'
with tempfile.TemporaryDirectory() as tmp:
    db=str(Path(tmp)/'audit-http.db');app=Flask(__name__)
    @app.before_request
    def identity():g.current_user={'id':10,'fundacion_id':1,'rol':'SUPERADMIN','username':'admin'}
    register_asistente_capacitacion(app,db);client=app.test_client()
    response=client.post('/api/asistente-capacitacion/chat',json={'message':'Genera la Relación del Mes de septiembre de 2026','module':'formatos'})
    assert response.status_code==200,response.get_data(as_text=True)
    body=response.get_json();assert body['confirmation_required'] is True
    request_id=body['request_id'];action=body['action_proposal']['id']
    conn=sqlite3.connect(db);row=conn.execute('SELECT result FROM liam_action_audit WHERE trace_id=? AND requested_action=?',(request_id,action)).fetchone();conn.close()
    assert row and row[0]=='AWAITING_CONFIRMATION'
    event=client.post('/api/asistente-capacitacion/actions/client-event',json={'action':action,'status':'completed','request_id':request_id,'module':'formatos'})
    assert event.status_code==200
    conn=sqlite3.connect(db);row=conn.execute('SELECT result FROM liam_action_audit WHERE trace_id=? AND requested_action=?',(request_id,action)).fetchone();conn.close()
    assert row[0]=='COMPLETED'
    history=client.get('/api/asistente-capacitacion/actions/history?limit=20')
    assert history.status_code==200 and history.get_json()['total']==1
    assert history.get_json()['scope']['foundation_id']==1

print('LIAM_ACTION_AUDIT_HTTP_V7_PASS')
