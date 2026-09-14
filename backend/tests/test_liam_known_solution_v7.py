"""Base de conocimiento: catálogo seguro y aislamiento estricto por tenant."""
from pathlib import Path
import sys,tempfile

BACKEND=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BACKEND))
from modules.asistente_capacitacion.orchestrator import LiamOrchestrator
from modules.asistente_capacitacion.schema import SCHEMA_SQL
from modules.dbapi_compat import sqlite3


with tempfile.TemporaryDirectory() as tmp:
    db=str(Path(tmp)/'knowledge.db');conn=sqlite3.connect(db);conn.executescript(SCHEMA_SQL)
    sql='''INSERT INTO lia_error_incidents(incident_id,fundacion_id,usuario_id,module,action,http_status,error_code,error_type,technical_message_redacted,cause,solution,severity,safe_retry,auto_correctable,status,request_id,context_redacted,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'''
    rows=[
        ('INC-20260914-130000-AAAAAA',1,10,'rpp','generar',500,'CUSTOM_RPP_9','error_backend','password=secreto','Nombre privado','Revisar los datos obligatorios del formato.','high',0,0,'OPEN','trace-privado','{}','2026-09-14','2026-09-14'),
        ('INC-20260914-130001-BBBBBB',1,11,'rpp','generar',422,'CUSTOM_RPP_9','error_datos','token=secreto','Documento privado','Revisar los datos obligatorios del formato.','medium',1,0,'RESOLVED','trace-2','{}','2026-09-14','2026-09-14'),
        ('INC-20260914-130002-CCCCCC',2,20,'rpp','generar',500,'CUSTOM_RPP_9','error_backend','api_key=secreto','Otra fundación','No debe aparecer.','high',0,0,'OPEN','trace-3','{}','2026-09-14','2026-09-14'),
    ]
    conn.executemany(sql,rows);conn.commit();conn.close();orchestrator=LiamOrchestrator(db)

    result=orchestrator.run('get_known_solution',args={'code':'CUSTOM_RPP_9'},tenant_id=1,user={'id':10,'rol':'DOCENTE'}).result
    item=result['known_solution']
    assert item['occurrences']==2 and item['resolved_occurrences']==1
    assert result['scope']['foundation_id']==1 and result['scope']['cross_foundation'] is False
    assert result['raw_messages_included'] is False and result['technical_details_included'] is False
    rendered=str(result).lower()
    assert 'otra fundación' not in rendered and 'password' not in rendered and 'trace-' not in rendered
    assert 'nombre privado' not in rendered and 'documento privado' not in rendered

    catalog=orchestrator.run('get_known_solution',args={'code':'PARTICIPANTES_REQUERIDOS'},tenant_id=1,user={'id':10,'rol':'DOCENTE'}).result
    assert catalog['known_solution']['catalog_confirmed'] is True
    assert catalog['known_solution']['occurrences']==0

    try:
        orchestrator.run('get_known_solution',args={'code':'UNKNOWN_CODE_404'},tenant_id=1,user={'id':10,'rol':'DOCENTE'})
    except LookupError:
        pass
    else:
        raise AssertionError('Un código desconocido sin incidencia local fue tratado como solución conocida.')

print('LIAM_KNOWN_SOLUTION_V7_PASS')
