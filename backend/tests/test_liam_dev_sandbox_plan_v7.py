"""Plan ADMIN/DEV verificable, cerrado y aislado; no ejecuta código."""
from pathlib import Path
import hashlib,json,sys,tempfile
BACKEND=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BACKEND))
from modules.asistente_capacitacion.schema import SCHEMA_SQL
from modules.asistente_capacitacion.tool_registry import execute
from modules.dbapi_compat import sqlite3

with tempfile.TemporaryDirectory() as tmp:
    db=str(Path(tmp)/'dev-plan.db');conn=sqlite3.connect(db);conn.executescript(SCHEMA_SQL);conn.close()
    created=execute('prepare_dev_change_request',args={'module':'base-maestra','objective':'Agregar filtro verificable por docente'},database_path=db,tenant_id=1,user={'id':10,'rol':'SUPERADMIN'})
    request_id=created['request']['request_id'];plan=execute('prepare_dev_sandbox_plan',args={'request_id':request_id},database_path=db,tenant_id=1,user={'id':10,'rol':'SUPERADMIN'})
    artifact=plan['artifact'];assert artifact['status']=='READY' and plan['requires_external_isolated_runner'] is True
    assert plan['code_modified'] is False and plan['tests_executed'] is False and plan['deployment_started'] is False
    assert artifact['architecture']['files'] and artifact['tests'] and '.env' in artifact['forbidden_paths']
    conn=sqlite3.connect(db);conn.row_factory=sqlite3.Row;row=dict(conn.execute('SELECT * FROM lia_dev_change_artifacts').fetchone());status=conn.execute('SELECT status FROM lia_dev_change_requests WHERE request_id=?',(request_id,)).fetchone()[0];conn.close()
    assert status=='PLANNED' and hashlib.sha256(row['content_json'].encode()).hexdigest()==row['content_sha256']==artifact['sha256']
    regenerated=execute('prepare_dev_sandbox_plan',args={'request_id':request_id},database_path=db,tenant_id=1,user={'id':10,'rol':'SUPERADMIN'})
    conn=sqlite3.connect(db);stored=conn.execute("SELECT artifact_id,COUNT(*) FROM lia_dev_change_artifacts WHERE request_id=? AND artifact_type='SANDBOX_PLAN'",(request_id,)).fetchone();conn.close()
    assert stored==(regenerated['artifact']['artifact_id'],1)
    review=execute('get_dev_change_review',args={'request_id':request_id},database_path=db,tenant_id=1,user={'id':10,'rol':'SUPERADMIN'})
    assert review['sandbox_plan']['content_sha256']==artifact['sha256'] and review['gates'][0]['status']=='READY' and review['gates'][2]['status']=='PLANNED'
    for tenant,user in ((2,{'id':10,'rol':'SUPERADMIN'}),(1,{'id':11,'rol':'SUPERADMIN'}),(1,{'id':10,'rol':'GERENTE'})):
        try:execute('prepare_dev_sandbox_plan',args={'request_id':request_id},database_path=db,tenant_id=tenant,user=user)
        except (LookupError,PermissionError):pass
        else:raise AssertionError('El plan cruzó tenant, usuario o rol.')

print('LIAM_DEV_SANDBOX_PLAN_V7_PASS')
