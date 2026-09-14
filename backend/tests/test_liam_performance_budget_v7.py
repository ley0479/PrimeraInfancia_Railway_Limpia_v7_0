"""Presupuesto local reproducible para páginas y payloads administrativos LIAM."""
from pathlib import Path
import json,sys,tempfile,time
BACKEND=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BACKEND))
from modules.asistente_capacitacion.action_audit import list_authorized
from modules.asistente_capacitacion.schema import SCHEMA_SQL
from modules.dbapi_compat import sqlite3

MAX_ROWS=100
MAX_SERIALIZED_BYTES=128*1024
MAX_SQLITE_SECONDS=2.5

with tempfile.TemporaryDirectory() as tmp:
    db=str(Path(tmp)/'performance.db');conn=sqlite3.connect(db);conn.executescript(SCHEMA_SQL)
    sql='''INSERT INTO liam_action_audit(action_key,fundacion_id,usuario_id,trace_id,intent,requested_action,approved_action,risk_level,resource,before_state,after_state,result,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)'''
    rows=[]
    for index in range(5000):
        tenant=1 if index<4500 else 2;rows.append((f'LAA-{index}',tenant,index%50,f'trace-{index}','open_module','open_module','open_module','navigation','dashboard','{}','{}','COMPLETED','2026-09-14','2026-09-14'))
    conn.executemany(sql,rows);conn.commit();conn.close()
    started=time.perf_counter();result=list_authorized(db,{'fundacion_id':1,'usuario_id':1,'rol':'SUPERADMIN'},limit=999,offset=0);elapsed=time.perf_counter()-started
    assert result['total']==4500 and len(result['actions'])==MAX_ROWS and result['has_more'] is True
    assert result['scope']=={'foundation_id':1,'cross_foundation':False}
    assert len(json.dumps(result,ensure_ascii=False).encode('utf-8'))<=MAX_SERIALIZED_BYTES
    assert elapsed<=MAX_SQLITE_SECONDS,f'Consulta paginada tardó {elapsed:.3f}s'

routes=(BACKEND/'modules'/'asistente_capacitacion'/'routes.py').read_text(encoding='utf-8')
tools=(BACKEND/'modules'/'asistente_capacitacion'/'tool_registry.py').read_text(encoding='utf-8')
assert "value['beneficiaries'][:30]" in routes and "value['results'][:30]" in routes and "value['profiles'][:30]" in routes
assert "min(int(args.get('limit') or 25),50)" in tools
print('LIAM_PERFORMANCE_BUDGET_V7_PASS')
