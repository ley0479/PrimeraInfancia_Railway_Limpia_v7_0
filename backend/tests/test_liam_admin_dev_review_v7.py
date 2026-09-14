"""Revisión ADMIN/DEV verificable, de solo lectura y aislada."""
from pathlib import Path
import sys,tempfile
BACKEND=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BACKEND))
from modules.dbapi_compat import sqlite3
from modules.asistente_capacitacion.schema import SCHEMA_SQL
from modules.asistente_capacitacion.tool_registry import execute

routes_source=(BACKEND/'modules'/'asistente_capacitacion'/'routes.py').read_text(encoding='utf-8')
assert "Revisión técnica {item.get('request_id')}" in routes_source
assert "elif proposal['server_tool']=='get_dev_change_review'" in routes_source
assert "'name':'get_dev_change_review'" in routes_source

with tempfile.TemporaryDirectory() as tmp:
    database=str(Path(tmp)/'review.db');conn=sqlite3.connect(database);conn.executescript(SCHEMA_SQL);conn.commit();conn.close()
    created=execute('prepare_dev_change_request',args={'module':'base-maestra','objective':'Agregar filtro verificable por docente'},database_path=database,tenant_id=1,user={'id':10,'rol':'SUPERADMIN'})
    request_id=created['request']['request_id']
    review=execute('get_dev_change_review',args={'request_id':request_id},database_path=database,tenant_id=1,user={'id':10,'rol':'SUPERADMIN'})
    assert review['request']['request_id']==request_id and review['module_review']['module']=='base-maestra'
    assert review['facts_verified_from_registry'] is True and review['files_inferred'] is False
    assert review['read_only'] is True and review['code_modified'] is False and review['deployment_started'] is False
    assert [item['gate'] for item in review['gates']]==['Arquitectura','Riesgo','Pruebas','Diff','Aprobación','Despliegue']
    for tenant,user_id in ((2,10),(1,11)):
        try:execute('get_dev_change_review',args={'request_id':request_id},database_path=database,tenant_id=tenant,user={'id':user_id,'rol':'SUPERADMIN'})
        except LookupError:pass
        else:raise AssertionError('La revisión cruzó el límite de usuario o fundación.')
    try:execute('get_dev_change_review',args={'request_id':request_id},database_path=database,tenant_id=1,user={'id':10,'rol':'GERENTE'})
    except PermissionError:pass
    else:raise AssertionError('Un rol no autorizado consultó la revisión técnica.')
print('LIAM_ADMIN_DEV_REVIEW_V7_PASS')
