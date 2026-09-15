"""Aprobación reautenticada de evidencia ADMIN/DEV, sin aplicar cambios."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import hmac
import json
import re
import uuid

from modules.dbapi_compat import sqlite3
from werkzeug.security import check_password_hash

from .dev_sandbox_results import REQUEST_PATTERN, SandboxResultError


def approve(database_path: str, request_id: str, tenant_id: int, user_id: int, password: str, result_sha256: str) -> dict:
    request_id=str(request_id or '').strip().upper();result_sha256=str(result_sha256 or '').strip().lower()
    if not REQUEST_PATTERN.fullmatch(request_id) or not re.fullmatch(r'[a-f0-9]{64}',result_sha256):
        raise SandboxResultError('La solicitud o el checksum del resultado no son válidos.')
    conn=sqlite3.connect(database_path);conn.row_factory=sqlite3.Row
    try:
        user=conn.execute('SELECT password_hash FROM usuarios_app WHERE id=? AND fundacion_id=? AND COALESCE(activo,1)=1',(user_id,tenant_id)).fetchone()
        if not user or not password or not check_password_hash(str(user['password_hash'] or ''),password):
            raise SandboxResultError('Debes reautenticarte con tu contraseña actual para aprobar el cambio.',403)
        change=conn.execute('SELECT status,module FROM lia_dev_change_requests WHERE request_id=? AND fundacion_id=? AND usuario_id=?',(request_id,tenant_id,user_id)).fetchone()
        if not change:raise SandboxResultError('No se encontró la solicitud en la sesión activa.',404)
        if str(change['status'])=='APPROVED':raise SandboxResultError('La solicitud ya fue aprobada.',409)
        plan=conn.execute("SELECT content_sha256 FROM lia_dev_change_artifacts WHERE request_id=? AND fundacion_id=? AND usuario_id=? AND artifact_type='SANDBOX_PLAN'",(request_id,tenant_id,user_id)).fetchone()
        result=conn.execute("SELECT content_json,content_sha256,status FROM lia_dev_change_artifacts WHERE request_id=? AND fundacion_id=? AND usuario_id=? AND artifact_type='SANDBOX_RESULT'",(request_id,tenant_id,user_id)).fetchone()
        if not plan or not result or str(result['status'])!='PASSED':raise SandboxResultError('Solo puede aprobarse un resultado de sandbox completamente satisfactorio.',409)
        if not hmac.compare_digest(str(result['content_sha256']).lower(),result_sha256):raise SandboxResultError('El checksum aprobado no coincide con el resultado vigente.',409)
        result_content=json.loads(result['content_json']);now=datetime.now(ZoneInfo('America/Bogota')).isoformat(timespec='seconds')
        approval={'request_id':request_id,'approved_by':user_id,'approved_at':now,'plan_sha256':str(plan['content_sha256']),'result_sha256':result_sha256,'scope':{'fundacion_id':tenant_id,'module':change['module']},'code_applied':False,'deployment_started':False}
        rollback={'request_id':request_id,'created_at':now,'base_commit':result_content.get('base_commit'),'strategy':'Revertir exclusivamente el futuro commit aprobado y verificar nuevamente todas las pruebas del plan.','changed_paths':result_content.get('changed_paths') or [],'automatic_execution':False,'deployment_started':False}
        for artifact_type,content,status in (('APPROVAL',approval,'APPROVED'),('ROLLBACK_PLAN',rollback,'READY')):
            encoded=json.dumps(content,ensure_ascii=False,sort_keys=True,separators=(',',':'));digest=hashlib.sha256(encoded.encode()).hexdigest();artifact_id='ART-'+uuid.uuid4().hex[:12].upper()
            conn.execute('''INSERT INTO lia_dev_change_artifacts(artifact_id,request_id,fundacion_id,usuario_id,artifact_type,content_json,content_sha256,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(fundacion_id,usuario_id,request_id,artifact_type) DO UPDATE SET artifact_id=excluded.artifact_id,content_json=excluded.content_json,content_sha256=excluded.content_sha256,status=excluded.status,updated_at=excluded.updated_at''',(artifact_id,request_id,tenant_id,user_id,artifact_type,encoded,digest,status,now,now))
        conn.execute("UPDATE lia_dev_change_requests SET status='APPROVED',updated_at=? WHERE request_id=? AND fundacion_id=? AND usuario_id=?",(now,request_id,tenant_id,user_id));conn.commit()
    except Exception:conn.rollback();raise
    finally:conn.close()
    return {'request_id':request_id,'status':'APPROVED','approved_result_sha256':result_sha256,'rollback_plan':rollback,'code_applied':False,'deployment_started':False,'manual_implementation_required':True}
