"""Contrato HTTP firmado para resultados ADMIN/DEV de sandbox externo."""
from pathlib import Path
import hashlib
import hmac
import json
import os
import sys
import tempfile

from flask import Flask, g, request

BACKEND=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BACKEND))
from modules.asistente_capacitacion.routes import register_asistente_capacitacion
from modules.asistente_capacitacion.tool_registry import execute
from modules.dbapi_compat import sqlite3


def signed(raw, key):
    return 'sha256='+hmac.new(key.encode(),raw,hashlib.sha256).hexdigest()


with tempfile.TemporaryDirectory() as tmp:
    previous={name:os.environ.get(name) for name in ('ENABLE_LIAM_ASSISTANT','LIAM_DEV_ENABLED','LIAM_DEV_SANDBOX_SIGNING_KEY')}
    os.environ.update(ENABLE_LIAM_ASSISTANT='true',LIAM_DEV_ENABLED='true',LIAM_DEV_SANDBOX_SIGNING_KEY='test-runner-key-not-production')
    try:
        db=str(Path(tmp)/'sandbox-result.db');app=Flask(__name__)
        identities={
            'owner':{'id':10,'fundacion_id':1,'rol':'SUPERADMIN','username':'owner'},
            'other-user':{'id':11,'fundacion_id':1,'rol':'SUPERADMIN','username':'other'},
            'other-tenant':{'id':10,'fundacion_id':2,'rol':'SUPERADMIN','username':'tenant2'},
            'manager':{'id':10,'fundacion_id':1,'rol':'GERENTE','username':'manager'},
        }
        @app.before_request
        def identity():g.current_user=identities[request.headers.get('X-Test-Identity','owner')]
        register_asistente_capacitacion(app,db);client=app.test_client()
        created=execute('prepare_dev_change_request',args={'module':'base-maestra','objective':'Agregar filtro seguro por docente'},database_path=db,tenant_id=1,user={'id':10,'rol':'SUPERADMIN'})
        request_id=created['request']['request_id'];plan=execute('prepare_dev_sandbox_plan',args={'request_id':request_id},database_path=db,tenant_id=1,user={'id':10,'rol':'SUPERADMIN'})['artifact']
        changed=plan['architecture']['files'][0]
        diff=f"diff --git a/{changed} b/{changed}\n--- a/{changed}\n+++ b/{changed}\n@@ -1 +1 @@\n-old\n+new\n"
        tests=[{'test':name,'status':'PASS','duration_ms':12} for name in [*plan['tests'],plan['generated_test_path']]]
        payload={'plan_sha256':plan['sha256'],'diff':diff,'git_diff_check':'PASS','tests':tests,'runner':'ci-sandbox-v1'}
        raw=json.dumps(payload,separators=(',',':')).encode();headers={'Content-Type':'application/json','X-Liam-Sandbox-Signature':signed(raw,os.environ['LIAM_DEV_SANDBOX_SIGNING_KEY'])}
        accepted=client.post(f'/api/asistente-capacitacion/dev/sandbox-results/{request_id}',data=raw,headers=headers)
        assert accepted.status_code==201,accepted.get_data(as_text=True)
        body=accepted.get_json();assert body['status']=='PASSED' and body['deployment_started'] is False and body['changed_paths']==[changed]
        review=execute('get_dev_change_review',args={'request_id':request_id},database_path=db,tenant_id=1,user={'id':10,'rol':'SUPERADMIN'})
        gates={item['gate']:item['status'] for item in review['gates']};assert gates['Pruebas']=='READY' and gates['Diff']=='READY' and gates['Aprobación']=='PENDING' and gates['Despliegue']=='DISABLED'
        assert review['code_modified'] is False and review['sandbox_diff_registered'] is True and review['sandbox_result']['runner']=='ci-sandbox-v1'
        conn=sqlite3.connect(db);stored=conn.execute("SELECT status,content_sha256 FROM lia_dev_change_artifacts WHERE request_id=? AND artifact_type='SANDBOX_RESULT'",(request_id,)).fetchone();state=conn.execute('SELECT status FROM lia_dev_change_requests WHERE request_id=?',(request_id,)).fetchone()[0];audit=conn.execute("SELECT COUNT(*) FROM lia_audit_events WHERE event_type='DEV_SANDBOX_RESULT_ACCEPTED'").fetchone()[0];conn.close()
        assert stored[0]=='PASSED' and len(stored[1])==64 and state=='TESTED' and audit==1

        assert client.post(f'/api/asistente-capacitacion/dev/sandbox-results/{request_id}',data=raw,headers={**headers,'X-Liam-Sandbox-Signature':'sha256='+'0'*64}).status_code==403
        for identity_name in ('other-user','other-tenant','manager'):
            response=client.post(f'/api/asistente-capacitacion/dev/sandbox-results/{request_id}',data=raw,headers={**headers,'X-Test-Identity':identity_name})
            assert response.status_code in {403,404},(identity_name,response.status_code,response.get_data(as_text=True))
        stale={**payload,'plan_sha256':'a'*64};stale_raw=json.dumps(stale,separators=(',',':')).encode()
        assert client.post(f'/api/asistente-capacitacion/dev/sandbox-results/{request_id}',data=stale_raw,headers={'Content-Type':'application/json','X-Liam-Sandbox-Signature':signed(stale_raw,os.environ['LIAM_DEV_SANDBOX_SIGNING_KEY'])}).status_code==409
        forbidden={**payload,'diff':'diff --git a/.env b/.env\n--- a/.env\n+++ b/.env\n@@ -1 +1 @@\n-a\n+b\n'};forbidden_raw=json.dumps(forbidden,separators=(',',':')).encode()
        assert client.post(f'/api/asistente-capacitacion/dev/sandbox-results/{request_id}',data=forbidden_raw,headers={'Content-Type':'application/json','X-Liam-Sandbox-Signature':signed(forbidden_raw,os.environ['LIAM_DEV_SANDBOX_SIGNING_KEY'])}).status_code==422
        incomplete={**payload,'tests':tests[:-1]};incomplete_raw=json.dumps(incomplete,separators=(',',':')).encode()
        assert client.post(f'/api/asistente-capacitacion/dev/sandbox-results/{request_id}',data=incomplete_raw,headers={'Content-Type':'application/json','X-Liam-Sandbox-Signature':signed(incomplete_raw,os.environ['LIAM_DEV_SANDBOX_SIGNING_KEY'])}).status_code==422
    finally:
        for name,value in previous.items():
            if value is None:os.environ.pop(name,None)
            else:os.environ[name]=value

print('LIAM_DEV_SANDBOX_RESULT_HTTP_V7_PASS')
