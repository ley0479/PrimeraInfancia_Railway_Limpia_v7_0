"""Supervisor de entregables: clasificación real y alcance por rol/tenant."""
from pathlib import Path
import sys
import tempfile

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from modules.asistente_capacitacion.orchestrator import LiamOrchestrator
from modules.dbapi_compat import sqlite3

with tempfile.TemporaryDirectory() as tmp:
    db = str(Path(tmp) / 'deliverables.db')
    conn = sqlite3.connect(db)
    conn.execute('''CREATE TABLE calendario_entregables(
      id INTEGER PRIMARY KEY,fundacion_id INTEGER,titulo TEXT,fecha_limite TEXT,modulo TEXT,
      responsable_nombre TEXT,coordinador TEXT,unidad TEXT,estado TEXT,prioridad TEXT,
      requiere_evidencia INTEGER,archivo_evidencia TEXT,fecha_entrega TEXT,clave_unica TEXT)''')
    rows = [
      (1,1,'Informe aprobado','2026-09-01','reportes','Dora','Ana','UDS A','aprobado','Alta',1,'a.pdf','2026-09-01','a'),
      (2,1,'Informe pendiente','2099-09-20','reportes','Dora','Ana','UDS A','pendiente','Media',0,None,None,'b'),
      (3,1,'Informe vencido','2020-09-01','reportes','Dora','Ana','UDS B','pendiente','Crítica',0,None,None,'c'),
      (4,1,'Informe devuelto','2026-09-04','reportes','Dora','Ana','UDS B','devuelto','Alta',1,'d.pdf','2026-09-03','d'),
      (5,1,'Informe incompleto','2026-09-05','reportes','Dora','Ana','UDS A','entregado','Alta',1,None,'2026-09-05','a'),
      (6,1,'Otro coordinador','2026-09-05','reportes','Diego','Bea','UDS C','pendiente','Alta',0,None,None,'f'),
      (7,2,'Otra fundación','2026-09-05','reportes','Dora','Ana','UDS AJENA','pendiente','Alta',0,None,None,'g'),
    ]
    conn.executemany('INSERT INTO calendario_entregables VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)', rows)
    conn.commit();conn.close()

    outcome = LiamOrchestrator(db).run('supervise_deliverables', args={}, tenant_id=1,
      user={'id':4,'rol':'COORDINADOR','nombre_completo':'Ana'})
    data = outcome.result;summary = data['summary']
    assert summary == {'expected':5,'received':2,'pending':1,'overdue':1,'returned':1,'incomplete':1,'duplicates':1,'compliance_percent':40.0}
    assert data['role_scope'] == 'assigned_records'
    assert 'Otro coordinador' not in str(data) and 'Otra fundación' not in str(data)
    assert {item['category'] for item in data['items']} == {'RECIBIDO','PENDIENTE','VENCIDO','DEVUELTO','INCOMPLETO'}
    assert data['read_only'] is True and data['scope']['cross_foundation'] is False

print('LIAM_DELIVERABLE_SUPERVISOR_V7_PASS')
