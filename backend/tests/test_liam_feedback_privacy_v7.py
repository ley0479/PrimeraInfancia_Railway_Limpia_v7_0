"""Feedback persiste observaciones redactadas y aisladas."""
from pathlib import Path
import os,sys,tempfile
BACKEND=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BACKEND))
from flask import Flask,g
from modules.asistente_capacitacion.routes import register_asistente_capacitacion
from modules.dbapi_compat import sqlite3

old=os.environ.get('ENABLE_LIAM_ASSISTANT');os.environ['ENABLE_LIAM_ASSISTANT']='true'
try:
    with tempfile.TemporaryDirectory() as tmp:
        database=str(Path(tmp)/'feedback.db');app=Flask(__name__)
        @app.before_request
        def identity():g.current_user={'id':10,'fundacion_id':1,'rol':'DOCENTE','username':'docente'}
        register_asistente_capacitacion(app,database)
        response=app.test_client().post('/api/asistente-capacitacion/feedback',json={'rating':-1,'reason':'Falló para persona@example.com documento 1234567890 token=private-feedback-token','module':'dashboard','request_id':'req-token=hidden-request-token'})
        assert response.status_code==201
        conn=sqlite3.connect(database);row=conn.execute('SELECT reason,module,request_id FROM lia_feedback').fetchone();conn.close();stored=' '.join(row)
        for secret in ('persona@example.com','1234567890','private-feedback-token','hidden-request-token'):assert secret not in stored
finally:
    if old is None:os.environ.pop('ENABLE_LIAM_ASSISTANT',None)
    else:os.environ['ENABLE_LIAM_ASSISTANT']=old
print('LIAM_FEEDBACK_PRIVACY_V7_PASS')
