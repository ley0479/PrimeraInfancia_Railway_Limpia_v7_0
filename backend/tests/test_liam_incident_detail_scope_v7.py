"""Detalle de incidente sanitizado, tenant-scoped y role-scoped."""
from pathlib import Path
import sys,tempfile
BACKEND=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BACKEND))
from modules.asistente_capacitacion.error_center import get_authorized
from modules.asistente_capacitacion.schema import SCHEMA_SQL
from modules.dbapi_compat import sqlite3

with tempfile.TemporaryDirectory() as tmp:
    db=str(Path(tmp)/'incidents.db');conn=sqlite3.connect(db);conn.executescript(SCHEMA_SQL)
    sql='''INSERT INTO lia_error_incidents(incident_id,fundacion_id,usuario_id,module,action,http_status,error_code,error_type,technical_message_redacted,cause,solution,severity,safe_retry,auto_correctable,status,request_id,context_redacted,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'''
    rows=[
        ('INC-20260914-140000-AAAAAA',1,10,'rpp','generar',500,'RPP_X','error_backend','password=oculta','Causa segura','Solución segura','high',0,0,'OPEN','trace-secreto','{"screen":"privada"}','2026-09-14','2026-09-14'),
        ('INC-20260914-140001-BBBBBB',2,10,'rpp','generar',500,'RPP_Y','error_backend','secreto','Otra','Otra','high',0,0,'OPEN','trace-otra','{}','2026-09-14','2026-09-14'),
    ]
    conn.executemany(sql,rows);conn.commit();conn.close()
    own=get_authorized(db,rows[0][0],1,10,'DOCENTE')
    assert own and own['scope']=='own_user' and own['sanitized'] is True
    assert 'technical_message_redacted' not in own and 'request_id' not in own and 'context_redacted' not in own
    assert get_authorized(db,rows[0][0],1,11,'DOCENTE') is None
    assert get_authorized(db,rows[0][0],1,99,'GERENTE')['scope']=='foundation'
    assert get_authorized(db,rows[1][0],1,99,'SUPERADMIN') is None

print('LIAM_INCIDENT_DETAIL_SCOPE_V7_PASS')
