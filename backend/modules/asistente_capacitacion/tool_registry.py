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
from services.relacion_mes_service import consolidar_por_unidad, docente_mas_frecuente, cantidades

ALLOWED_TOOLS = frozenset({'get_pending_activities_summary','get_foundation_data_summary','get_monthly_relation_summary','list_foundation_profiles','search_foundation_beneficiaries','get_platform_module_summary','get_monthly_health_indicators','get_document_processing_status','get_format_generation_status','get_structured_error','propose_platform_action'})

MODULE_DATASETS = {
    'ambientes-protectores': [('activos','aep_activos',None),('mantenimientos','aep_mantenimientos',None)],
    'administrativo-financiero': [('presupuestos','af_presupuestos',None),('proveedores','af_proveedores',None),('compras','af_compras',None),('legalizaciones','af_legalizaciones',None)],
    'backups': [('copias de seguridad','backups_sistema',None)],
    'calidad-datos': [('análisis','cd_analisis',None),('hallazgos','cd_hallazgos',None)],
    'importaciones-universales': [('importaciones','importaciones_universales',None),('perfiles de mapeo','perfiles_mapeo_universal',None)],
    'integraciones-configuracion': [('parámetros','ic_parametros',None),('integraciones','ic_integraciones',None)],
    'motor-plantillas': [('plantillas','mp_plantillas','estado'),('pruebas','mp_pruebas','estado'),('plantillas oficiales','plantillas_oficiales',None)],
    'componente-psicosocial': [('expedientes','ps_expedientes',None),('planes','ps_planes_acompanamiento',None),('seguimientos','ps_seguimientos',None)],
    'centro-planeacion': [('reglas','cpo_reglas_operativas',None),('documentos preparados','cpo_documentos_preparados',None),('notificaciones','cpo_notificaciones',None)],
    'motor-gestion-proyecto': [('tareas','mgp_tareas',None),('productos','mgp_productos',None),('cierres mensuales','mgp_cierres_mensuales',None)],
    'expediente-operativo-uca': [('expedientes UCA','giu_expedientes_uca',None),('planes UCA','giu_planes_uca',None),('paquetes de supervisión','giu_paquetes_supervision',None)],
    'gestion-coordinador': [('asignaciones','gp_asignaciones_coordinador',None),('evidencias','gp_evidencias',None),('cumplimiento','gp_estado_cumplimiento',None)],
    'panel-comercial': [('tickets','pc_tickets_soporte',None),('alertas de pago','pc_alertas_pago',None)],
    'supervision-calidad': [('supervisiones','csc_supervisiones',None),('hallazgos','csc_hallazgos',None),('planes de mejora','csc_planes_mejora',None)],
    'calendario-inteligente': [('entregables','calendario_entregables','estado'),('actividades','calendario_actividades','estado'),('alertas','calendario_alertas','estado')],
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


def _foundation_summary_complete(database_path: str, tenant_id: int) -> dict:
    """Amplía el resumen con las fuentes maestras institucionales vigentes."""
    summary=_foundation_summary(database_path,tenant_id)
    conn=sqlite3.connect(database_path);conn.row_factory=sqlite3.Row
    try:
        def query(sql,params=()):
            try:return [dict(row) for row in conn.execute(sql,params).fetchall()]
            except Exception:return []
        versions=query('''SELECT id,estado,fecha_publicacion FROM master_versiones
          WHERE fundacion_id=? AND activa=1 ORDER BY fecha_publicacion DESC,id DESC LIMIT 1''',(tenant_id,))
        version=versions[0] if versions else {};version_id=version.get('id')
        people=query('''SELECT nombre_completo,cargo,rol_normalizado,unidad_servicio,coordinador,estado
          FROM master_talento_humano WHERE fundacion_id=? AND COALESCE(activo,1)=1
          ORDER BY coordinador,nombre_completo''',(tenant_id,))
        units=query('''SELECT nombre,codigo_unidad,coordinador,total_ninos,total_talento,modalidad
          FROM master_unidades WHERE fundacion_id=? AND COALESCE(activo,1)=1 ORDER BY nombre''',(tenant_id,))
        children_coords=query("""SELECT coordinador,unidad_servicio FROM master_ninos
          WHERE fundacion_id=? AND COALESCE(activo,1)=1 AND COALESCE(TRIM(coordinador),'')<>''""",(tenant_id,))
        app_coords=query('''SELECT COALESCE(NULLIF(TRIM(nombre_completo),''),username) AS nombre
          FROM usuarios_app WHERE fundacion_id=? AND COALESCE(activo,1)=1 AND UPPER(TRIM(rol))='COORDINADOR' ''',(tenant_id,))
        loads=query('''SELECT tipo_fuente,nombre_archivo_original,fecha_carga,total_registros,
          registros_validos,registros_error,estado FROM cargas_archivos
          WHERE fundacion_id=? ORDER BY fecha_carga DESC,id DESC''',(tenant_id,))
        movements=query('''SELECT tipo_movimiento,COUNT(*) AS total FROM master_movimientos
          WHERE fundacion_id=? AND version_id=? GROUP BY tipo_movimiento ORDER BY tipo_movimiento''',(tenant_id,version_id)) if version_id else []
    finally:conn.close()
    clean=lambda value:str(value or '').strip()
    norm=lambda value:' '.join(clean(value).upper().split())
    coordinators={}
    def add(name,source,unit=''):
        if not clean(name):return
        item=coordinators.setdefault(norm(name),{'name':clean(name),'sources':set(),'units':set(),'team':[]})
        item['sources'].add(source)
        if clean(unit):item['units'].add(clean(unit))
    for row in app_coords:add(row.get('nombre'),'usuarios_app')
    for row in children_coords:add(row.get('coordinador'),'master_ninos',row.get('unidad_servicio'))
    for row in units:add(row.get('coordinador'),'master_unidades',row.get('nombre'))
    for row in people:
        if 'COORDINADOR' in norm(row.get('rol_normalizado') or row.get('cargo')):add(row.get('nombre_completo'),'master_talento_humano',row.get('unidad_servicio'))
        add(row.get('coordinador'),'master_talento_humano',row.get('unidad_servicio'))
    for row in people:
        item=coordinators.get(norm(row.get('coordinador')))
        if item and norm(row.get('nombre_completo'))!=norm(row.get('coordinador')):
            item['team'].append({'name':row.get('nombre_completo'),'role':row.get('rol_normalizado') or row.get('cargo'),'unit':row.get('unidad_servicio'),'status':row.get('estado')})
    coordinator_items=[{'name':item['name'],'sources':sorted(item['sources']),'units':sorted(item['units']),'team':item['team']} for item in sorted(coordinators.values(),key=lambda x:norm(x['name']))]
    latest_loads={}
    for row in loads:
        source=clean(row.get('tipo_fuente')) or 'SIN_FUENTE'
        if source not in latest_loads:latest_loads[source]={'source':source,'file':row.get('nombre_archivo_original'),'loaded_at':row.get('fecha_carga'),'records':int(row.get('total_registros') or 0),'valid':int(row.get('registros_validos') or 0),'errors':int(row.get('registros_error') or 0),'status':row.get('estado')}
    summary['master_version']={'id':version_id,'status':version.get('estado'),'published_at':version.get('fecha_publicacion')}
    summary['profiles']['coordinators']=len(coordinator_items)
    summary['profiles']['coordinator_items']=coordinator_items
    summary['profiles']['interdisciplinary_team_total']=len(people)
    summary['profiles']['interdisciplinary_team']=[{'name':row.get('nombre_completo'),'role':row.get('rol_normalizado') or row.get('cargo'),'unit':row.get('unidad_servicio'),'coordinator':row.get('coordinador'),'status':row.get('estado')} for row in people[:100]]
    if units:
        summary['units']['registered_active']=len(units)
        summary['units']['items']=[{'unit':row.get('nombre'),'code':row.get('codigo_unidad'),'beneficiaries':int(row.get('total_ninos') or 0),'coordinator':row.get('coordinador'),'talent_total':int(row.get('total_talento') or 0),'modality':row.get('modalidad')} for row in units]
    summary['sources']={'active_loads':list(latest_loads.values()),'total_sources':len(latest_loads)}
    summary['movements']={'by_type':[{'type':row.get('tipo_movimiento'),'total':int(row.get('total') or 0)} for row in movements],'total':sum(int(row.get('total') or 0) for row in movements)}
    beneficiary_total=int(summary['beneficiaries'].get('total') or 0)
    declared_unit_total=sum(int(item.get('beneficiaries') or 0) for item in summary['units'].get('items') or [])
    warnings=[]
    if units and declared_unit_total!=beneficiary_total:warnings.append(f'La suma declarada en UDS ({declared_unit_total}) no coincide con los beneficiarios activos ({beneficiary_total}).')
    if not version_id:warnings.append('No existe una versión maestra activa identificable.')
    summary['consistency']={'status':'consistent' if not warnings else 'review_required','beneficiaries_active':beneficiary_total,'beneficiaries_declared_by_units':declared_unit_total,'active_units':int(summary['units'].get('registered_active') or 0),'coordinators_consolidated':len(coordinator_items),'warnings':warnings,'checked_sources':['master_ninos','master_unidades','master_talento_humano','usuarios_app','master_versiones']}
    return summary

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

def _present(value) -> bool:
    text=str(value or '').strip().lower()
    return bool(text and text not in {'no','0','false','ninguno','ninguna','sin dato','pendiente','n/a','na'})

def _health_indicators(database_path: str, tenant_id: int, args: dict) -> dict:
    limit=max(1,min(200,int(args.get('limit') or 100)));unit=str(args.get('unit') or '').strip()[:120]
    conn=sqlite3.connect(database_path);conn.row_factory=sqlite3.Row
    try:
        where='n.fundacion_id=? AND COALESCE(n.activo,1)=1';params=[tenant_id]
        if unit:where+=" AND LOWER(COALESCE(n.unidad_servicio,'')) LIKE LOWER(?)";params.append(f'%{unit}%')
        rows=conn.execute(f'''SELECT n.id,n.documento,n.tipo_documento,n.nombre_completo,n.grupo_etario,n.unidad_servicio,
          n.carne_salud,n.control_crecimiento,n.carne_crecimiento,n.perimetro_braquial,n.diagnostico_nutricional,n.estado_nutricional,n.datos_json
          FROM master_ninos n WHERE {where} ORDER BY n.nombre_completo''',tuple(params)).fetchall()
        try:
            valuations=conn.execute('''SELECT documento,diagnostico_global,clasificacion_profesional,nivel_alerta,perimetro_braquial_cm,fecha_valoracion
              FROM sn_valoraciones WHERE fundacion_id=? ORDER BY fecha_valoracion DESC,id DESC''',(tenant_id,)).fetchall()
        except Exception:valuations=[]
    finally:conn.close()
    latest={}
    for row in valuations:
        doc=str(row['documento'] or '').strip()
        if doc and doc not in latest:latest[doc]=dict(row)
    counts={'total':len(rows),'carne_salud':0,'crecimiento_desarrollo':0,'registro_civil':0,'perimetro_braquial':0,'gestantes':0,'gestantes_control_prenatal':0,'sobrepeso':0,'desnutricion':0,'riesgo_desnutricion':0}
    annex=[]
    for row in rows:
        item=dict(row);valuation=latest.get(str(item.get('documento') or '').strip(),{})
        try:data=__import__('json').loads(item.get('datos_json') or '{}')
        except Exception:data={}
        flat=' '.join(f'{k}:{v}' for k,v in data.items()).lower() if isinstance(data,dict) else ''
        if _present(item.get('carne_salud')):counts['carne_salud']+=1
        if _present(item.get('control_crecimiento')) or _present(item.get('carne_crecimiento')):counts['crecimiento_desarrollo']+=1
        if 'registro' in str(item.get('tipo_documento') or '').lower() or str(item.get('tipo_documento') or '').strip().upper()=='RC':counts['registro_civil']+=1
        arm=valuation.get('perimetro_braquial_cm') or item.get('perimetro_braquial')
        if _present(arm):counts['perimetro_braquial']+=1
        pregnant='gestante' in str(item.get('grupo_etario') or '').lower()
        if pregnant:
            counts['gestantes']+=1
            if 'control_prenatal' in flat and not any(x in flat for x in ('control_prenatal:no','control_prenatal: no','control_prenatal:false')):counts['gestantes_control_prenatal']+=1
        diagnosis=str(valuation.get('clasificacion_profesional') or valuation.get('diagnostico_global') or item.get('diagnostico_nutricional') or item.get('estado_nutricional') or 'SIN CLASIFICAR').strip()
        norm=diagnosis.lower()
        category=None
        if 'sobrepeso' in norm or 'obesidad' in norm:category='SOBREPESO';counts['sobrepeso']+=1
        elif 'riesgo' in norm and 'desnut' in norm:category='RIESGO_DESNUTRICION';counts['riesgo_desnutricion']+=1
        elif 'desnut' in norm:category='DESNUTRICION';counts['desnutricion']+=1
        if category and len(annex)<limit:annex.append({'id':item.get('id'),'document':item.get('documento'),'name':item.get('nombre_completo'),'unit':item.get('unidad_servicio'),'age_group':item.get('grupo_etario'),'category':category,'nutritional_status':diagnosis,'alert_level':valuation.get('nivel_alerta'),'arm_circumference_cm':arm})
    return {'scope':{'foundation_id':tenant_id,'source':'authenticated_session','cross_foundation':False},'unit':unit or None,'indicators':counts,'nutritional_annex':annex,'annex_limit':limit,'read_only':True}

def _int_arg(args, name, minimum=1):
    try: value=int(args.get(name))
    except (TypeError,ValueError): raise ValueError(f'{name} debe ser un entero válido.')
    if value<minimum: raise ValueError(f'{name} no es válido.')
    return value

def _monthly_relation(database_path: str, tenant_id: int, args: dict) -> dict:
    period=str(args.get('period') or '').strip()
    if not period:
        try: period=f"{int(args.get('year')):04d}-{int(args.get('month')):02d}"
        except (TypeError,ValueError): period=datetime.now(ZoneInfo('America/Bogota')).strftime('%Y-%m')
    if len(period)!=7 or period[4]!='-' or not period[:4].isdigit() or not period[5:].isdigit() or not 1<=int(period[5:])<=12:
        raise ValueError('period debe tener el formato AAAA-MM.')
    year,month=int(period[:4]),int(period[5:])
    conn=sqlite3.connect(database_path);conn.row_factory=sqlite3.Row
    try:
        rows=conn.execute('''SELECT unidad_servicio AS unidad,grupo_etario,edad_meses,fecha_nacimiento,
          estado,docente,datos_json FROM master_ninos
          WHERE fundacion_id=? AND COALESCE(activo,1)=1''',(tenant_id,)).fetchall()
    finally:conn.close()
    grouped=consolidar_por_unidad((dict(row) for row in rows),year,month)
    columns=['UNIDAD DE ATENCIÓN','DOCENTE','GESTANTES','MENORES 6 MESES','6 A 11 MESES','1 A 2 AÑOS 11 MESES','3 A 5 AÑOS 11 MESES','SIN CLASIFICAR / REVISAR','TOTAL USUARIOS','HUEVOS PARA GRUPOS DE 30','HUEVOS PARA 6 A 11 (15)','TOTAL HUEVOS (UNIDADES)','CUBETAS DE 30','PANALES COMPLETOS (7 CUBETAS)','CUBETAS SUELTAS','GESTANTES/LACTANTES CON DOBLE VERDURA','TOTAL VERDURAS','OLLA COMUNITARIA','BIENESTARINA']
    output=[]
    for unit in sorted(grouped):
        item=grouped[unit];amounts=cantidades(item)
        output.append([unit,docente_mas_frecuente(item) or 'SIN DOCENTE ASIGNADO',item['gestantes'],item['menores_6'],item['seis_11'],item['uno_2'],item['tres_5'],item['sin_clasificar'],amounts['total'],amounts['huevos_30'],amounts['huevos_15'],amounts['total_huevos'],amounts['cubetas_30'],amounts['panales_7'],amounts['cubetas_sueltas'],item['verduras_dobles'],amounts['verduras'],amounts['olla_comunitaria'],amounts['bienestarina']])
    numeric_totals=[sum(int(row[index] or 0) for row in output) for index in range(2,len(columns))]
    total_row=['TOTAL GENERAL','',*numeric_totals]
    metrics=[{'label':'Unidades de atención','value':len(output)},{'label':'Total usuarios','value':numeric_totals[6] if numeric_totals else 0},{'label':'Total huevos','value':numeric_totals[9] if numeric_totals else 0},{'label':'Cubetas de 30','value':numeric_totals[10] if numeric_totals else 0},{'label':'Panales completos','value':numeric_totals[11] if numeric_totals else 0},{'label':'Total verduras','value':numeric_totals[14] if numeric_totals else 0},{'label':'Ollas comunitarias','value':numeric_totals[15] if numeric_totals else 0},{'label':'Bienestarina','value':numeric_totals[16] if numeric_totals else 0}]
    return {'scope':{'foundation_id':tenant_id,'source':'authenticated_session','cross_foundation':False},'period':period,'title':f'RELACIÓN DEL MES {period}','rule':'30 huevos por usuario; de 6 a 11 meses recibe 15. Una cubeta contiene 30 huevos y un panal contiene 7 cubetas.','metrics':metrics,'columns':columns,'relation_rows':output,'total_row':total_row,'read_only':True}

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
    if tool_name=='get_foundation_data_summary': return _foundation_summary_complete(database_path,tenant_id)
    if tool_name=='get_monthly_relation_summary': return _monthly_relation(database_path,tenant_id,args)
    if tool_name=='list_foundation_profiles': return _foundation_profiles(database_path,tenant_id,args)
    if tool_name=='search_foundation_beneficiaries': return _beneficiaries(database_path,tenant_id,args)
    if tool_name=='get_platform_module_summary':
        module=str(args.get('module') or '').strip().lower();allowed=set(ROLE_MENU_PERMISSIONS.get(str(user.get('rol') or ''),[]))
        if allowed and module not in allowed:raise PermissionError('Tu rol no tiene permiso para consultar ese módulo.')
        return _module_summary(database_path,tenant_id,args)
    if tool_name=='get_monthly_health_indicators': return _health_indicators(database_path,tenant_id,args)
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
