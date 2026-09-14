"""Redacción recursiva previa a auditoría y persistencia."""
from pathlib import Path
import os,sys,tempfile
BACKEND=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BACKEND))
from modules.asistente_capacitacion.privacy_service import redact_data
from modules.asistente_capacitacion.routes import register_asistente_capacitacion
from modules.dbapi_compat import sqlite3
from flask import Flask,g

payload={'token':'abc123456789','nested':{'authorization':'Bearer private-value','message':'correo persona@example.com password=hidden-value'},'items':['documento 1234567890']}
safe=redact_data(payload);serialized=str(safe)
for secret in ('abc123456789','private-value','persona@example.com','hidden-value','1234567890'):assert secret not in serialized
assert safe['token']=='[SECRETO REDACTADO]' and safe['nested']['authorization']=='[SECRETO REDACTADO]'
routes=(BACKEND/'modules'/'asistente_capacitacion'/'routes.py').read_text(encoding='utf-8')
assert 'json.dumps(redact_data(metadata or {})' in routes
assert "redact(str(module or ''))[:80]" in routes

previous=os.environ.get('ENABLE_LIAM_ASSISTANT');os.environ['ENABLE_LIAM_ASSISTANT']='true'
try:
    with tempfile.TemporaryDirectory() as tmp:
        database=str(Path(tmp)/'audit.db');app=Flask(__name__)
        @app.before_request
        def identity():g.current_user={'id':10,'fundacion_id':1,'rol':'SUPERADMIN','username':'admin'}
        register_asistente_capacitacion(app,database)
        response=app.test_client().post('/api/asistente-capacitacion/tools/get_structured_error',json={'code':'PARTICIPANTES_REQUERIDOS'},headers={'X-Liam-Module':'token=audit-secret-123'})
        assert response.status_code==200
        conn=sqlite3.connect(database);row=conn.execute('SELECT modulo,metadata_redacted FROM lia_audit_events ORDER BY id DESC LIMIT 1').fetchone();conn.close()
        persisted=' '.join(str(item or '') for item in row)
        assert 'audit-secret-123' not in persisted and '[SECRETO REDACTADO]' in persisted
finally:
    if previous is None:os.environ.pop('ENABLE_LIAM_ASSISTANT',None)
    else:os.environ['ENABLE_LIAM_ASSISTANT']=previous
print('LIAM_AUDIT_PRIVACY_V7_PASS')
