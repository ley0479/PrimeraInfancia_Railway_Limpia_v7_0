"""Centro transversal de incidentes explicables por LIAM."""
from __future__ import annotations

from datetime import datetime
import json, re, uuid
from modules.dbapi_compat import sqlite3
from .error_catalog import explain
from .privacy_service import redact

TYPE_BY_STATUS = {400:'error_usuario',401:'error_permisos',403:'error_permisos',404:'error_datos',409:'error_integridad',413:'error_archivo',415:'error_archivo',422:'error_datos',429:'error_configuracion',502:'error_integracion',503:'error_backend',504:'error_red'}

def classify(*,code='',message='',status=500):
    key=str(code or '').strip().upper().replace(' ','_') or f'HTTP_{status}'
    text=(str(message or '')+' '+key).casefold()
    kind=TYPE_BY_STATUS.get(int(status or 500),'error_backend' if int(status or 500)>=500 else 'error_desconocido')
    if any(x in text for x in ('plantilla','hoja esperada')): kind='error_plantilla'
    elif any(x in text for x in ('postgres','database','base de datos')): kind='error_base_datos'
    elif any(x in text for x in ('conex','network','fetch','timeout')): kind='error_red'
    elif any(x in text for x in ('duplic','conflict','unique')): kind='error_integridad'
    elif any(x in text for x in ('archivo','excel','pdf','csv')): kind='error_archivo'
    known=explain(key)
    if known.get('confidence')=='confirmed':
        cause=known['message'];solution='; '.join(known.get('actions') or []) or 'Revisa los datos indicados e intenta nuevamente.'
    else:
        cause=redact(message)[:500] or 'La plataforma no recibió información suficiente para confirmar la causa.'
        solutions={'error_permisos':'Verifica tu sesión, rol y UDS autorizadas.','error_usuario':'Corrige los campos señalados y vuelve a intentar.','error_datos':'Comprueba los datos obligatorios y el periodo seleccionado.','error_archivo':'Usa el archivo y la plantilla correspondientes a este módulo.','error_plantilla':'Verifica que exista una plantilla oficial vigente y con la estructura esperada.','error_red':'Comprueba la conexión y reintenta; la solicitud no debe asumirse como completada.','error_base_datos':'Conserva el incidente y solicita revisión técnica antes de repetir cambios.','error_integridad':'Revisa si el registro ya existe o entra en conflicto con información publicada.','error_backend':'Conserva el incidente para revisión técnica; no repitas una modificación sin verificar el resultado.'}
        solution=solutions.get(kind,'Conserva el incidente y solicita revisión con el contexto mostrado.')
    return {'code':key,'type':kind,'cause':cause,'solution':solution,'severity':'high' if int(status or 500)>=500 else 'medium','safe_retry':kind in {'error_red','error_usuario','error_datos'},'auto_correctable':False}

def record(database_path,*,tenant_id,user_id,module,action,status,code,message,request_id=None,context=None):
    diagnosis=classify(code=code,message=message,status=status)
    incident_id='INC-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6].upper()
    now=datetime.now().isoformat(timespec='seconds');safe_context={}
    for key in ('period','screen','method'):
        if (context or {}).get(key) is not None:safe_context[key]=redact(str(context[key]))[:120]
    conn=sqlite3.connect(database_path)
    conn.execute('''INSERT INTO lia_error_incidents(incident_id,fundacion_id,usuario_id,module,action,http_status,error_code,error_type,technical_message_redacted,cause,solution,severity,safe_retry,auto_correctable,status,request_id,context_redacted,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(incident_id,int(tenant_id or 1),int(user_id or 0),str(module or '')[:80],str(action or '')[:100],int(status or 500),diagnosis['code'],diagnosis['type'],redact(message)[:800],diagnosis['cause'],diagnosis['solution'],diagnosis['severity'],1 if diagnosis['safe_retry'] else 0,1 if diagnosis['auto_correctable'] else 0,'OPEN',str(request_id or '')[:80],json.dumps(safe_context,ensure_ascii=False),now,now))
    conn.commit();conn.close()
    return {'incident_id':incident_id,**diagnosis,'status':'OPEN'}

def get(database_path,incident_id,tenant_id):
    conn=sqlite3.connect(database_path);conn.row_factory=sqlite3.Row
    row=conn.execute('SELECT * FROM lia_error_incidents WHERE incident_id=? AND fundacion_id=?',(str(incident_id),int(tenant_id or 1))).fetchone();conn.close()
    return dict(row) if row else None

def list_recent(database_path,tenant_id,limit=50):
    conn=sqlite3.connect(database_path);conn.row_factory=sqlite3.Row
    rows=conn.execute('SELECT incident_id,module,action,http_status,error_code,error_type,cause,solution,severity,status,created_at FROM lia_error_incidents WHERE fundacion_id=? ORDER BY id DESC LIMIT ?',(int(tenant_id or 1),max(1,min(100,int(limit or 50))))).fetchall();conn.close()
    return [dict(row) for row in rows]
