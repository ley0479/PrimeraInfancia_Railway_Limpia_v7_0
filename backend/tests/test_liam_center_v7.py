"""Centro Liam: autorización, alcance explícito y degradación segura."""
from pathlib import Path
import sys
import tempfile

BACKEND=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND))

from modules.dbapi_compat import sqlite3
from modules.asistente_capacitacion.schema import SCHEMA_SQL
from modules.asistente_capacitacion.tool_registry import execute


def test_center_is_superadmin_only_and_reports_partial_sources():
    with tempfile.TemporaryDirectory() as tmp:
        database=str(Path(tmp)/'liam-center.db')
        conn=sqlite3.connect(database)
        conn.executescript(SCHEMA_SQL)
        conn.execute("INSERT INTO lia_audit_events(fundacion_id,usuario_id,event_type,success,created_at) VALUES(1,7,'QUESTION_COMPLETED',1,datetime('now','localtime'))")
        conn.execute("INSERT INTO lia_audit_events(fundacion_id,usuario_id,event_type,success,created_at) VALUES(2,8,'QUESTION_COMPLETED',1,datetime('now','localtime'))")
        conn.execute("INSERT INTO lia_action_proposals(proposal_id,usuario_id,action_name,target_fundacion_id,arguments_json,before_json,after_json,status,expires_at,created_at) VALUES('p-1',7,'update_user',1,'{}','{}','{}','PENDING',datetime('now','+1 day'),datetime('now'))")
        conn.commit();conn.close()

        result=execute('get_liam_center',args={},database_path=database,tenant_id=1,user={'id':7,'rol':'SUPERADMIN'})
        assert result['read_only'] is True and result['sanitized'] is True
        assert result['scope']['active_foundation_id']==1
        assert result['scope']['cross_foundation_sections']==['foundations','backups','changes']
        assert result['sections']['activity']['total']==1
        assert result['sections']['changes']['pending']==1
        assert result['availability']['activity'] is True
        assert isinstance(result['metrics'],list) and result['metrics']
        assert result['partial'] is True

        try:
            execute('get_liam_center',args={},database_path=database,tenant_id=1,user={'id':9,'rol':'GERENTE'})
        except PermissionError:
            pass
        else:
            raise AssertionError('Un rol no autorizado pudo abrir el Centro Liam.')


if __name__=='__main__':
    test_center_is_superadmin_only_and_reports_partial_sources()
    print('LIAM_CENTER_V7_PASS')
