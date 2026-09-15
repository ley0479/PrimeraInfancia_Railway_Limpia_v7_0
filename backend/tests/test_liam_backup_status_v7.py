"""Consulta sanitizada de backups, sin restauración ni secretos."""
from pathlib import Path
import sys,tempfile
BACKEND=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BACKEND))
from modules.dbapi_compat import sqlite3
from modules.backups.schema import BACKUPS_SCHEMA_SQL
from modules.asistente_capacitacion.tool_registry import execute

with tempfile.TemporaryDirectory() as tmp:
    database=str(Path(tmp)/'backup.db');conn=sqlite3.connect(database);conn.executescript(BACKUPS_SCHEMA_SQL)
    conn.execute("INSERT INTO backups_sistema(archivo,ruta_archivo,motivo,sha256,tamano_bytes,estado,integridad,fundacion_id,fecha_creacion) VALUES('secret.zip','C:/secret/secret.zip','AUTO_DIARIO','abcdef',2048,'VALIDO','OK',1,'2026-09-14T08:00:00')")
    conn.commit();conn.close()
    result=execute('get_backup_status',args={},database_path=database,tenant_id=1,user={'id':1,'rol':'SUPERADMIN'})
    assert result['summary']=={'total':1,'valid':1,'errors':0}
    assert result['latest']['tamano_bytes']==2048 and 'archivo' not in result['latest'] and 'ruta_archivo' not in result['latest'] and 'sha256' not in result['latest']
    assert result['restore_available'] is False and result['paths_included'] is False
    assert result['restore_proposal_available'] is True and result['restore_automatic'] is False
    try:execute('get_backup_status',args={},database_path=database,tenant_id=1,user={'id':2,'rol':'GERENTE'})
    except PermissionError:pass
    else:raise AssertionError('Un rol no autorizado consultó los backups globales.')
print('LIAM_BACKUP_STATUS_V7_PASS')
