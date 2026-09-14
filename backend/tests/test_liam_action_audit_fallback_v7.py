"""La auditoría auxiliar nunca cambia el resultado de una acción funcional."""
from pathlib import Path
import os,sys,tempfile
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from flask import Flask,g
from modules.asistente_capacitacion.routes import register_asistente_capacitacion
from modules.dbapi_compat import sqlite3

os.environ['ENABLE_LIA_ASSISTANT']='true';os.environ['ENABLE_LIAM_ASSISTANT']='true';os.environ['LIAM_ACTIONS_ENABLED']='true'
with tempfile.TemporaryDirectory() as tmp:
    db=str(Path(tmp)/'fallback.db');app=Flask(__name__)
    @app.before_request
    def identity():g.current_user={'id':10,'fundacion_id':1,'rol':'SUPERADMIN','username':'admin'}
    register_asistente_capacitacion(app,db)
    conn=sqlite3.connect(db);conn.execute('DROP TABLE liam_action_audit');conn.commit();conn.close()
    with app.test_client() as client:
        event=client.post('/api/asistente-capacitacion/actions/client-event',json={'action':'open_module','status':'completed','request_id':'trace-fallback','module':'dashboard'})
        assert event.status_code==200 and event.get_json()['ok'] is True
        proposal=client.post('/api/asistente-capacitacion/chat',json={'message':'Genera la Relación del Mes de septiembre de 2026','module':'formatos'})
        assert proposal.status_code==200 and proposal.get_json()['confirmation_required'] is True

print('LIAM_ACTION_AUDIT_FALLBACK_V7_PASS')
