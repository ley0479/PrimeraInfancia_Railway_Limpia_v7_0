"""Centro transversal de incidentes explicables por LIAM."""
from __future__ import annotations

from datetime import datetime,timedelta
import json, re, uuid
from modules.dbapi_compat import sqlite3
from .error_catalog import explain
from .privacy_service import redact

TYPE_BY_STATUS = {400:'error_usuario',401:'error_permisos',403:'error_permisos',404:'error_datos',409:'error_integridad',413:'error_archivo',415:'error_archivo',422:'error_datos',429:'error_configuracion',502:'error_integracion',503:'error_backend',504:'error_red'}

ACTION_LABELS = {
    'review_detected_columns': 'Revisa las columnas detectadas en el archivo.',
    'open_mapping': 'Abre el mapeo, relaciona los campos obligatorios y vuelve a validar.',
    'retry': 'Comprueba la conexión y vuelve a intentarlo una sola vez.',
    'check_status': 'Consulta el estado del proceso antes de generar nuevamente.',
}


def _plain_server_diagnosis(text: str, kind: str) -> tuple[str, str, bool]:
    """Traduce fallos técnicos frecuentes sin exponer rutas, SQL ni excepciones."""
    if any(token in text for token in ('permission denied', 'read-only file system', 'access is denied', 'acceso denegado')):
        return (
            'La plataforma no pudo guardar el archivo o crear la carpeta que necesitaba.',
            'No vuelvas a cargar la información todavía. Conserva la referencia y solicita que revisen el almacenamiento de la plataforma.',
            False,
        )
    if any(token in text for token in ('no space left', 'disk full', 'espacio insuficiente')):
        return (
            'El espacio disponible para guardar archivos se agotó.',
            'Libera espacio o solicita ampliar el almacenamiento y luego repite la operación.',
            True,
        )
    if any(token in text for token in ('no such table', 'undefined table', 'relation ', 'database is not initialized')):
        return (
            'La base de datos necesaria para esta función todavía no está preparada.',
            'Carga o publica la Base Maestra correspondiente. Si ya lo hiciste, conserva la referencia y solicita revisar la actualización de la base.',
            False,
        )
    if any(token in text for token in ('no such column', 'undefined column', 'column ') ):
        return (
            'La información cargada no contiene una columna que esta función necesita.',
            'Revisa el mapeo y confirma que estén relacionados los campos obligatorios antes de procesar nuevamente.',
            True,
        )
    if any(token in text for token in ('template', 'plantilla', 'no such file', 'file not found')):
        return (
            'No se encontró la plantilla o el archivo necesario para completar la operación.',
            'Carga la plantilla oficial del módulo o selecciona nuevamente el archivo correcto y vuelve a intentarlo.',
            True,
        )
    if any(token in text for token in ('timeout', 'timed out', 'demasiado tiempo', 'worker timeout')):
        return (
            'El proceso no alcanzó a terminar dentro del tiempo disponible.',
            'No lo inicies varias veces. Revisa primero si el resultado ya apareció; si no, usa una base más liviana o procesa menos unidades.',
            True,
        )
    if any(token in text for token in ('connection', 'network', 'failed to fetch', 'conexión', 'conexion')):
        return (
            'Se interrumpió la comunicación con el servidor o con la base de datos.',
            'Comprueba tu conexión, espera unos segundos y vuelve a intentarlo una sola vez.',
            True,
        )
    if kind == 'error_base_datos':
        return (
            'La plataforma no pudo consultar o guardar la información en la base de datos.',
            'No repitas cambios hasta verificar el resultado. Conserva la referencia y solicita revisión de la base de datos.',
            False,
        )
    return (
        'La plataforma encontró un problema inesperado y no pudo terminar esta acción.',
        'No repitas la operación varias veces. Conserva la referencia mostrada para que soporte pueda identificar la causa exacta.',
        False,
    )

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
        cause=known['message'];solution=' '.join(ACTION_LABELS.get(action, action) for action in (known.get('actions') or [])) or 'Revisa los datos indicados e intenta nuevamente.'
    else:
        if int(status or 500) >= 500:
            cause, solution, safe_retry = _plain_server_diagnosis(text, kind)
        else:
            cause=redact(message)[:500] or 'Falta información para completar la acción.'
            solutions={'error_permisos':'Inicia sesión nuevamente y verifica que tu rol tenga permiso para esta unidad.','error_usuario':'Corrige los campos señalados y vuelve a intentarlo.','error_datos':'Comprueba los datos obligatorios, la unidad y el periodo seleccionado.','error_archivo':'Selecciona el archivo correspondiente a este módulo y verifica su formato.','error_plantilla':'Carga una plantilla oficial vigente con la estructura esperada.','error_red':'Comprueba la conexión y vuelve a intentarlo una sola vez.','error_integridad':'Revisa si el registro ya existe o entra en conflicto con información publicada.'}
            solution=solutions.get(kind,'Revisa los datos mostrados y vuelve a intentarlo.')
            safe_retry=kind in {'error_red','error_usuario','error_datos','error_archivo','error_plantilla'}
    return {'code':key,'type':kind,'cause':cause,'solution':solution,'severity':'high' if int(status or 500)>=500 else 'medium','safe_retry':safe_retry if known.get('confidence')!='confirmed' else bool(known.get('retryable')),'auto_correctable':False}

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

def get_authorized(database_path,incident_id,tenant_id,user_id,role):
    """Devuelve solamente el diagnóstico funcional permitido para la sesión."""
    normalized=str(role or '').strip().upper()
    where='incident_id=? AND fundacion_id=?'
    params=[str(incident_id),int(tenant_id or 1)]
    if normalized not in {'SUPERADMIN','GERENTE'}:
        where+=' AND usuario_id=?';params.append(int(user_id or 0))
    conn=sqlite3.connect(database_path);conn.row_factory=sqlite3.Row
    row=conn.execute(f'''SELECT incident_id,module,action,http_status,error_code,error_type,cause,solution,severity,safe_retry,auto_correctable,status,created_at,updated_at
        FROM lia_error_incidents WHERE {where}''',tuple(params)).fetchone();conn.close()
    if not row:return None
    return {**dict(row),'sanitized':True,'technical_details_included':False,'scope':'foundation' if normalized in {'SUPERADMIN','GERENTE'} else 'own_user'}

def list_recent(database_path,tenant_id,limit=50):
    conn=sqlite3.connect(database_path);conn.row_factory=sqlite3.Row
    rows=conn.execute('SELECT incident_id,module,action,http_status,error_code,error_type,cause,solution,severity,status,created_at FROM lia_error_incidents WHERE fundacion_id=? ORDER BY id DESC LIMIT ?',(int(tenant_id or 1),max(1,min(100,int(limit or 50))))).fetchall();conn.close()
    return [dict(row) for row in rows]

TRANSITIONS={'OPEN':{'IN_ANALYSIS','CLOSED'},'IN_ANALYSIS':{'IN_PROGRESS','RESOLVED','CLOSED'},'IN_PROGRESS':{'RESOLVED','CLOSED'},'RESOLVED':{'CLOSED','IN_ANALYSIS'},'CLOSED':{'IN_ANALYSIS'}}

def create_transition_proposal(database_path,ctx,incident_id,target_status,resolution=''):
    role=str(ctx.get('rol') or '').upper()
    if role not in {'SUPERADMIN','GERENTE'}:raise PermissionError('Tu rol no puede cambiar el estado de incidencias.')
    incident=str(incident_id or '').strip().upper();target=str(target_status or '').strip().upper();resolution=redact(str(resolution or '').strip())[:500]
    conn=sqlite3.connect(database_path);conn.row_factory=sqlite3.Row
    row=conn.execute('SELECT incident_id,status,error_code,solution FROM lia_error_incidents WHERE incident_id=? AND fundacion_id=?',(incident,int(ctx.get('fundacion_id') or 1))).fetchone()
    if not row:conn.close();raise LookupError('No encontré esa incidencia dentro de la fundación activa.')
    before=dict(row);current=str(before['status'] or '').upper()
    if target not in TRANSITIONS.get(current,set()):conn.close();raise ValueError(f'No está permitida la transición de {current} a {target}.')
    if target in {'RESOLVED','CLOSED'} and not resolution:conn.close();raise ValueError('Indica una solución general antes de resolver o cerrar la incidencia.')
    args={'incident_id':incident,'target_status':target,'resolution':resolution};proposal_id=uuid.uuid4().hex;now=datetime.now();expires=now+timedelta(seconds=60)
    conn.execute('''INSERT INTO lia_action_proposals(proposal_id,usuario_id,action_name,target_fundacion_id,arguments_json,before_json,status,expires_at,created_at) VALUES(?,?,?,?,?,?,?,?,?)''',(proposal_id,int(ctx.get('usuario_id') or 0),'transition_incident',int(ctx.get('fundacion_id') or 1),json.dumps(args,ensure_ascii=False),json.dumps(before,ensure_ascii=False,default=str),'PENDING',expires.isoformat(timespec='seconds'),now.isoformat(timespec='seconds')));conn.commit();conn.close()
    return {'id':'transition_incident','proposal_id':proposal_id,'summary':f'Cambiar {incident} de {current} a {target}.','label':'Confirmar cambio de estado','confirmation_required':True,'confirmation_type':'explicit','risk':'modification','server_confirmation':True,'expires_at':expires.isoformat(timespec='seconds')}

def confirm_transition(database_path,proposal_id,ctx):
    role=str(ctx.get('rol') or '').upper()
    if role not in {'SUPERADMIN','GERENTE'}:raise PermissionError('Tu rol no puede cambiar el estado de incidencias.')
    conn=sqlite3.connect(database_path);conn.row_factory=sqlite3.Row;row=conn.execute('SELECT * FROM lia_action_proposals WHERE proposal_id=?',(str(proposal_id),)).fetchone()
    if not row:conn.close();raise LookupError('La propuesta no existe.')
    row=dict(row)
    if row['action_name']!='transition_incident':conn.close();raise ValueError('La propuesta no corresponde a una incidencia.')
    if int(row['usuario_id'])!=int(ctx.get('usuario_id') or 0) or int(row['target_fundacion_id'])!=int(ctx.get('fundacion_id') or 1):conn.close();raise PermissionError('La propuesta pertenece a otra sesión o fundación.')
    if row['status']!='PENDING' or datetime.fromisoformat(row['expires_at'])<datetime.now():conn.close();raise ValueError('La confirmación venció o ya fue utilizada.')
    args=json.loads(row['arguments_json']);before=json.loads(row['before_json']);current=str(before.get('status') or '').upper();target=str(args.get('target_status') or '').upper()
    if target not in TRANSITIONS.get(current,set()):conn.close();raise ValueError('La transición dejó de ser válida.')
    updated=conn.execute("UPDATE lia_action_proposals SET status='EXECUTING' WHERE proposal_id=? AND status='PENDING'",(proposal_id,))
    if int(getattr(updated,'rowcount',0) or 0)!=1:conn.rollback();conn.close();raise ValueError('La propuesta ya está siendo procesada.')
    now=datetime.now().isoformat(timespec='seconds');resolution=str(args.get('resolution') or '')
    changed=conn.execute('''UPDATE lia_error_incidents SET status=?,solution=CASE WHEN ?<>'' THEN ? ELSE solution END,updated_at=? WHERE incident_id=? AND fundacion_id=? AND UPPER(status)=?''',(target,resolution,resolution,now,args['incident_id'],int(ctx.get('fundacion_id') or 1),current))
    if int(getattr(changed,'rowcount',0) or 0)!=1:conn.rollback();conn.close();raise ValueError('La incidencia cambió desde que se preparó la propuesta.')
    after={'incident_id':args['incident_id'],'status':target,'error_code':before.get('error_code'),'solution':resolution or before.get('solution')}
    conn.execute("UPDATE lia_action_proposals SET status='COMPLETED',after_json=?,completed_at=? WHERE proposal_id=?",(json.dumps(after,ensure_ascii=False),now,proposal_id));conn.commit();conn.close()
    return {'message':f"La incidencia {args['incident_id']} quedó en estado {target}.",'incident':after}
