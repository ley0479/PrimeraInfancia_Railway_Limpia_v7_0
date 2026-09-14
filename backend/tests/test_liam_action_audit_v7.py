"""Trazabilidad de acciones: ciclo, privacidad y aislamiento tenant/usuario."""
from pathlib import Path
import sys,tempfile
BACKEND=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BACKEND))
from modules.asistente_capacitacion.action_audit import record_proposal,complete,list_authorized
from modules.asistente_capacitacion.schema import SCHEMA_SQL
from modules.dbapi_compat import sqlite3

with tempfile.TemporaryDirectory() as tmp:
    db=str(Path(tmp)/'audit.db');conn=sqlite3.connect(db);conn.executescript(SCHEMA_SQL);conn.close()
    ctx={'fundacion_id':1,'usuario_id':10,'session_id':'session-1'}
    proposal={'id':'generate_monthly_reports','risk':'generation','confirmation_required':True,'arguments':{'id':'2026-09','password':'no-guardar'}}
    key=record_proposal(db,ctx,proposal,'trace-1','relacion-mes')
    assert key.startswith('LAA-')
    assert complete(db,{'fundacion_id':2,'usuario_id':10},'trace-1','generate_monthly_reports','completed') is False
    assert complete(db,{'fundacion_id':1,'usuario_id':11},'trace-1','generate_monthly_reports','completed') is False
    assert complete(db,ctx,'trace-1','generate_monthly_reports','completed') is True
    conn=sqlite3.connect(db);conn.row_factory=sqlite3.Row;row=dict(conn.execute('SELECT * FROM liam_action_audit').fetchone());conn.close()
    assert row['fundacion_id']==1 and row['usuario_id']==10 and row['result']=='COMPLETED'
    assert row['requested_action']=='generate_monthly_reports' and row['approved_action']=='generate_monthly_reports'
    assert row['before_state']=='{}' and row['after_state']=='{}' and row['error'] is None
    assert 'password' not in str(row).lower() and 'no-guardar' not in str(row)
    history=list_authorized(db,{'fundacion_id':1,'usuario_id':99,'rol':'GERENTE'},50,0)
    assert history['total']==1 and history['scope']['cross_foundation'] is False
    assert 'before_state' not in history['actions'][0] and 'error' not in history['actions'][0]
    try:list_authorized(db,{'fundacion_id':1,'usuario_id':10,'rol':'DOCENTE'})
    except PermissionError:pass
    else:raise AssertionError('Un rol operativo accedió al historial administrativo.')

print('LIAM_ACTION_AUDIT_V7_PASS')
