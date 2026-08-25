from __future__ import annotations

from datetime import datetime
from flask import Blueprint, jsonify, request, g
from modules.dbapi_compat import sqlite3
from modules.seguridad.services import ROLE_MENU_PERMISSIONS, get_request_user_context
from .guides import DEFAULT_GUIDE, GUIDES
from .schema import SCHEMA_SQL
from .config import public_flags
from .assistant_service import respond
from .platform_profile import get_platform_profile
from .tool_registry import ALLOWED_TOOLS, execute
from .rate_limit import allow
import json, uuid


def register_asistente_capacitacion(app, database_path: str) -> None:
    def connect():
        conn = sqlite3.connect(database_path); conn.row_factory = sqlite3.Row; return conn

    conn = connect(); conn.executescript(SCHEMA_SQL); conn.commit(); conn.close()
    bp = Blueprint('asistente_capacitacion', __name__, url_prefix='/api/asistente-capacitacion')

    def audit_lia(ctx, event_type, *, module=None, tool=None, success=True, request_id=None, metadata=None):
        conn=connect();conn.execute('''INSERT INTO lia_audit_events
          (fundacion_id,usuario_id,event_type,modulo,tool_name,success,request_id,metadata_redacted,created_at)
          VALUES(?,?,?,?,?,?,?,?,?)''',(int(ctx.get('fundacion_id') or 1),int(ctx.get('usuario_id') or 0),event_type,module,tool,1 if success else 0,request_id,json.dumps(metadata or {},ensure_ascii=False),datetime.now().isoformat(timespec='seconds')));conn.commit();conn.close()

    def limited(ctx):
        flags=public_flags();key=f"{ctx.get('fundacion_id')}:{ctx.get('usuario_id')}"
        return not allow(key,flags['rate_limit_per_minute'])

    @bp.get('/config')
    def config_publica():
        return jsonify({'lia': public_flags(), 'platform_profile': get_platform_profile()}), 200

    @bp.get('/contexto')
    def contexto():
        if not public_flags()['enabled']:
            return jsonify({'error':'LÍA está desactivada.'}), 404
        ctx = get_request_user_context(); modulo = str(request.args.get('modulo') or 'dashboard').strip()
        allowed = set(ROLE_MENU_PERMISSIONS.get(str(ctx.get('rol') or ''), []))
        if allowed and modulo not in allowed: return jsonify({'error':'Módulo no autorizado para el rol actual.'}), 403
        guide = dict(GUIDES.get(modulo, DEFAULT_GUIDE)); guide['modulo'] = modulo
        conn = connect(); row = conn.execute('SELECT * FROM ayuda_progreso_usuario WHERE fundacion_id=? AND usuario_id=? AND modulo=?',(ctx.get('fundacion_id') or 1,ctx.get('usuario_id'),modulo)).fetchone(); conn.close()
        return jsonify({'guia':guide,'rol':ctx.get('rol'),'progreso':dict(row) if row else None,'solo_orientacion':True}), 200

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
        result=respond(question=question, module=module, role=str(ctx.get('rol') or ''))
        audit_lia(ctx,'QUESTION_COMPLETED',module=module,request_id=result['request_id'],metadata={'length':len(question),'provider':result['provider']})
        return jsonify(result), 200

    @bp.get('/health')
    def health():
        flags = public_flags()
        return jsonify({'status':'ok', 'enabled':flags['enabled'], 'mode':'static' if not flags['ai_enabled'] else 'provider'}), 200

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
