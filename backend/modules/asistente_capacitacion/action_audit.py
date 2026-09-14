"""Trazabilidad estructurada y sanitizada del ciclo de acciones LIAM."""
from __future__ import annotations
from datetime import datetime
import hashlib
from modules.dbapi_compat import sqlite3
from .privacy_service import redact

def _text(value,limit=160):return redact(str(value or ''))[:limit]
def record_proposal(database_path,ctx,proposal,trace_id,module=''):
    action=_text(proposal.get('id') or proposal.get('action'),100);trace=_text(trace_id,80)
    raw=f"{int(ctx.get('fundacion_id') or 1)}:{int(ctx.get('usuario_id') or 0)}:{trace}:{action}"
    key='LAA-'+hashlib.sha256(raw.encode()).hexdigest()[:24];now=datetime.now().isoformat(timespec='seconds')
    result='AWAITING_CONFIRMATION' if proposal.get('confirmation_required') else 'AUTHORIZED'
    conn=sqlite3.connect(database_path)
    conn.execute('''INSERT INTO liam_action_audit(action_key,fundacion_id,usuario_id,session_id,trace_id,intent,requested_action,approved_action,risk_level,resource,resource_id,before_state,after_state,result,error,created_at,updated_at)
      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(action_key) DO UPDATE SET approved_action=excluded.approved_action,risk_level=excluded.risk_level,result=excluded.result,updated_at=excluded.updated_at''',
      (key,int(ctx.get('fundacion_id') or 1),int(ctx.get('usuario_id') or 0),_text(ctx.get('_session_id') or ctx.get('session_id'),80) or None,trace,action,action,action,_text(proposal.get('risk'),40),_text(module,80) or None,_text((proposal.get('arguments') or {}).get('id'),100) or None,'{}','{}',result,None,now,now))
    conn.commit();conn.close();return key

def complete(database_path,ctx,trace_id,action,status,detail=''):
    now=datetime.now().isoformat(timespec='seconds');trace=_text(trace_id,80);name=_text(action,100)
    conn=sqlite3.connect(database_path)
    row=conn.execute('''SELECT action_key FROM liam_action_audit WHERE fundacion_id=? AND usuario_id=? AND trace_id=? AND requested_action=? ORDER BY id DESC LIMIT 1''',(int(ctx.get('fundacion_id') or 1),int(ctx.get('usuario_id') or 0),trace,name)).fetchone()
    if row:
        normalized=str(status or '').upper();error=_text(detail,300) if normalized=='FAILED' else None
        conn.execute('UPDATE liam_action_audit SET result=?,error=?,updated_at=? WHERE action_key=?',(normalized,error,now,row[0]));conn.commit()
    conn.close();return bool(row)

def list_authorized(database_path,ctx,limit=50,offset=0):
    role=str(ctx.get('rol') or ctx.get('role') or '').upper()
    if role not in {'SUPERADMIN','GERENTE'}:raise PermissionError('Tu rol no tiene permiso para consultar el historial administrativo de acciones.')
    limit=max(1,min(int(limit or 50),100));offset=max(0,int(offset or 0));tenant=int(ctx.get('fundacion_id') or 1)
    conn=sqlite3.connect(database_path);conn.row_factory=sqlite3.Row
    total=int(conn.execute('SELECT COUNT(*) FROM liam_action_audit WHERE fundacion_id=?',(tenant,)).fetchone()[0] or 0)
    rows=[dict(row) for row in conn.execute('''SELECT action_key,usuario_id,trace_id,intent,requested_action,approved_action,risk_level,resource,resource_id,result,created_at,updated_at
      FROM liam_action_audit WHERE fundacion_id=? ORDER BY id DESC LIMIT ? OFFSET ?''',(tenant,limit,offset)).fetchall()]
    conn.close();return {'scope':{'foundation_id':tenant,'cross_foundation':False},'total':total,'limit':limit,'offset':offset,'has_more':offset+len(rows)<total,'actions':rows,'technical_details_included':False}
