"""Contexto efímero y minimizado de la sesión autenticada de LIAM."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import re

from modules.dbapi_compat import sqlite3
from .privacy_service import redact

FIELDS=('module_id','view_id','tab_id','modal_id','active_help_id','selected_unit','selected_month','selected_year','selected_period','active_document')


def sanitize(value: dict | None) -> dict:
    source=value if isinstance(value,dict) else {};result={}
    for key in FIELDS:
        item=source.get(key)
        if item is None or item=='':continue
        if key=='selected_month':
            try:item=int(item)
            except (TypeError,ValueError):continue
            if not 1<=item<=12:continue
        elif key=='selected_year':
            try:item=int(item)
            except (TypeError,ValueError):continue
            if not 2000<=item<=2100:continue
        else:
            item=redact(re.sub(r'\s+',' ',str(item)).strip())[:160]
        result[key]=item
    if 'selected_period' not in result and result.get('selected_year') and result.get('selected_month'):
        result['selected_period']=f"{result['selected_year']:04d}-{result['selected_month']:02d}"
    if result.get('selected_period') and not re.fullmatch(r'20\d{2}-(0[1-9]|1[0-2])',str(result['selected_period'])):
        result.pop('selected_period',None)
    return result


def load(database_path: str,tenant_id: int,user_id: int) -> dict:
    conn=sqlite3.connect(database_path);conn.row_factory=sqlite3.Row
    try:row=conn.execute('SELECT context_json,active_task,updated_at,expires_at FROM lia_session_context WHERE fundacion_id=? AND usuario_id=?',(tenant_id,user_id)).fetchone()
    finally:conn.close()
    if not row:return {'context':{},'active_task':None,'available':False}
    now=datetime.now(timezone.utc).isoformat(timespec='seconds')
    if str(row['expires_at'] or '')<now:return {'context':{},'active_task':None,'available':False,'expired':True}
    try:context=sanitize(json.loads(row['context_json'] or '{}'))
    except (TypeError,ValueError,json.JSONDecodeError):context={}
    return {'context':context,'active_task':str(row['active_task'] or '')[:240] or None,'updated_at':row['updated_at'],'expires_at':row['expires_at'],'available':True}


def save(database_path: str,tenant_id: int,user_id: int,value: dict | None,active_task: object=None) -> dict:
    current=load(database_path,tenant_id,user_id);merged={**current.get('context',{}),**sanitize(value)}
    task=redact(re.sub(r'\s+',' ',str(active_task or current.get('active_task') or '')).strip())[:240] or None
    now=datetime.now(timezone.utc);updated=now.isoformat(timespec='seconds');expires=(now+timedelta(hours=8)).isoformat(timespec='seconds')
    conn=sqlite3.connect(database_path)
    try:
        conn.execute('''INSERT INTO lia_session_context(fundacion_id,usuario_id,context_json,active_task,updated_at,expires_at) VALUES(?,?,?,?,?,?)
          ON CONFLICT(fundacion_id,usuario_id) DO UPDATE SET context_json=excluded.context_json,active_task=excluded.active_task,updated_at=excluded.updated_at,expires_at=excluded.expires_at''',(tenant_id,user_id,json.dumps(merged,ensure_ascii=False),task,updated,expires));conn.commit()
    except Exception:conn.rollback();raise
    finally:conn.close()
    return {'context':merged,'active_task':task,'updated_at':updated,'expires_at':expires,'available':True}


def clear(database_path: str,tenant_id: int,user_id: int) -> None:
    conn=sqlite3.connect(database_path)
    try:conn.execute('DELETE FROM lia_session_context WHERE fundacion_id=? AND usuario_id=?',(tenant_id,user_id));conn.commit()
    finally:conn.close()
