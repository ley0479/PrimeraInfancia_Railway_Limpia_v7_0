"""Rutas administrativas respetan bandera y rol además del tenant."""
from pathlib import Path
import os,sys,tempfile
BACKEND=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BACKEND))
from flask import Flask,g,request
from modules.asistente_capacitacion.routes import register_asistente_capacitacion
from modules.dbapi_compat import sqlite3

saved={name:os.environ.get(name) for name in ('ENABLE_LIAM_ASSISTANT','LIAM_ADMIN_ENABLED')}
os.environ.update({'ENABLE_LIAM_ASSISTANT':'true','LIAM_ADMIN_ENABLED':'true'})
try:
    with tempfile.TemporaryDirectory() as tmp:
        app=Flask(__name__)
        @app.before_request
        def identity():
            role=request.headers.get('X-Test-Role','SUPERADMIN');g.current_user={'id':10,'fundacion_id':1,'rol':role,'username':'test'}
        database=str(Path(tmp)/'admin.db');register_asistente_capacitacion(app,database)
        conn=sqlite3.connect(database);conn.execute('CREATE TABLE usuarios_app(id INTEGER PRIMARY KEY,fundacion_id INTEGER,username TEXT)');conn.commit();conn.close();client=app.test_client()
        assert client.get('/api/asistente-capacitacion/notification-providers').status_code==200
        assert client.get('/api/asistente-capacitacion/notification-providers',headers={'X-Test-Role':'DOCENTE'}).status_code==403
        assert client.get('/api/asistente-capacitacion/chat/history/admin').status_code==200
        visual=client.get('/api/asistente-capacitacion/elian/visual-config',headers={'X-Test-Role':'DOCENTE'});assert visual.status_code==200 and visual.get_json()['editable'] is False
finally:
    for name,value in saved.items():
        if value is None:os.environ.pop(name,None)
        else:os.environ[name]=value
print('LIAM_ADMIN_ENDPOINT_GATE_V7_PASS')
