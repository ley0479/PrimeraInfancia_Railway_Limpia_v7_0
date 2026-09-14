"""Query Builder cerrado: campos permitidos, vista previa y aislamiento tenant."""
from pathlib import Path
import sys
import tempfile

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from modules.asistente_capacitacion.orchestrator import LiamOrchestrator
from modules.dbapi_compat import sqlite3

with tempfile.TemporaryDirectory() as tmp:
    db = str(Path(tmp) / 'reports.db')
    conn = sqlite3.connect(db)
    conn.execute('''CREATE TABLE master_ninos(
      id INTEGER PRIMARY KEY,fundacion_id INTEGER,activo INTEGER,unidad_servicio TEXT,
      coordinador TEXT,docente TEXT,grupo_etario TEXT)''')
    conn.executemany('INSERT INTO master_ninos VALUES(?,?,?,?,?,?,?)', [
        (1,1,1,'UDS A','Ana','Dora','3 a 5'),(2,1,1,'UDS A','Ana','Dora','1 a 2'),
        (3,1,1,'UDS B','Bea','Diego','3 a 5'),(4,2,1,'UDS AJENA','Otro','Otro','3 a 5'),
    ])
    conn.commit();conn.close()
    orchestrator = LiamOrchestrator(db)
    outcome = orchestrator.run('build_custom_report_preview', args={
        'report':'unit_coverage','fields':['unit','teacher','children_count']
    }, tenant_id=1, user={'id':9,'rol':'COORDINADOR','nombre_completo':'Ana'})
    data = outcome.result
    assert data['preview_only'] is True and data['read_only'] is True
    assert data['fields'] == ['unit','teacher','children_count']
    assert sum(row['children_count'] for row in data['rows']) == 2
    assert data['role_scope'] == 'assigned_records'
    assert 'UDS B' not in str(data)
    assert 'UDS AJENA' not in str(data)
    assert data['scope']['cross_foundation'] is False
    try:
        orchestrator.run('build_custom_report_preview', args={
            'report':'unit_coverage','fields':['unit','password']
        }, tenant_id=1, user={'id':9,'rol':'COORDINADOR','nombre_completo':'Ana'})
    except ValueError:
        pass
    else:
        raise AssertionError('Se aceptó un campo fuera del catálogo seguro.')
    try:
        orchestrator.run('build_custom_report_preview', args={'report':'SELECT * FROM usuarios_app'}, tenant_id=1, user={'id':9,'rol':'COORDINADOR','nombre_completo':'Ana'})
    except ValueError:
        pass
    else:
        raise AssertionError('Se aceptó SQL como tipo de reporte.')

print('LIAM_SAFE_REPORT_BUILDER_V7_PASS')
