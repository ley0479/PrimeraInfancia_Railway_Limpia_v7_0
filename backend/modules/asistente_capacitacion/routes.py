from __future__ import annotations

from datetime import datetime
from flask import Blueprint, jsonify, request
from modules.dbapi_compat import sqlite3
from modules.seguridad.services import ROLE_MENU_PERMISSIONS, get_request_user_context
from .guides import DEFAULT_GUIDE, GUIDES
from .schema import SCHEMA_SQL
from .config import public_flags
from .assistant_service import respond


def register_asistente_capacitacion(app, database_path: str) -> None:
    def connect():
        conn = sqlite3.connect(database_path); conn.row_factory = sqlite3.Row; return conn

    conn = connect(); conn.executescript(SCHEMA_SQL); conn.commit(); conn.close()
    bp = Blueprint('asistente_capacitacion', __name__, url_prefix='/api/asistente-capacitacion')

    @bp.get('/config')
    def config_publica():
        return jsonify({'lia': public_flags()}), 200

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
        return jsonify(respond(question=question, module=module, role=str(ctx.get('rol') or ''))), 200

    @bp.get('/health')
    def health():
        flags = public_flags()
        return jsonify({'status':'ok', 'enabled':flags['enabled'], 'mode':'static' if not flags['ai_enabled'] else 'provider'}), 200

    app.register_blueprint(bp)
