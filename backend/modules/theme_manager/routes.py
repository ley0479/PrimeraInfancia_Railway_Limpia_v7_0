from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from modules.seguridad.services import require_roles

from .services import (
    create_theme,
    current_context,
    init_schema,
    list_themes,
    save_corporation_config,
    save_user_preference,
    update_theme,
)

ALL_ROLES = (
    'SUPERADMIN', 'GERENTE', 'COORDINADOR', 'DOCENTE', 'NUTRICIONISTA',
    'PSICOSOCIAL', 'AUXILIAR_ADMINISTRATIVO'
)
ADMIN_ROLES = ('SUPERADMIN', 'GERENTE')


def payload() -> dict:
    return request.get_json(silent=True) or {}


def current_user() -> dict:
    return getattr(g, 'current_user', {}) or {}


def register_theme_manager(app, database_path: str) -> None:
    bp = Blueprint('theme_manager', __name__, url_prefix='/api/theme-manager')

    @bp.route('/actual', methods=['GET'])
    @require_roles(*ALL_ROLES)
    def obtener_tema_actual():
        return jsonify(current_context(database_path, current_user()))

    @bp.route('/temas', methods=['GET'])
    @require_roles(*ALL_ROLES)
    def obtener_temas():
        user = current_user()
        include_inactive = user.get('rol') in {'SUPERADMIN', 'GERENTE'} and request.args.get('incluir_inactivos') == '1'
        return jsonify({'temas': list_themes(database_path, include_inactive=include_inactive, fundacion_id=int(user.get('fundacion_id') or 1))})

    @bp.route('/preferencia', methods=['POST'])
    @require_roles(*ALL_ROLES)
    def guardar_preferencia():
        try:
            ctx = save_user_preference(database_path, current_user(), payload(), request.remote_addr)
            return jsonify({'message': 'Diseño guardado para tu usuario.', **ctx})
        except PermissionError as exc:
            return jsonify({'error': str(exc)}), 403
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 400

    @bp.route('/corporacion', methods=['POST'])
    @require_roles(*ADMIN_ROLES)
    def guardar_config_corporacion():
        try:
            ctx = save_corporation_config(database_path, current_user(), payload(), request.remote_addr)
            return jsonify({'message': 'Configuración de diseño guardada para la corporación.', **ctx})
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 400

    @bp.route('/temas', methods=['POST'])
    @require_roles(*ADMIN_ROLES)
    def crear_tema():
        try:
            tema = create_theme(database_path, current_user(), payload(), request.remote_addr)
            return jsonify({'message': 'Tema creado correctamente.', 'tema': tema}), 201
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 400

    @bp.route('/temas/<codigo>', methods=['PUT'])
    @require_roles(*ADMIN_ROLES)
    def actualizar_tema(codigo: str):
        try:
            tema = update_theme(database_path, current_user(), codigo, payload(), request.remote_addr)
            return jsonify({'message': 'Tema actualizado correctamente.', 'tema': tema})
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 400

    app.register_blueprint(bp)
