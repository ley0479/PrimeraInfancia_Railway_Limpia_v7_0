"""Aprobación ADMIN/DEV reautenticada, tenant-scoped y sin despliegue."""
from pathlib import Path
import hashlib,hmac,json,os,sys,tempfile
from flask import Flask,g,request
from werkzeug.security import generate_password_hash

BACKEND=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BACKEND))
from modules.asistente_capacitacion.routes import register_asistente_capacitacion
from modules.asistente_capacitacion.tool_registry import execute
from modules.dbapi_compat import sqlite3

with tempfile.TemporaryDirectory() as tmp:
    names=('ENABLE_LIAM_ASSISTANT','LIAM_DEV_ENABLED','LIAM_DEV_SANDBOX_SIGNING_KEY');previous={x:os.environ.get(x) for x in names};os.environ.update(ENABLE_LIAM_ASSISTANT='true',LIAM_DEV_ENABLED='true',LIAM_DEV_SANDBOX_SIGNING_KEY='approval-test-key')
    try:
        db=str(Path(tmp)/'approval.db');app=Flask(__name__);identities={'owner':{'id':10,'fundacion_id':1,'rol':'SUPERADMIN'},'other':{'id':11,'fundacion_id':1,'rol':'SUPERADMIN'},'tenant2':{'id':10,'fundacion_id':2,'rol':'SUPERADMIN'},'manager':{'id':10,'fundacion_id':1,'rol':'GERENTE'}}
        @app.before_request
        def identity():g.current_user=identities[request.headers.get('X-Test-Identity','owner')]
        register_asistente_capacitacion(app,db);conn=sqlite3.connect(db);conn.execute('CREATE TABLE usuarios_app(id INTEGER,fundacion_id INTEGER,activo INTEGER,password_hash TEXT)');conn.executemany('INSERT INTO usuarios_app VALUES(?,?,?,?)',[(10,1,1,generate_password_hash('Clave-Segura-2026!')),(11,1,1,generate_password_hash('Otra-Clave-2026!')),(10,2,1,generate_password_hash('Tenant-Clave-2026!'))]);conn.commit();conn.close();client=app.test_client()
        made=execute('prepare_dev_change_request',args={'module':'base-maestra','objective':'Agregar validación segura de docente'},database_path=db,tenant_id=1,user={'id':10,'rol':'SUPERADMIN'});request_id=made['request']['request_id'];plan=execute('prepare_dev_sandbox_plan',args={'request_id':request_id},database_path=db,tenant_id=1,user={'id':10,'rol':'SUPERADMIN'})['artifact'];changed=plan['architecture']['files'][0]
        payload={'plan_sha256':plan['sha256'],'base_commit':'a'*40,'diff':f'diff --git a/{changed} b/{changed}\n--- a/{changed}\n+++ b/{changed}\n@@ -1 +1 @@\n-a\n+b\n','git_diff_check':'PASS','tests':[{'test':name,'status':'PASS','duration_ms':5} for name in [*plan['tests'],plan['generated_test_path']]],'runner':'approval-ci'};raw=json.dumps(payload,separators=(',',':')).encode();signature='sha256='+hmac.new(b'approval-test-key',raw,hashlib.sha256).hexdigest()
        received=client.post(f'/api/asistente-capacitacion/dev/sandbox-results/{request_id}',data=raw,headers={'Content-Type':'application/json','X-Liam-Sandbox-Signature':signature});assert received.status_code==201,received.get_data(as_text=True);result_sha=received.get_json()['artifact_sha256']
        base={'confirmar':'APROBAR CAMBIO','result_sha256':result_sha}
        assert client.post(f'/api/asistente-capacitacion/dev/change-requests/{request_id}/approve',json={**base,'password_actual':'mal'}).status_code==403
        for identity_name in ('other','tenant2','manager'):
            response=client.post(f'/api/asistente-capacitacion/dev/change-requests/{request_id}/approve',json={**base,'password_actual':'Otra-Clave-2026!'},headers={'X-Test-Identity':identity_name});assert response.status_code in {403,404}
        stale=client.post(f'/api/asistente-capacitacion/dev/change-requests/{request_id}/approve',json={'confirmar':'APROBAR CAMBIO','password_actual':'Clave-Segura-2026!','result_sha256':'b'*64});assert stale.status_code==409
        approved=client.post(f'/api/asistente-capacitacion/dev/change-requests/{request_id}/approve',json={**base,'password_actual':'Clave-Segura-2026!'});assert approved.status_code==200,approved.get_data(as_text=True);body=approved.get_json();assert body['status']=='APPROVED' and body['code_applied'] is False and body['deployment_started'] is False and body['rollback_plan']['base_commit']=='a'*40
        review=execute('get_dev_change_review',args={'request_id':request_id},database_path=db,tenant_id=1,user={'id':10,'rol':'SUPERADMIN'});gates={x['gate']:x['status'] for x in review['gates']};assert gates['Aprobación']=='READY' and gates['Despliegue']=='DISABLED';assert review['rollback_plan']['automatic_execution'] is False
        conn=sqlite3.connect(db);types=dict(conn.execute("SELECT artifact_type,status FROM lia_dev_change_artifacts WHERE request_id=? AND artifact_type IN ('APPROVAL','ROLLBACK_PLAN')",(request_id,)).fetchall());state=conn.execute('SELECT status FROM lia_dev_change_requests WHERE request_id=?',(request_id,)).fetchone()[0];audit=conn.execute("SELECT COUNT(*) FROM lia_audit_events WHERE event_type='DEV_CHANGE_APPROVED'").fetchone()[0];conn.close();assert types=={'APPROVAL':'APPROVED','ROLLBACK_PLAN':'READY'} and state=='APPROVED' and audit==1
        assert client.post(f'/api/asistente-capacitacion/dev/change-requests/{request_id}/approve',json={**base,'password_actual':'Clave-Segura-2026!'}).status_code==409
    finally:
        for name,value in previous.items():
            if value is None:os.environ.pop(name,None)
            else:os.environ[name]=value

print('LIAM_DEV_CHANGE_APPROVAL_HTTP_V7_PASS')
