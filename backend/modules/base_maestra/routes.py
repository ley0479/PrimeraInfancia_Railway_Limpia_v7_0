from __future__ import annotations

import os
from pathlib import Path

from flask import Blueprint, jsonify, request, send_from_directory

from modules.seguridad.services import require_roles
from modules.seguridad.tenant_context import tenant_path

from .repository import BaseMaestraRepository
from .services import (
    exportar_inconsistencias_excel,
    exportar_unidad_fuentes_excel,
    exportar_validacion_excel,
    get_user_context,
    guardar_fuente,
    validar_carga,
    validar_fuentes_pendientes,
    consolidar_base_maestra,
    publicar_base_maestra,
    dashboard_base_maestra,
    dashboard_operativo_base_maestra,
    detalle_unidad_base_maestra,
    diagnostico_unidades_base_maestra,
    fuente_estado_base_maestra,
    listar_coordinadores,
    listar_corporaciones,
    listar_historial,
    listar_inconsistencias,
    listar_movimientos,
    listar_unidades,
    normalize_tipo_fuente,
)


def payload() -> dict:
    if request.is_json:
        return request.get_json(silent=True) or {}
    return request.form.to_dict() or {}


def register_base_maestra(app, database_path: str, upload_folder: str, output_folder: str) -> None:
    repo = BaseMaestraRepository(database_path)

    bp = Blueprint('base_maestra', __name__, url_prefix='/api/base-maestra')
    module_upload = tenant_path(upload_folder, 'base_maestra')
    module_output = tenant_path(output_folder, 'base_maestra')
    os.makedirs(module_upload, exist_ok=True)
    os.makedirs(module_output, exist_ok=True)

    @bp.route('/fuentes-estado', methods=['GET'])
    @require_roles('SUPERADMIN', 'GERENTE', 'COORDINADOR', 'AUXILIAR_ADMINISTRATIVO', 'NUTRICIONISTA')
    def fuentes_estado():
        """Estado de las tres fuentes que alimentan la Base Maestra."""
        return jsonify(fuente_estado_base_maestra(database_path)), 200

    @bp.route('/resumen-panel', methods=['GET'])
    @require_roles('SUPERADMIN', 'GERENTE', 'COORDINADOR', 'AUXILIAR_ADMINISTRATIVO', 'NUTRICIONISTA')
    def resumen_panel():
        """Contrato compatible con el Panel Principal: todo desde Base Maestra publicada."""
        return jsonify(dashboard_operativo_base_maestra(database_path)), 200

    @bp.route('/diagnostico-unidades', methods=['GET'])
    @require_roles('SUPERADMIN', 'GERENTE', 'COORDINADOR', 'AUXILIAR_ADMINISTRATIVO', 'NUTRICIONISTA')
    def diagnostico_unidades():
        return jsonify(diagnostico_unidades_base_maestra(database_path)), 200

    @bp.route('/unidad/<path:unidad>/pendientes', methods=['GET'])
    @require_roles('SUPERADMIN', 'GERENTE', 'COORDINADOR', 'AUXILIAR_ADMINISTRATIVO', 'NUTRICIONISTA')
    def unidad_pendientes(unidad: str):
        detalle = detalle_unidad_base_maestra(database_path, unidad)
        return jsonify({
            'unidad': detalle.get('unidad'),
            'encontrada': detalle.get('encontrada'),
            'pendientes': detalle.get('pendientes') or {},
            'nutricion_pendiente': detalle.get('nutricion_pendiente') or 0,
            'usuarios': detalle.get('usuarios') or [],
        }), 200

    @bp.route('/unidad/<path:unidad>/grupos-etarios', methods=['GET'])
    @require_roles('SUPERADMIN', 'GERENTE', 'COORDINADOR', 'AUXILIAR_ADMINISTRATIVO', 'NUTRICIONISTA')
    def unidad_grupos_etarios(unidad: str):
        detalle = detalle_unidad_base_maestra(database_path, unidad)
        return jsonify({
            'unidad': detalle.get('unidad'),
            'encontrada': detalle.get('encontrada'),
            'grupos_edad': detalle.get('grupos_edad') or {},
            'usuarios': detalle.get('usuarios') or [],
        }), 200

    @bp.route('/resumen', methods=['GET'])
    @require_roles('SUPERADMIN', 'GERENTE', 'COORDINADOR', 'AUXILIAR_ADMINISTRATIVO', 'NUTRICIONISTA')
    def resumen():
        return jsonify(dashboard_base_maestra(database_path)), 200

    @bp.route('/version-activa', methods=['GET'])
    @require_roles('SUPERADMIN', 'GERENTE', 'COORDINADOR', 'AUXILIAR_ADMINISTRATIVO', 'NUTRICIONISTA')
    def version_activa():
        ctx = get_user_context()
        row = repo.version_activa(ctx['fundacion_id'])
        return jsonify({'version_activa': row}), 200

    @bp.route('/corporaciones', methods=['GET'])
    @require_roles('SUPERADMIN', 'GERENTE', 'AUXILIAR_ADMINISTRATIVO')
    def corporaciones():
        return jsonify(listar_corporaciones(database_path)), 200

    @bp.route('/unidades', methods=['GET'])
    @require_roles('SUPERADMIN', 'GERENTE', 'COORDINADOR', 'AUXILIAR_ADMINISTRATIVO', 'NUTRICIONISTA')
    def unidades():
        return jsonify(listar_unidades(database_path)), 200

    @bp.route('/coordinadores', methods=['GET'])
    @require_roles('SUPERADMIN', 'GERENTE', 'COORDINADOR', 'AUXILIAR_ADMINISTRATIVO')
    def coordinadores():
        return jsonify(listar_coordinadores(database_path)), 200

    @bp.route('/inconsistencias', methods=['GET'])
    @require_roles('SUPERADMIN', 'GERENTE', 'COORDINADOR', 'AUXILIAR_ADMINISTRATIVO', 'NUTRICIONISTA')
    def inconsistencias():
        limit = request.args.get('limit', 500, type=int)
        return jsonify(listar_inconsistencias(database_path, limit=limit)), 200

    @bp.route('/historial', methods=['GET'])
    @require_roles('SUPERADMIN', 'GERENTE', 'COORDINADOR', 'AUXILIAR_ADMINISTRATIVO')
    def historial():
        limit = request.args.get('limit', 500, type=int)
        return jsonify(listar_historial(database_path, limit=limit)), 200

    @bp.route('/movimientos', methods=['GET'])
    @require_roles('SUPERADMIN', 'GERENTE', 'COORDINADOR', 'AUXILIAR_ADMINISTRATIVO', 'NUTRICIONISTA')
    def movimientos():
        limit = request.args.get('limit', 500, type=int)
        return jsonify(listar_movimientos(database_path, limit=limit)), 200

    @bp.route('/cargar-fuente', methods=['POST'])
    @require_roles('SUPERADMIN', 'GERENTE', 'AUXILIAR_ADMINISTRATIVO', 'NUTRICIONISTA')
    def cargar_fuente():
        if 'file' not in request.files or not request.files['file'].filename:
            return jsonify({'error': 'Selecciona un archivo para cargar como fuente de Base Maestra.'}), 400
        tipo = normalize_tipo_fuente(request.form.get('tipo_fuente') or request.form.get('tipo') or 'cuentame')
        ctx = get_user_context()
        corporacion_id = request.form.get('corporacion_id', type=int)
        if corporacion_id:
            ctx['corporacion_id'] = corporacion_id
        try:
            return jsonify(guardar_fuente(database_path, module_upload, request.files['file'], tipo, ctx)), 201
        except Exception as exc:
            return jsonify({'error': f'No se pudo cargar la fuente de Base Maestra: {exc}'}), 400

    @bp.route('/validar', methods=['POST'])
    @require_roles('SUPERADMIN', 'GERENTE', 'AUXILIAR_ADMINISTRATIVO', 'NUTRICIONISTA')
    def validar():
        data = payload()
        carga_id = data.get('carga_id') or request.args.get('carga_id', type=int)
        try:
            if carga_id:
                return jsonify(validar_carga(database_path, int(carga_id))), 200
            return jsonify(validar_fuentes_pendientes(database_path)), 200
        except PermissionError as exc:
            return jsonify({'error': str(exc)}), 403
        except Exception as exc:
            return jsonify({'error': f'No se pudo validar la carga: {exc}'}), 400

    @bp.route('/consolidar', methods=['POST'])
    @require_roles('SUPERADMIN', 'GERENTE', 'AUXILIAR_ADMINISTRATIVO', 'NUTRICIONISTA')
    def consolidar():
        data = payload()
        try:
            resultado = consolidar_base_maestra(database_path, observaciones=data.get('observaciones') or '')
            return jsonify(resultado), 201
        except PermissionError as exc:
            return jsonify({'error': str(exc)}), 403
        except Exception as exc:
            return jsonify({'error': f'No se pudo consolidar la Base Maestra: {exc}'}), 400

    @bp.route('/publicar', methods=['POST'])
    @require_roles('SUPERADMIN', 'GERENTE', 'AUXILIAR_ADMINISTRATIVO')
    def publicar():
        data = payload()
        version_id = data.get('version_id') or request.args.get('version_id', type=int)
        if not version_id:
            return jsonify({'error': 'version_id es requerido para publicar.'}), 400
        try:
            return jsonify(publicar_base_maestra(database_path, int(version_id), observaciones=data.get('observaciones') or '')), 200
        except PermissionError as exc:
            return jsonify({'error': str(exc)}), 403
        except Exception as exc:
            return jsonify({'error': str(exc)}), 400

    @bp.route('/validacion/<int:validacion_id>/descargar', methods=['GET'])
    @require_roles('SUPERADMIN', 'GERENTE', 'AUXILIAR_ADMINISTRATIVO', 'NUTRICIONISTA')
    def descargar_validacion(validacion_id: int):
        try:
            path = exportar_validacion_excel(database_path, module_output, validacion_id)
            return send_from_directory(module_output, Path(path).name, as_attachment=True)
        except PermissionError as exc:
            return jsonify({'error': str(exc)}), 403
        except Exception as exc:
            return jsonify({'error': f'No se pudo descargar validación: {exc}'}), 400

    @bp.route('/inconsistencias/descargar', methods=['GET'])
    @require_roles('SUPERADMIN', 'GERENTE', 'COORDINADOR', 'AUXILIAR_ADMINISTRATIVO', 'NUTRICIONISTA')
    def descargar_inconsistencias():
        try:
            path = exportar_inconsistencias_excel(database_path, module_output)
            return send_from_directory(module_output, Path(path).name, as_attachment=True)
        except Exception as exc:
            return jsonify({'error': f'No se pudo descargar inconsistencias: {exc}'}), 400

    @bp.route('/unidad-registros/descargar', methods=['GET'])
    @require_roles('SUPERADMIN', 'GERENTE', 'COORDINADOR', 'AUXILIAR_ADMINISTRATIVO', 'NUTRICIONISTA')
    def descargar_registros_unidad():
        try:
            unidad = request.args.get('unidad') or ''
            path = exportar_unidad_fuentes_excel(database_path, module_output, unidad)
            return send_from_directory(module_output, Path(path).name, as_attachment=True)
        except Exception as exc:
            return jsonify({'error': f'No se pudo generar el Excel de la unidad: {exc}'}), 400

    app.register_blueprint(bp)
