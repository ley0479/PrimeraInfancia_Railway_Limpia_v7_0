"""Registro cerrado de herramientas de lectura de LÍA."""
from __future__ import annotations
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from modules.dbapi_compat import sqlite3
from modules.calendario_inteligente.repository import CalendarioInteligenteRepository
from modules.idp_documental.repository import IDPRepository
from .error_catalog import explain
from .action_policy import require as require_action
from .action_policy import decision as action_decision
from .action_intents import propose_action
from modules.seguridad.services import ROLE_MENU_PERMISSIONS

ALLOWED_TOOLS = frozenset({'get_pending_activities_summary','get_foundation_data_summary','list_foundation_profiles','search_foundation_beneficiaries','get_platform_module_summary','get_document_processing_status','get_format_generation_status','get_structured_error','propose_platform_action'})

MODULE_DATASETS = {
    'salud-nutricion': [('valoraciones','sn_valoraciones','estado'),('alertas','sn_alertas','estado'),('actividades','sn_actividades_integrales','estado'),('canalizaciones','sn_canalizaciones','estado')],
    'talento': [('personas','master_talento_humano','estado'),('documentos','th_documentos','estado'),('formaciones','th_formaciones','estado'),('evaluaciones','th_evaluaciones','estado')],
    'planeacion-pedagogica': [('planeaciones','pp_planeaciones','estado'),('actividades','pp_actividades','estado'),('documentos','pp_documentos_generados','estado')],
    'gestion-pedagogica': [('entregables','gp_entregables','estado'),('documentos','gp_documentos','estado'),('alertas','gp_alertas','estado')],
    'centro-documental': [('documentos','doc_instancias','estado'),('evidencias','doc_evidencias',None),('revisiones','doc_revisiones','accion')],
    'reportes-gerenciales': [('reportes','rg_reportes','estado'),('informes','rg9_informes','estado'),('hallazgos','rg9_hallazgos','estado')],
    'paquete-mensual': [('paquetes','pm_paquetes','estado'),('archivos','pm_archivos','estado')],
    'familias-redes': [('expedientes','fcr_expedientes_familiares','estado'),('actividades','fcr_actividades','estado'),('compromisos','fcr_compromisos','estado'),('alertas','fcr_alertas','estado')],
}

def _foundation_summary(database_path: str, tenant_id: int) -> dict:
    """Resumen de solo lectura. El tenant siempre proviene de la sesión autenticada."""
    conn=sqlite3.connect(database_path);conn.row_factory=sqlite3.Row
    try:
        foundation=conn.execute('SELECT id,nombre FROM fundaciones WHERE id=?',(tenant_id,)).fetchone()
        profile_rows=conn.execute('''SELECT COALESCE(NULLIF(TRIM(rol),''),'SIN_ROL') AS rol,COUNT(*) AS total,
          SUM(CASE WHEN COALESCE(activo,1)=1 THEN 1 ELSE 0 END) AS activos
          FROM usuarios_app WHERE fundacion_id=? GROUP BY COALESCE(NULLIF(TRIM(rol),''),'SIN_ROL') ORDER BY rol''',(tenant_id,)).fetchall()
        children=conn.execute('''SELECT id,documento,nombre_completo,fecha_nacimiento,edad_meses,grupo_etario,
          unidad_servicio,codigo_unidad,estado
          FROM master_ninos WHERE fundacion_id=? AND COALESCE(activo,1)=1''',(tenant_id,)).fetchall()
        unit_rows=conn.execute('''SELECT COALESCE(NULLIF(TRIM(unidad_servicio),''),'SIN UNIDAD') AS unidad,
          MAX(NULLIF(TRIM(codigo_unidad),'')) AS codigo,COUNT(*) AS total
          FROM master_ninos WHERE fundacion_id=? AND COALESCE(activo,1)=1
          GROUP BY COALESCE(NULLIF(TRIM(unidad_servicio),''),'SIN UNIDAD') ORDER BY unidad''',(tenant_id,)).fetchall()
        registered_units=conn.execute('SELECT COUNT(*) AS total FROM master_unidades WHERE fundacion_id=? AND COALESCE(activo,1)=1',(tenant_id,)).fetchone()
    finally: conn.close()
    groups={}
    missing={'documento':0,'nombre_completo':0,'fecha_nacimiento':0,'grupo_etario':0,'unidad':0,'estado':0}
    for row in children:
        group=str(row['grupo_etario'] or 'SIN GRUPO ETARIO').strip() or 'SIN GRUPO ETARIO'
        groups[group]=groups.get(group,0)+1
        values={'documento':row['documento'],'nombre_completo':row['nombre_completo'],'fecha_nacimiento':row['fecha_nacimiento'],'grupo_etario':row['grupo_etario'],'unidad':row['unidad_servicio'],'estado':row['estado']}
        for key,value in values.items():
            if not str(value or '').strip():missing[key]+=1
    profiles=[{'role':row['rol'],'total':int(row['total'] or 0),'active':int(row['activos'] or 0)} for row in profile_rows]
    return {'scope':{'foundation_id':tenant_id,'foundation_name':foundation['nombre'] if foundation else None,'source':'authenticated_session','cross_foundation':False},
      'profiles':{'total':sum(x['total'] for x in profiles),'by_role':profiles,'coordinators':sum(x['total'] for x in profiles if str(x['role']).upper()=='COORDINADOR')},
      'beneficiaries':{'total':len(children),'by_age_group':[{'age_group':key,'total':value} for key,value in sorted(groups.items())]},
      'units':{'registered_active':int(registered_units['total'] or 0) if registered_units else 0,'with_beneficiaries':len(unit_rows),'items':[{'unit':row['unidad'],'code':row['codigo'],'beneficiaries':int(row['total'] or 0)} for row in unit_rows]},
      'data_quality':{'incomplete_fields':missing,'records_with_any_incomplete_field':sum(1 for row in children if any(not str(row[key] or '').strip() for key in ('documento','nombre_completo','fecha_nacimiento','grupo_etario','unidad_servicio','estado')))},
      'read_only':True}

def _foundation_profiles(database_path: str, tenant_id: int, args: dict) -> dict:
    limit=max(1,min(100,int(args.get('limit') or 50)));offset=max(0,int(args.get('offset') or 0))
    role=str(args.get('role') or '').strip().upper()
    conn=sqlite3.connect(database_path);conn.row_factory=sqlite3.Row
    try:
        where='fundacion_id=?';params=[tenant_id]
        if role:where+=' AND UPPER(rol)=?';params.append(role)
        total=conn.execute(f'SELECT COUNT(*) AS total FROM usuarios_app WHERE {where}',tuple(params)).fetchone()
        rows=conn.execute(f'''SELECT id,username,email,rol,nombre_completo,activo,estado,fecha_ultima_conexion
          FROM usuarios_app WHERE {where} ORDER BY rol,nombre_completo,username LIMIT ? OFFSET ?''',tuple([*params,limit,offset])).fetchall()
    finally:conn.close()
    return {'scope':{'foundation_id':tenant_id,'source':'authenticated_session','cross_foundation':False},'total':int(total['total'] or 0),'limit':limit,'offset':offset,
      'profiles':[dict(row) for row in rows],'read_only':True}

def _beneficiaries(database_path: str, tenant_id: int, args: dict) -> dict:
    limit=max(1,min(50,int(args.get('limit') or 20)));offset=max(0,int(args.get('offset') or 0))
    query=str(args.get('query') or '').strip()[:120];unit=str(args.get('unit') or '').strip()[:120]
    age_group=str(args.get('age_group') or '').strip()[:120];status=str(args.get('status') or '').strip()[:40]
    where=['fundacion_id=?','COALESCE(activo,1)=1'];params=[tenant_id]
    if query:
        where.append("(LOWER(COALESCE(documento,'')) LIKE LOWER(?) OR LOWER(COALESCE(nombre_completo,'')) LIKE LOWER(?))")
        params.extend([f'%{query}%',f'%{query}%'])
    if unit:where.append("LOWER(COALESCE(unidad_servicio,'')) LIKE LOWER(?)");params.append(f'%{unit}%')
    if age_group:where.append("LOWER(COALESCE(grupo_etario,'')) LIKE LOWER(?)");params.append(f'%{age_group}%')
    if status:where.append("UPPER(COALESCE(estado,''))=UPPER(?)");params.append(status)
    clause=' AND '.join(where);conn=sqlite3.connect(database_path);conn.row_factory=sqlite3.Row
    try:
        total=conn.execute(f'SELECT COUNT(*) AS total FROM master_ninos WHERE {clause}',tuple(params)).fetchone()
        rows=conn.execute(f'''SELECT id,documento,nombre_completo,fecha_nacimiento,edad_meses,grupo_etario,sexo,
          unidad_servicio,codigo_unidad,coordinador,docente,modalidad,estado
          FROM master_ninos WHERE {clause} ORDER BY nombre_completo,documento LIMIT ? OFFSET ?''',tuple([*params,limit,offset])).fetchall()
    finally:conn.close()
    return {'scope':{'foundation_id':tenant_id,'source':'authenticated_session','cross_foundation':False},
      'filters':{'query':query or None,'unit':unit or None,'age_group':age_group or None,'status':status or None},
      'total':int(total['total'] or 0),'limit':limit,'offset':offset,'beneficiaries':[dict(row) for row in rows],'read_only':True}

def _module_summary(database_path: str, tenant_id: int, args: dict) -> dict:
    module=str(args.get('module') or '').strip().lower()
    if module not in MODULE_DATASETS:raise ValueError('Módulo no reconocido para consulta operativa.')
    conn=sqlite3.connect(database_path);conn.row_factory=sqlite3.Row;datasets=[]
    try:
        for label,table,state_column in MODULE_DATASETS[module]:
            try:
                total=conn.execute(f'SELECT COUNT(*) AS total FROM {table} WHERE fundacion_id=?',(tenant_id,)).fetchone()
                states=[]
                if state_column:
                    rows=conn.execute(f'''SELECT COALESCE(NULLIF(TRIM({state_column}),''),'SIN_ESTADO') AS estado,COUNT(*) AS total
                      FROM {table} WHERE fundacion_id=? GROUP BY COALESCE(NULLIF(TRIM({state_column}),''),'SIN_ESTADO') ORDER BY estado''',(tenant_id,)).fetchall()
                    states=[{'status':row['estado'],'total':int(row['total'] or 0)} for row in rows]
                datasets.append({'name':label,'total':int(total['total'] or 0),'by_status':states})
            except Exception:
                datasets.append({'name':label,'total':0,'by_status':[],'available':False})
    finally:conn.close()
    return {'scope':{'foundation_id':tenant_id,'source':'authenticated_session','cross_foundation':False},'module':module,'datasets':datasets,'total_records':sum(x['total'] for x in datasets),'read_only':True}

def _int_arg(args, name, minimum=1):
    try: value=int(args.get(name))
    except (TypeError,ValueError): raise ValueError(f'{name} debe ser un entero válido.')
    if value<minimum: raise ValueError(f'{name} no es válido.')
    return value

def execute(tool_name: str, *, args: dict, database_path: str, tenant_id: int, user: dict) -> dict:
    if tool_name not in ALLOWED_TOOLS: raise PermissionError('Herramienta no autorizada para LÍA.')
    require_action(tool_name, str(user.get('rol') or ''))
    if tool_name=='propose_platform_action':
        command=str(args.get('command') or '').strip()
        if not command or len(command)>1000:raise ValueError('La orden de plataforma no es válida.')
        proposal=propose_action(command,screen_context=args.get('screen_context') if isinstance(args.get('screen_context'),dict) else {})
        if not proposal:raise ValueError('No identifiqué una operación segura y completa. Reformula la orden con los datos necesarios.')
        policy=action_decision(proposal.get('id'),str(user.get('rol') or ''))
        if not policy.get('allowed'):raise PermissionError(policy.get('reason'))
        target=str((proposal.get('arguments') or {}).get('module') or '')
        allowed=set(ROLE_MENU_PERMISSIONS.get(str(user.get('rol') or ''),[]))
        if target and allowed and target not in allowed:raise PermissionError('Tu rol no tiene permiso para operar ese módulo.')
        proposal.update({'risk':policy['risk'],'confirmation_type':policy['confirmation']})
        if proposal.get('confirmation_required'):
            proposal.setdefault('expires_at',(datetime.now()+timedelta(seconds=60)).isoformat(timespec='seconds'))
        message=proposal['summary']+(' Antes de continuar necesito: '+', '.join(proposal['missing'])+'.' if proposal.get('missing') else ' Revisa los datos y confirma desde la interfaz.')
        return {'proposal_only':True,'message':message,'action_proposal':proposal}
    if tool_name=='get_structured_error': return explain(str(args.get('code') or ''))
    if tool_name=='get_foundation_data_summary': return _foundation_summary(database_path,tenant_id)
    if tool_name=='list_foundation_profiles': return _foundation_profiles(database_path,tenant_id,args)
    if tool_name=='search_foundation_beneficiaries': return _beneficiaries(database_path,tenant_id,args)
    if tool_name=='get_platform_module_summary': return _module_summary(database_path,tenant_id,args)
    if tool_name=='get_pending_activities_summary':
        scope=str(args.get('scope') or 'self').strip().lower()
        if scope not in {'self','team'}: raise ValueError('scope debe ser self o team.')
        if scope=='team' and str(user.get('rol') or '').upper() not in {'SUPERADMIN','GERENTE','COORDINADOR'}:
            raise PermissionError('Tu rol no puede consultar pendientes del equipo.')
        period=str(args.get('period') or '').strip()
        if period and (len(period)!=7 or period[4]!='-' or not period[:4].isdigit() or not period[5:].isdigit() or not 1<=int(period[5:])<=12):
            raise ValueError('period debe tener el formato AAAA-MM.')
        repo=CalendarioInteligenteRepository(database_path)
        if scope=='self':
            rows=repo.list_mis_pendientes(user,limit=500)
        else:
            filters={'periodo':period} if period else {}
            if str(user.get('rol') or '').upper()=='COORDINADOR':
                coordinator=str(user.get('nombre_completo') or user.get('nombre') or user.get('username') or '').strip()
                if not coordinator: raise PermissionError('No fue posible validar el coordinador de la sesión.')
                filters['coordinador']=coordinator
            rows=repo.list_entregables(filters,limit=500)
        if period and scope=='self': rows=[x for x in rows if str(x.get('fecha_limite') or '').startswith(period)]
        today=datetime.now(ZoneInfo('America/Bogota')).date().isoformat()
        inactive={'entregado','aprobado','cancelado','no_aplica','no aplica','cerrado'}
        rows=[x for x in rows if str(x.get('estado') or 'pendiente').strip().lower() not in inactive]
        overdue=sum(1 for x in rows if x.get('fecha_limite') and str(x['fecha_limite'])<today)
        due_today=sum(1 for x in rows if str(x.get('fecha_limite') or '')==today)
        undated=sum(1 for x in rows if not x.get('fecha_limite'))
        seen=set(); duplicates=[]
        for row in rows:
            key=str(row.get('clave_unica') or '').strip()
            if key and key in seen: duplicates.append(row.get('id'))
            if key: seen.add(key)
        return {'total':len(rows),'overdue':overdue,'due_today':due_today,'upcoming':max(0,len(rows)-overdue-due_today-undated),'undated':undated,'duplicate_candidates':len(duplicates),'query':{'period':period or None,'scope':scope,'timezone':'America/Bogota','tenant_id_source':'authenticated_session'},'diagnosis':{'filters_applied':bool(period),'missing_dates':undated,'duplicate_candidate_ids':duplicates[:20]},'items':[{'id':x.get('id'),'title':x.get('titulo'),'due_date':x.get('fecha_limite'),'status':x.get('estado'),'module':x.get('modulo'),'unit':x.get('unidad'),'responsible':x.get('responsable_nombre')} for x in rows[:20]]}
    if tool_name=='get_document_processing_status':
        item=IDPRepository(database_path).get_document(_int_arg(args,'document_id'),tenant_id)
        if not item: raise LookupError('Documento no encontrado o no autorizado.')
        validations=item.get('resultados_validacion') or []
        return {'document_id':item.get('id'),'status':item.get('estado'),'stage':item.get('etapa'),'progress':item.get('progreso'),'document_type':item.get('tipo_documento'),'error_code':item.get('error_codigo'),'error_message':item.get('error_mensaje'),'validation_errors':sum(1 for x in validations if str(x.get('nivel')).upper()=='CRITICO'),'warnings':sum(1 for x in validations if str(x.get('nivel')).upper()=='ADVERTENCIA')}
    test_id=_int_arg(args,'test_id')
    conn=sqlite3.connect(database_path);conn.row_factory=sqlite3.Row
    row=conn.execute('''SELECT p.id,p.estado,p.total_usuarios,p.errores_json,p.archivo_generado,p.fecha_creacion,t.tipo
      FROM mp_pruebas p JOIN mp_plantillas t ON t.id=p.plantilla_id
      WHERE p.id=? AND COALESCE(t.fundacion_id,1)=?''',(test_id,tenant_id)).fetchone();conn.close()
    if not row: raise LookupError('Generación no encontrada o no autorizada.')
    return {'test_id':row['id'],'format_type':row['tipo'],'status':row['estado'],'total_users':row['total_usuarios'],'has_errors':bool(row['errores_json']),'file_available':bool(row['archivo_generado']),'download_ready':str(row['estado']).upper() in {'OK','COMPLETADO','GENERADO'} and bool(row['archivo_generado']),'created_at':row['fecha_creacion']}
