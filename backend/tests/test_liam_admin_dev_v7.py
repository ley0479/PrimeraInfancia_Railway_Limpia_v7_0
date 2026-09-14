"""Solicitudes ADMIN/DEV: borrador sanitizado, rol, usuario y tenant."""
from pathlib import Path
import sys,tempfile
BACKEND=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BACKEND))
from modules.dbapi_compat import sqlite3
from modules.asistente_capacitacion.schema import SCHEMA_SQL
from modules.asistente_capacitacion.tool_registry import execute

with tempfile.TemporaryDirectory() as tmp:
    database=str(Path(tmp)/'dev.db');conn=sqlite3.connect(database);conn.executescript(SCHEMA_SQL);conn.commit();conn.close()
    created=execute('prepare_dev_change_request',args={'module':'base-maestra','objective':'Agregar filtro por docente token=abc123456789'},database_path=database,tenant_id=1,user={'id':10,'rol':'SUPERADMIN'})
    assert created['request']['status']=='DRAFT' and created['code_modified'] is False and created['deployment_started'] is False
    assert 'abc123456789' not in created['request']['objective']
    execute('prepare_dev_change_request',args={'module':'dashboard','objective':'Agregar indicador institucional seguro'},database_path=database,tenant_id=1,user={'id':11,'rol':'SUPERADMIN'})
    execute('prepare_dev_change_request',args={'module':'dashboard','objective':'Cambio de otra fundación segura'},database_path=database,tenant_id=2,user={'id':10,'rol':'SUPERADMIN'})
    listed=execute('list_dev_change_requests',args={},database_path=database,tenant_id=1,user={'id':10,'rol':'SUPERADMIN'})
    assert listed['total']==1 and listed['requests'][0]['request_id']==created['request']['request_id']
    try:execute('prepare_dev_change_request',args={'module':'dashboard','objective':'Intento sin permiso suficiente'},database_path=database,tenant_id=1,user={'id':12,'rol':'GERENTE'})
    except PermissionError:pass
    else:raise AssertionError('Un rol no autorizado registró un cambio técnico.')
print('LIAM_ADMIN_DEV_V7_PASS')
