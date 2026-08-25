"""Persistencia aditiva y aislada de preferencias, feedback y auditoría."""
from pathlib import Path
import tempfile,sys
BACKEND=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BACKEND))
from modules.dbapi_compat import sqlite3
from modules.asistente_capacitacion.schema import SCHEMA_SQL
with tempfile.TemporaryDirectory() as tmp:
    conn=sqlite3.connect(str(Path(tmp)/'lia.db'));conn.executescript(SCHEMA_SQL)
    conn.execute("INSERT INTO lia_user_preferences(fundacion_id,usuario_id,created_at,updated_at) VALUES(1,7,'x','x')")
    conn.execute("INSERT INTO lia_user_preferences(fundacion_id,usuario_id,created_at,updated_at) VALUES(2,7,'x','x')")
    assert conn.execute('SELECT COUNT(*) FROM lia_user_preferences WHERE usuario_id=7').fetchone()[0]==2
    conn.execute("INSERT INTO lia_feedback(fundacion_id,usuario_id,rating,reason,created_at) VALUES(1,7,-1,'respuesta_no_util','x')")
    conn.execute("INSERT INTO lia_audit_events(fundacion_id,usuario_id,event_type,success,created_at) VALUES(1,7,'TEST',1,'x')")
    assert conn.execute('SELECT COUNT(*) FROM lia_feedback WHERE fundacion_id=2').fetchone()[0]==0
    assert conn.execute('SELECT COUNT(*) FROM lia_audit_events WHERE fundacion_id=2').fetchone()[0]==0
    conn.close()
print('LIA_PREFERENCES_FEEDBACK_V7_PASS')
