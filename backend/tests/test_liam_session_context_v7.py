"""Memoria temporal de LIAM aislada por tenant y usuario."""
from pathlib import Path
import sys
import tempfile

BACKEND=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND))

from modules.dbapi_compat import sqlite3
from modules.asistente_capacitacion.schema import SCHEMA_SQL
from modules.asistente_capacitacion.context_service import clear,load,save,sanitize


def test_context_is_minimized_merged_and_isolated():
    assert sanitize({'selected_month':99,'password':'secret','module_id':'base-maestra'})=={'module_id':'base-maestra'}
    with tempfile.TemporaryDirectory() as tmp:
        database=str(Path(tmp)/'context.db');conn=sqlite3.connect(database);conn.executescript(SCHEMA_SQL);conn.commit();conn.close()
        first=save(database,1,10,{'module_id':'base-maestra','selected_month':9,'selected_year':2026,'password':'no'},'Publicar Base Maestra')
        assert first['context']['selected_period']=='2026-09' and 'password' not in first['context']
        second=save(database,1,10,{'selected_unit':'UCA ALTO NECORA'})
        assert second['context']['module_id']=='base-maestra' and second['active_task']=='Publicar Base Maestra'
        assert load(database,1,10)['context']['selected_unit']=='UCA ALTO NECORA'
        protected=save(database,1,10,{'active_document':'token=abc123456789'},'Revisar password=clave-super-secreta')
        assert 'abc123456789' not in protected['context']['active_document'] and 'clave-super-secreta' not in protected['active_task']
        inspect_conn=sqlite3.connect(database);raw=inspect_conn.execute('SELECT context_json,active_task FROM lia_session_context WHERE fundacion_id=1 AND usuario_id=10').fetchone();inspect_conn.close()
        assert 'abc123456789' not in raw[0] and 'clave-super-secreta' not in raw[1]
        assert load(database,2,10)['available'] is False
        assert load(database,1,11)['available'] is False
        clear(database,1,10)
        assert load(database,1,10)['available'] is False


if __name__=='__main__':
    test_context_is_minimized_merged_and_isolated()
    print('LIAM_SESSION_CONTEXT_V7_PASS')
