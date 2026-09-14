"""Diagnóstico técnico elevado, sanitizado y tenant-scoped."""
from pathlib import Path
import sys,tempfile
BACKEND=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BACKEND))
from modules.asistente_capacitacion.orchestrator import LiamOrchestrator
from modules.asistente_capacitacion.schema import SCHEMA_SQL
from modules.dbapi_compat import sqlite3

with tempfile.TemporaryDirectory() as tmp:
    db=str(Path(tmp)/'technical.db');conn=sqlite3.connect(db);conn.executescript(SCHEMA_SQL)
    sql='''INSERT INTO lia_error_incidents(incident_id,fundacion_id,usuario_id,module,action,http_status,error_code,error_type,technical_message_redacted,cause,solution,severity,safe_retry,auto_correctable,status,request_id,context_redacted,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'''
    rows=[('INC-20260914-150000-AAAAAA',1,10,'rpp','generar',500,'RPP_X','error_backend','password=abc documento 12345678','Causa','Solución','high',0,0,'OPEN','admin@example.com','{"method":"POST","screen":"rpp","extra":"oculto"}','2026-09-14','2026-09-14'),('INC-20260914-150001-BBBBBB',2,20,'ram','generar',500,'RAM_X','error_backend','otro tenant','Causa','Solución','high',0,0,'OPEN','trace-2','{}','2026-09-14','2026-09-14')]
    conn.executemany(sql,rows);conn.commit();conn.close();orchestrator=LiamOrchestrator(db)
    result=orchestrator.run('get_technical_diagnostic',args={'incident_id':rows[0][0]},tenant_id=1,user={'id':99,'rol':'SUPERADMIN'}).result
    item=result['diagnostic'];assert item['incident_id']==rows[0][0] and result['scope']['cross_foundation'] is False
    assert result['sanitized'] is True and result['secrets_included'] is False
    assert '[SECRETO REDACTADO]' in item['exception_sanitized'] and '[IDENTIFICADOR]' in item['exception_sanitized']
    assert item['trace_id']=='[CORREO]' and item['context']=={'method':'POST','screen':'rpp'}
    try:orchestrator.run('get_technical_diagnostic',args={'incident_id':rows[0][0]},tenant_id=1,user={'id':10,'rol':'DOCENTE'})
    except PermissionError:pass
    else:raise AssertionError('DOCENTE accedió al diagnóstico técnico.')
    try:orchestrator.run('get_technical_diagnostic',args={'incident_id':rows[1][0]},tenant_id=1,user={'id':99,'rol':'SUPERADMIN'})
    except LookupError:pass
    else:raise AssertionError('SUPERADMIN cruzó la fundación activa.')

print('LIAM_TECHNICAL_DIAGNOSTIC_V7_PASS')
