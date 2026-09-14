"""Contrato de historial acumulativo y aislado de Lía."""
from modules.asistente_capacitacion.schema import SCHEMA_SQL
from modules.dbapi_compat import sqlite3
from pathlib import Path

def test_messages_are_append_only_and_tenant_scoped():
    conn=sqlite3.connect(':memory:');conn.row_factory=sqlite3.Row;conn.executescript(SCHEMA_SQL)
    rows=[(1,7,'user','Primera orden'),(1,7,'assistant','Primera respuesta'),(1,7,'user','Segunda orden'),(1,7,'assistant','Segunda respuesta'),(2,7,'user','Otra fundación')]
    for fid,uid,role,content in rows:
        conn.execute('INSERT INTO lia_conversation_messages(fundacion_id,usuario_id,role,content_redacted,module,request_id,created_at) VALUES(?,?,?,?,?,?,?)',(fid,uid,role,content,'dashboard','req','2026-09-14T10:00:00'))
    saved=conn.execute('SELECT role,content_redacted FROM lia_conversation_messages WHERE fundacion_id=? AND usuario_id=? ORDER BY id',(1,7)).fetchall()
    assert [(x['role'],x['content_redacted']) for x in saved]==[(x[2],x[3]) for x in rows[:4]]
    assert conn.execute('SELECT COUNT(*) FROM lia_conversation_messages').fetchone()[0]==5
    conn.close()

def test_history_supports_search_export_paging_and_voice():
    root=Path(__file__).resolve().parents[2]
    routes=(root/'backend/modules/asistente_capacitacion/routes.py').read_text(encoding='utf-8')
    controller=(root/'frontend/js/liam/liam-controller.js').read_text(encoding='utf-8')
    assert "chat/history/export.csv" in routes and "LOWER(content_redacted) LIKE LOWER(?)" in routes
    assert "event=='transcript'" in routes and "saveVoiceTranscript(\"user\"" in controller and "saveVoiceTranscript(\"assistant\"" in controller
    assert 'data-action="history-more"' in controller and 'data-action="history-search"' in controller and 'data-action="history-export"' in controller

if __name__=='__main__':
    test_messages_are_append_only_and_tenant_scoped()
    test_history_supports_search_export_paging_and_voice()
    print('LIA_CONVERSATION_HISTORY_V7_PASS')
