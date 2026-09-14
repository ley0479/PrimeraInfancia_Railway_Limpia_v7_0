"""Analítica funcional aislada por fundación y sin eliminaciones."""
from pathlib import Path
import sys,tempfile
BACKEND=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BACKEND))
from modules.dbapi_compat import sqlite3
from modules.asistente_capacitacion.schema import SCHEMA_SQL
from modules.asistente_capacitacion.tool_registry import execute

with tempfile.TemporaryDirectory() as tmp:
    database=str(Path(tmp)/'usage.db');conn=sqlite3.connect(database);conn.executescript(SCHEMA_SQL)
    for index in range(12):conn.execute("INSERT INTO lia_audit_events(fundacion_id,usuario_id,event_type,modulo,success,created_at) VALUES(1,10,'QUESTION_COMPLETED','base-maestra',1,datetime('now'))")
    conn.execute("INSERT INTO lia_audit_events(fundacion_id,usuario_id,event_type,modulo,success,created_at) VALUES(1,11,'QUESTION_COMPLETED','formatos',1,datetime('now'))")
    for index in range(20):conn.execute("INSERT INTO lia_audit_events(fundacion_id,usuario_id,event_type,modulo,success,created_at) VALUES(2,20,'QUESTION_COMPLETED','calendario-inteligente',1,datetime('now'))")
    conn.commit();conn.close()
    result=execute('get_module_usage',args={'days':30},database_path=database,tenant_id=1,user={'id':1,'rol':'GERENTE'})
    by_module={item['module']:item for item in result['items']}
    assert by_module['base-maestra']['uses']==12 and by_module['base-maestra']['category']=='FRECUENTE'
    assert by_module['formatos']['uses']==1 and by_module['formatos']['category']=='POCO USADO'
    assert by_module['calendario-inteligente']['uses']==0
    assert result['deletion_enabled'] is False and result['scope']['foundation_id']==1
    try:execute('get_module_usage',args={},database_path=database,tenant_id=1,user={'id':2,'rol':'DOCENTE'})
    except PermissionError:pass
    else:raise AssertionError('Un rol no autorizado consultó analítica administrativa.')
print('LIAM_MODULE_USAGE_V7_PASS')
