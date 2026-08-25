"""Herramientas cerradas, error estructurado y aislamiento de formatos."""
from pathlib import Path
import tempfile,sys
BACKEND=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BACKEND))
from modules.dbapi_compat import sqlite3
from modules.asistente_capacitacion.tool_registry import ALLOWED_TOOLS,execute

assert ALLOWED_TOOLS==frozenset({'get_pending_activities_summary','get_document_processing_status','get_format_generation_status','get_structured_error'})
try: execute('run_sql',args={},database_path='none',tenant_id=1,user={})
except PermissionError: pass
else: raise AssertionError('Una herramienta fuera de lista fue aceptada.')
error=execute('get_structured_error',args={'code':'PARTICIPANTES_REQUERIDOS'},database_path='none',tenant_id=1,user={})
assert error['confidence']=='confirmed' and error['severity']=='error'

with tempfile.TemporaryDirectory() as tmp:
    db=str(Path(tmp)/'lia.db');conn=sqlite3.connect(db)
    conn.execute('CREATE TABLE mp_plantillas(id INTEGER PRIMARY KEY,tipo TEXT,fundacion_id INTEGER)')
    conn.execute('CREATE TABLE mp_pruebas(id INTEGER PRIMARY KEY,plantilla_id INTEGER,estado TEXT,total_usuarios INTEGER,errores_json TEXT,archivo_generado TEXT,fecha_creacion TEXT)')
    conn.execute("INSERT INTO mp_plantillas VALUES(1,'RAM',1)");conn.execute("INSERT INTO mp_plantillas VALUES(2,'RPP',2)")
    conn.execute("INSERT INTO mp_pruebas VALUES(10,1,'GENERADO',20,NULL,'ram.xlsx','2026-08-25')")
    conn.execute("INSERT INTO mp_pruebas VALUES(20,2,'GENERADO',30,NULL,'rpp.xlsx','2026-08-25')");conn.commit();conn.close()
    own=execute('get_format_generation_status',args={'test_id':10},database_path=db,tenant_id=1,user={'id':1})
    assert own['download_ready'] is True and own['format_type']=='RAM'
    try: execute('get_format_generation_status',args={'test_id':20},database_path=db,tenant_id=1,user={'id':1})
    except LookupError: pass
    else: raise AssertionError('Se cruzó una generación de otro tenant.')
print('LIA_TOOL_REGISTRY_V7_PASS')
