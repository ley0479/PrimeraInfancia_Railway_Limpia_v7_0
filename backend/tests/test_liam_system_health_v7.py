"""Salud del sistema: superadministrador, sanitización y tenant."""
from pathlib import Path
import sys
import tempfile

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from modules.asistente_capacitacion.orchestrator import LiamOrchestrator
from modules.dbapi_compat import sqlite3

with tempfile.TemporaryDirectory() as tmp:
    db = str(Path(tmp) / 'health.db');conn = sqlite3.connect(db)
    for table in ('idp_documentos','calendario_entregables','master_ninos'):
        conn.execute(f'CREATE TABLE {table}(id INTEGER PRIMARY KEY,fundacion_id INTEGER)')
    conn.execute('CREATE TABLE lia_audit_events(id INTEGER PRIMARY KEY,fundacion_id INTEGER,success INTEGER)')
    conn.executemany('INSERT INTO lia_audit_events VALUES(?,?,?)',[(1,1,0),(2,2,0),(3,1,1)])
    conn.commit();conn.close()
    orchestrator = LiamOrchestrator(db)
    result = orchestrator.run('get_system_health',args={},tenant_id=1,user={'id':1,'rol':'SUPERADMIN'}).result
    assert result['overall_status'] == 'OPERATIVO'
    assert result['failed_audit_events'] == 1
    assert result['sanitized'] is True and result['secrets_included'] is False
    serialized = str(result).lower()
    for forbidden in ('password','secret_key','jwt','database_url','connection string'):
        assert forbidden not in serialized
    try:
        orchestrator.run('get_system_health',args={},tenant_id=1,user={'id':2,'rol':'DOCENTE'})
    except PermissionError:
        pass
    else:
        raise AssertionError('Un rol no privilegiado consultó salud interna.')

print('LIAM_SYSTEM_HEALTH_V7_PASS')
