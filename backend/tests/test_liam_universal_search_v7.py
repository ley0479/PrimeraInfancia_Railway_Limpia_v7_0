"""Búsqueda universal paginada, sin datos sensibles ni cruce tenant."""
from pathlib import Path
import sys,tempfile
BACKEND=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BACKEND))
from modules.dbapi_compat import sqlite3
from modules.asistente_capacitacion.action_intents import propose_action
from modules.asistente_capacitacion.orchestrator import LiamOrchestrator

action=propose_action('Liam busca la unidad UDS Uno')
assert action['server_tool']=='universal_search' and action['arguments']['resource']=='units'
with tempfile.TemporaryDirectory() as tmp:
    db=str(Path(tmp)/'search.db');conn=sqlite3.connect(db)
    conn.execute('CREATE TABLE master_ninos(id INTEGER,nombre_completo TEXT,documento TEXT,unidad_servicio TEXT,docente TEXT,estado TEXT,activo INTEGER,fundacion_id INTEGER)')
    conn.executemany('INSERT INTO master_ninos VALUES(?,?,?,?,?,?,?,?)',[(1,'ANA UNO','101','UDS UNO','DOCENTE UNO','ACTIVO',1,1),(2,'ANA AJENA','999','UDS DOS','DOCENTE DOS','ACTIVO',1,2)])
    conn.commit();conn.close()
    outcome=LiamOrchestrator(db).run('universal_search',args={'query':'ANA','resource':'beneficiaries','limit':10},tenant_id=1,user={'rol':'DOCENTE'},module='dashboard')
    assert outcome.result['total']==1 and outcome.result['results'][0]['reference']=='101'
    assert 'email' not in outcome.result['results'][0] and outcome.result['scope']['cross_foundation'] is False
print('LIAM_UNIVERSAL_SEARCH_V7_PASS')
