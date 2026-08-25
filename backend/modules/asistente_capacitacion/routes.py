from __future__ import annotations

from datetime import datetime
from flask import Blueprint, jsonify, request, g
from modules.dbapi_compat import sqlite3
from modules.seguridad.services import ROLE_MENU_PERMISSIONS, get_request_user_context
from .guides import DEFAULT_GUIDE, GUIDES
from .schema import SCHEMA_SQL
from .config import public_flags, public_liam_flags, public_elian_flags
from .elian_module_registry import authorized_modules
from .assistant_service import respond
from .platform_profile import get_platform_profile
from .tool_registry import ALLOWED_TOOLS, execute
from .rate_limit import allow
from .provider_adapter import provider_status
import json, uuid


def register_asistente_capacitacion(app, database_path: str) -> None:
    def connect():
        conn = sqlite3.connect(database_path); conn.row_factory = sqlite3.Row; return conn

    conn = connect(); conn.executescript(SCHEMA_SQL); conn.commit(); conn.close()
    bp = Blueprint('asistente_capacitacion', __name__, url_prefix='/api/asistente-capacitacion')

    def audit_lia(ctx, event_type, *, module=None, tool=None, success=True, request_id=None, metadata=None):
        conn=None
        try:
            conn=connect();conn.execute('''INSERT INTO lia_audit_events
              (fundacion_id,usuario_id,event_type,modulo,tool_name,success,request_id,metadata_redacted,created_at)
              VALUES(?,?,?,?,?,?,?,?,?)''',(int(ctx.get('fundacion_id') or 1),int(ctx.get('usuario_id') or 0),event_type,module,tool,1 if success else 0,request_id,json.dumps(metadata or {},ensure_ascii=False),datetime.now().isoformat(timespec='seconds')));conn.commit()
        except Exception as exc:
            if conn:
                try: conn.rollback()
                except Exception: pass
            app.logger.warning('LÍA continúa sin auditoría auxiliar: %s', type(exc).__name__)
        finally:
            if conn:
                try: conn.close()
                except Exception: pass

    def limited(ctx):
        flags=public_flags();key=f"{ctx.get('fundacion_id')}:{ctx.get('usuario_id')}"
        return not allow(key,flags['rate_limit_per_minute'])

    @bp.get('/config')
    def config_publica():
        return jsonify({'lia': public_flags(), 'liam': public_liam_flags(), 'elian': public_elian_flags(), 'platform_profile': get_platform_profile()}), 200

    @bp.get('/contexto')
    def contexto():
        if not public_flags()['enabled']:
            return jsonify({'error':'LÍA está desactivada.'}), 404
        ctx = get_request_user_context(); modulo = str(request.args.get('modulo') or 'dashboard').strip()
        allowed = set(ROLE_MENU_PERMISSIONS.get(str(ctx.get('rol') or ''), []))
        if allowed and modulo not in allowed: return jsonify({'error':'Módulo no autorizado para el rol actual.'}), 403
        guide = dict(GUIDES.get(modulo, DEFAULT_GUIDE)); guide['modulo'] = modulo
        guide['tour_steps']=[{'help_id':f'{modulo}.screen','message':guide.get('resumen') or ''}]+[{'help_id':f'{modulo}.primary-action','message':step} for step in guide.get('pasos',[])]
        conn = connect(); row = conn.execute('SELECT * FROM ayuda_progreso_usuario WHERE fundacion_id=? AND usuario_id=? AND modulo=?',(ctx.get('fundacion_id') or 1,ctx.get('usuario_id'),modulo)).fetchone(); conn.close()
        return jsonify({'guia':guide,'rol':ctx.get('rol'),'progreso':dict(row) if row else None,'solo_orientacion':True}), 200

    @bp.get('/presentation')
    def presentation():
        if not public_flags()['enabled']: return jsonify({'error':'LÍA está desactivada.'}),404
        ctx=get_request_user_context();allowed=list(ROLE_MENU_PERMISSIONS.get(str(ctx.get('rol') or ''),[]))
        modules=[]
        for key in allowed:
            item=GUIDES.get(key)
            if item: modules.append({'module':key,'title':item.get('titulo'),'purpose':item.get('proposito') or item.get('resumen')})
        profile=get_platform_profile();audit_lia(ctx,'PLATFORM_PRESENTATION_OPENED',module='dashboard',metadata={'modules':len(modules)})
        workflow=['Confirmar sesión, fundación y periodo.','Actualizar las fuentes autorizadas en Base Maestra.','Revisar unidades, participantes y equipo humano.','Consultar calendario, actividades y entregables.','Trabajar en el módulo correspondiente según el rol.','Cargar evidencias o generar borradores.','Confirmar el resultado y atender revisiones o devoluciones.']
        return jsonify({'profile':profile,'modules':modules,'role':ctx.get('rol'),'total':len(modules),'workflow':workflow}),200

    @bp.get('/elian/platform-tour')
    def elian_platform_tour():
        if not public_elian_flags()['enabled'] or not public_elian_flags()['platform_tour_enabled']:
            return jsonify({'error':'El recorrido general de ELIAN está desactivado.'}),404
        ctx=get_request_user_context();fid=int(ctx.get('fundacion_id') or 1);uid=int(ctx.get('usuario_id') or 0)
        allowed=ROLE_MENU_PERMISSIONS.get(str(ctx.get('rol') or ''),[])
        modules=authorized_modules(allowed)
        conn=connect();row=conn.execute('SELECT * FROM elian_platform_tour_progress WHERE fundacion_id=? AND usuario_id=? AND tour_id=?',(fid,uid,'platform-overview')).fetchone();conn.close()
        progress=dict(row) if row else None
        if progress:
            for field in ('completed_modules_json','skipped_modules_json','pending_modules_json'):
                progress[field[:-5]]=json.loads(progress.pop(field) or '[]')
        audit_lia(ctx,'ELIAN_PLATFORM_TOUR_OPENED',module='dashboard',metadata={'modules':len(modules)})
        return jsonify({'tour_id':'platform-overview','tour_version':1,'profile':get_platform_profile(),'role':ctx.get('rol'),'modules':modules,'total':len(modules),'progress':progress,'navigation_policy':'registered_routes_only'}),200

    @bp.route('/elian/platform-tour/progress',methods=['GET','PUT'])
    def elian_platform_tour_progress():
        if not public_elian_flags()['enabled']: return jsonify({'error':'ELIAN está desactivado.'}),404
        ctx=get_request_user_context();fid=int(ctx.get('fundacion_id') or 1);uid=int(ctx.get('usuario_id') or 0);tour_id='platform-overview';conn=connect()
        if request.method=='GET':
            row=conn.execute('SELECT * FROM elian_platform_tour_progress WHERE fundacion_id=? AND usuario_id=? AND tour_id=?',(fid,uid,tour_id)).fetchone();conn.close()
            if not row:return jsonify({'progress':None}),200
            value=dict(row)
            for field in ('completed_modules_json','skipped_modules_json','pending_modules_json'):value[field[:-5]]=json.loads(value.pop(field) or '[]')
            return jsonify({'progress':value}),200
        data=request.get_json(silent=True) or {};allowed_ids=[m['module_id'] for m in authorized_modules(ROLE_MENU_PERMISSIONS.get(str(ctx.get('rol') or ''),[]))];allowed_set=set(allowed_ids)
        status=str(data.get('status') or 'in_progress');mode=str(data.get('mode') or 'automatic')
        if status not in {'not_started','in_progress','paused','completed','cancelled','outdated','failed'} or mode not in {'automatic','interactive','pending','module'}:
            conn.close();return jsonify({'error':'Estado o modo de recorrido no válido.'}),422
        current=str(data.get('current_module_id') or '')
        if current and current not in allowed_set:conn.close();return jsonify({'error':'Módulo no autorizado para el recorrido.'}),403
        def clean_list(name):
            values=data.get(name) or []
            return [item for item in dict.fromkeys(str(v) for v in values) if item in allowed_set]
        completed=clean_list('completed_modules');skipped=clean_list('skipped_modules');pending=[m for m in allowed_ids if m not in set(completed+skipped)]
        now=datetime.now().isoformat(timespec='seconds');completed_at=now if status=='completed' else None
        conn.execute('''INSERT INTO elian_platform_tour_progress(fundacion_id,usuario_id,tour_id,tour_version,current_module_id,current_step,completed_modules_json,skipped_modules_json,pending_modules_json,mode,status,created_at,updated_at,completed_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(fundacion_id,usuario_id,tour_id) DO UPDATE SET tour_version=excluded.tour_version,current_module_id=excluded.current_module_id,current_step=excluded.current_step,completed_modules_json=excluded.completed_modules_json,skipped_modules_json=excluded.skipped_modules_json,pending_modules_json=excluded.pending_modules_json,mode=excluded.mode,status=excluded.status,updated_at=excluded.updated_at,completed_at=excluded.completed_at''',(fid,uid,tour_id,1,current,max(0,int(data.get('current_step') or 0)),json.dumps(completed),json.dumps(skipped),json.dumps(pending),mode,status,now,now,completed_at));conn.commit();conn.close()
        audit_lia(ctx,'ELIAN_PLATFORM_TOUR_PROGRESS',module=current or 'dashboard',metadata={'status':status,'completed':len(completed),'skipped':len(skipped)})
        return jsonify({'message':'Progreso de ELIAN actualizado.','progress':{'tour_id':tour_id,'tour_version':1,'current_module_id':current,'current_step':max(0,int(data.get('current_step') or 0)),'completed_modules':completed,'skipped_modules':skipped,'pending_modules':pending,'mode':mode,'status':status}}),200

    @bp.route('/elian/visual-config',methods=['GET','PUT'])
    def elian_visual_config():
        ctx=get_request_user_context();fid=int(ctx.get('fundacion_id') or 1);uid=int(ctx.get('usuario_id') or 0)
        variants={
            'afro_colombian_institutional':{'label':'Afrocolombiano institucional','assets':{'male':'./assets/lia/elian-afro-institutional-male-v1.png','female':'./assets/lia/elian-afro-institutional-female-v1.png'},'ready_genders':['male','female']},
            'afro_colombian_technological':{'label':'Afrocolombiano tecnológico','assets':{'male':'./assets/lia/elian-afro-institutional-male-v1.png','female':'./assets/lia/elian-afro-institutional-female-v1.png'},'ready_genders':[]},
            'afro_colombian_educational':{'label':'Afrocolombiano educativo','assets':{'male':'./assets/lia/elian-afro-institutional-male-v1.png','female':'./assets/lia/elian-afro-institutional-female-v1.png'},'ready_genders':[]},
        }
        defaults={'assistant_name':'ELIAN','avatar_gender':'male','avatar_variant':'afro_colombian_institutional','skin_tone':'dark','hair_style':'short_coily','clothing_style':'institutional_vest','primary_color':'#123A63','secondary_color':'#16C6D8','voice_gender':'male','voice_speed':.95,'headset_enabled':1,'tablet_enabled':1,'hologram_enabled':1,'animation_enabled':1,'walk_enabled':0,'lip_sync_enabled':0,'motion_level':'light','avatar_asset_path':variants['afro_colombian_institutional']['assets']['male']}
        conn=connect();row=conn.execute('SELECT * FROM elian_visual_configuration WHERE fundacion_id=?',(fid,)).fetchone()
        if request.method=='GET':
            conn.close();config={**defaults,**(dict(row) if row else {})};selected=variants.get(config['avatar_variant'],variants['afro_colombian_institutional']);ready=config['avatar_gender'] in selected['ready_genders'];return jsonify({'configuration':config,'variants':variants,'genders':['male','female'],'editable':str(ctx.get('rol') or '') in {'SUPERADMIN','GERENTE'},'fallback_active':not ready}),200
        if str(ctx.get('rol') or '') not in {'SUPERADMIN','GERENTE'}:conn.close();return jsonify({'error':'Solo un administrador autorizado puede cambiar la apariencia global.'}),403
        data=request.get_json(silent=True) or {};gender=str(data.get('avatar_gender') or defaults['avatar_gender']);variant=str(data.get('avatar_variant') or defaults['avatar_variant']);motion=str(data.get('motion_level') or defaults['motion_level'])
        if gender not in {'male','female'} or variant not in variants or motion not in {'full','light','reduced'}:conn.close();return jsonify({'error':'La variante visual solicitada no está registrada.'}),422
        asset=variants[variant]['assets'][gender];asset_ready=gender in variants[variant]['ready_genders'];name=str(data.get('assistant_name') or 'ELIAN').strip()[:40] or 'ELIAN';now=datetime.now().isoformat(timespec='seconds')
        values=(name,gender,variant,str(data.get('skin_tone') or 'dark')[:30],str(data.get('hair_style') or 'short_coily')[:40],str(data.get('clothing_style') or 'institutional_vest')[:40],str(data.get('primary_color') or '#123A63')[:16],str(data.get('secondary_color') or '#16C6D8')[:16],str(data.get('voice_gender') or gender)[:12],max(.6,min(1.5,float(data.get('voice_speed') or .95))),1 if data.get('headset_enabled',True) else 0,1 if data.get('tablet_enabled',True) else 0,1 if data.get('hologram_enabled',True) else 0,1 if data.get('animation_enabled',True) else 0,1 if data.get('walk_enabled',False) else 0,1 if data.get('lip_sync_enabled',False) else 0,motion,asset)
        conn.execute('''INSERT INTO elian_visual_configuration(fundacion_id,assistant_name,avatar_gender,avatar_variant,skin_tone,hair_style,clothing_style,primary_color,secondary_color,voice_gender,voice_speed,headset_enabled,tablet_enabled,hologram_enabled,animation_enabled,walk_enabled,lip_sync_enabled,motion_level,avatar_asset_path,updated_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(fundacion_id) DO UPDATE SET assistant_name=excluded.assistant_name,avatar_gender=excluded.avatar_gender,avatar_variant=excluded.avatar_variant,skin_tone=excluded.skin_tone,hair_style=excluded.hair_style,clothing_style=excluded.clothing_style,primary_color=excluded.primary_color,secondary_color=excluded.secondary_color,voice_gender=excluded.voice_gender,voice_speed=excluded.voice_speed,headset_enabled=excluded.headset_enabled,tablet_enabled=excluded.tablet_enabled,hologram_enabled=excluded.hologram_enabled,animation_enabled=excluded.animation_enabled,walk_enabled=excluded.walk_enabled,lip_sync_enabled=excluded.lip_sync_enabled,motion_level=excluded.motion_level,avatar_asset_path=excluded.avatar_asset_path,updated_by=excluded.updated_by,updated_at=excluded.updated_at''',(fid,*values,uid,now,now));conn.commit();conn.close();audit_lia(ctx,'ELIAN_VISUAL_CONFIGURATION_UPDATED',module='administracion',metadata={'variant':variant,'gender':gender,'asset_ready':asset_ready})
        return jsonify({'message':'Configuración visual de ELIAN actualizada.','configuration':{'assistant_name':name,'avatar_gender':gender,'avatar_variant':variant,'motion_level':motion,'avatar_asset_path':asset},'asset_ready':asset_ready}),200

    @bp.post('/progreso')
    def progreso():
        if not public_flags()['enabled']:
            return jsonify({'error':'LÍA está desactivada.'}), 404
        ctx=get_request_user_context(); data=request.get_json(silent=True) or {}; modulo=str(data.get('modulo') or '').strip()
        if not modulo: return jsonify({'error':'Módulo requerido.'}),400
        allowed=set(ROLE_MENU_PERMISSIONS.get(str(ctx.get('rol') or ''), []))
        if allowed and modulo not in allowed: return jsonify({'error':'Módulo no autorizado.'}),403
        now=datetime.now().isoformat(timespec='seconds'); completed=1 if data.get('recorrido_completado') else 0; skipped=1 if data.get('recorrido_omitido') else 0
        conn=connect(); conn.execute("""INSERT INTO ayuda_progreso_usuario
        (fundacion_id,usuario_id,modulo,recorrido_completado,recorrido_omitido,veces_abierto,ultima_apertura,fecha_creacion,fecha_actualizacion)
        VALUES (?,?,?,?,?,1,?,?,?) ON CONFLICT(fundacion_id,usuario_id,modulo) DO UPDATE SET
        recorrido_completado=CASE WHEN excluded.recorrido_completado=1 THEN 1 ELSE ayuda_progreso_usuario.recorrido_completado END,
        recorrido_omitido=CASE WHEN excluded.recorrido_omitido=1 THEN 1 ELSE ayuda_progreso_usuario.recorrido_omitido END,
        veces_abierto=ayuda_progreso_usuario.veces_abierto+1,ultima_apertura=excluded.ultima_apertura,fecha_actualizacion=excluded.fecha_actualizacion""",
        (ctx.get('fundacion_id') or 1,ctx.get('usuario_id'),modulo,completed,skipped,now,now,now)); conn.commit(); conn.close()
        return jsonify({'message':'Progreso de aprendizaje actualizado.'}),200

    @bp.post('/chat')
    def chat():
        flags = public_flags()
        if not flags['enabled'] or not flags['text_enabled']:
            return jsonify({'error':'El chat de LÍA está desactivado.'}), 404
        ctx = get_request_user_context()
        if limited(ctx): return jsonify({'error':'Demasiadas solicitudes a LÍA. Espera un momento.'}),429
        data = request.get_json(silent=True) or {}
        question = str(data.get('message') or '').strip()
        module = str(data.get('module') or 'dashboard').strip()
        if not question:
            return jsonify({'error':'La pregunta es obligatoria.'}), 400
        if len(question) > flags['max_message_length']:
            return jsonify({'error':'La pregunta supera el límite permitido.'}), 413
        allowed = set(ROLE_MENU_PERMISSIONS.get(str(ctx.get('rol') or ''), []))
        if allowed and module not in allowed:
            return jsonify({'error':'Módulo no autorizado para el rol actual.'}), 403
        result=respond(question=question, module=module, role=str(ctx.get('rol') or ''),allowed_modules=sorted(allowed))
        audit_lia(ctx,'QUESTION_COMPLETED',module=module,request_id=result['request_id'],metadata={'length':len(question),'provider':result['provider']})
        return jsonify(result), 200

    @bp.get('/health')
    def health():
        flags = public_flags()
        provider=provider_status()
        return jsonify({'status':'ok','enabled':flags['enabled'],'mode':'institutional_static' if not provider['ready'] else 'provider','provider_ready':provider['ready'],'realtime_enabled':flags['realtime_enabled']}), 200

    @bp.get('/tools')
    def tools_available():
        if not public_flags()['enabled']: return jsonify({'error':'LÍA está desactivada.'}),404
        get_request_user_context()
        return jsonify({'tools':sorted(ALLOWED_TOOLS),'write_tools':[]}),200

    @bp.post('/tools/<string:tool_name>')
    def run_tool(tool_name: str):
        if not public_flags()['enabled']: return jsonify({'error':'LÍA está desactivada.'}),404
        ctx=get_request_user_context(); user=dict(getattr(g,'current_user',None) or {})
        if limited(ctx): return jsonify({'error':'Demasiadas solicitudes a LÍA. Espera un momento.'}),429
        if not user.get('id'): user={'id':ctx.get('usuario_id'),'rol':ctx.get('rol')}
        request_id=uuid.uuid4().hex
        try:
            result=execute(tool_name,args=request.get_json(silent=True) or {},database_path=database_path,tenant_id=int(ctx.get('fundacion_id') or 1),user=user)
        except PermissionError as exc: audit_lia(ctx,'TOOL_REJECTED',tool=tool_name,success=False,request_id=request_id);return jsonify({'error':str(exc),'request_id':request_id}),403
        except LookupError as exc: audit_lia(ctx,'TOOL_NOT_FOUND',tool=tool_name,success=False,request_id=request_id);return jsonify({'error':str(exc),'request_id':request_id}),404
        except ValueError as exc: audit_lia(ctx,'TOOL_INVALID_ARGUMENT',tool=tool_name,success=False,request_id=request_id);return jsonify({'error':str(exc),'request_id':request_id}),422
        audit_lia(ctx,'TOOL_COMPLETED',tool=tool_name,request_id=request_id,metadata={'read_only':True})
        return jsonify({'tool':tool_name,'result':result,'read_only':True,'request_id':request_id}),200

    @bp.route('/preferences',methods=['GET','PUT'])
    def preferences():
        if not public_flags()['enabled']: return jsonify({'error':'LÍA está desactivada.'}),404
        ctx=get_request_user_context();fid=int(ctx.get('fundacion_id') or 1);uid=int(ctx.get('usuario_id') or 0);conn=connect()
        if request.method=='GET':
            row=conn.execute('SELECT voice_enabled,auto_speak_enabled,muted,speech_rate,reduced_motion,language FROM lia_user_preferences WHERE fundacion_id=? AND usuario_id=?',(fid,uid)).fetchone();conn.close()
            return jsonify({'preferences':dict(row) if row else {'voice_enabled':0,'auto_speak_enabled':0,'muted':0,'speech_rate':.95,'reduced_motion':0,'language':'es-CO'}}),200
        data=request.get_json(silent=True) or {}
        try: rate=max(.6,min(1.5,float(data.get('speech_rate') or .95)))
        except (TypeError,ValueError): conn.close();return jsonify({'error':'La velocidad de voz no es válida.'}),422
        now=datetime.now().isoformat(timespec='seconds')
        values=(1 if data.get('voice_enabled') else 0,1 if data.get('auto_speak_enabled') else 0,1 if data.get('muted') else 0,rate,1 if data.get('reduced_motion') else 0,'es-CO')
        conn.execute('''INSERT INTO lia_user_preferences(fundacion_id,usuario_id,voice_enabled,auto_speak_enabled,muted,speech_rate,reduced_motion,language,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(fundacion_id,usuario_id) DO UPDATE SET voice_enabled=excluded.voice_enabled,auto_speak_enabled=excluded.auto_speak_enabled,muted=excluded.muted,speech_rate=excluded.speech_rate,reduced_motion=excluded.reduced_motion,language=excluded.language,updated_at=excluded.updated_at''',(fid,uid,*values,now,now));conn.commit();conn.close();audit_lia(ctx,'PREFERENCES_UPDATED',metadata={'voice_enabled':bool(values[0]),'muted':bool(values[2])})
        return jsonify({'message':'Preferencias de LÍA actualizadas.'}),200

    @bp.post('/feedback')
    def feedback():
        flags=public_flags()
        if not flags['enabled'] or not flags['feedback_enabled']: return jsonify({'error':'La retroalimentación está desactivada.'}),404
        ctx=get_request_user_context();data=request.get_json(silent=True) or {};rating=int(data.get('rating') or 0)
        if rating not in {-1,1}: return jsonify({'error':'Valoración no válida.'}),422
        reason=str(data.get('reason') or '')[:240];module=str(data.get('module') or '')[:80];request_id=str(data.get('request_id') or '')[:64];conn=connect();now=datetime.now().isoformat(timespec='seconds')
        conn.execute('INSERT INTO lia_feedback(fundacion_id,usuario_id,request_id,rating,reason,module,created_at) VALUES(?,?,?,?,?,?,?)',(int(ctx.get('fundacion_id') or 1),int(ctx.get('usuario_id') or 0),request_id,rating,reason,module,now));conn.commit();conn.close();audit_lia(ctx,'FEEDBACK_RECORDED',module=module,request_id=request_id,metadata={'rating':rating})
        return jsonify({'message':'Gracias. Registramos tu valoración sin guardar datos personales de la conversación.'}),201

    app.register_blueprint(bp)
