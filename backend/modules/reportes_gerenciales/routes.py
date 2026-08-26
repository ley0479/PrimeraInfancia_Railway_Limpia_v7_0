from __future__ import annotations

import os
from datetime import datetime

from flask import Blueprint, g, jsonify, request, send_file

from modules.seguridad.services import require_roles
from .services import ReportesGerencialesService
from .atenciones_priorizadas import AtencionesPriorizadasService, ATENCIONES

ALLOWED_ROLES = ('SUPERADMIN', 'GERENTE', 'COORDINADOR', 'AUXILIAR_ADMINISTRATIVO')


def current_user() -> dict:
    user = getattr(g, 'current_user', {}) or {}
    return {
        'id': user.get('id') or user.get('usuario_id'),
        'username': user.get('username') or user.get('email') or 'sistema',
        'rol': user.get('rol') or 'SUPERADMIN',
        'fundacion_id': int(user.get('fundacion_id') or 1),
        'raw': user,
    }


def register_reportes_gerenciales(app, database_path: str, output_folder: str) -> None:
    service = ReportesGerencialesService(database_path, output_folder)
    atenciones_service = AtencionesPriorizadasService(service)
    service.init_schema()

    bp = Blueprint('reportes_gerenciales', __name__, url_prefix='/api/reportes-gerenciales')

    @bp.before_request
    def _ensure_schema():
        service.init_schema()

    @bp.route('/dashboard', methods=['GET'])
    @require_roles(*ALLOWED_ROLES)
    def dashboard():
        user = current_user()
        return jsonify(service.dashboard(user.get('fundacion_id')))

    @bp.route('/9-atenciones/catalogo', methods=['GET'])
    @require_roles(*ALLOWED_ROLES)
    def catalogo_nueve_atenciones():
        return jsonify({'atenciones': [
            {'codigo': codigo, 'nombre': nombre, 'fuente': fuente, 'automatizacion': automatizacion}
            for codigo, nombre, fuente, automatizacion in ATENCIONES
        ]})

    @bp.route('/9-atenciones/consolidar', methods=['GET'])
    @require_roles(*ALLOWED_ROLES)
    def consolidar_nueve_atenciones():
        hoy = datetime.now()
        try:
            mes = max(1, min(12, int(request.args.get('mes') or hoy.month)))
            anio = int(request.args.get('anio') or hoy.year)
            cobertura = int(request.args.get('cobertura_contratada') or 0)
            user = current_user()
            return jsonify(atenciones_service.consolidar(user['fundacion_id'], mes, anio, cobertura))
        except Exception as exc:
            return jsonify({'error': f'No se pudo consolidar el informe de nueve atenciones: {exc}'}), 422

    @bp.route('/9-atenciones/informes', methods=['POST'])
    @require_roles(*ALLOWED_ROLES)
    def guardar_nueve_atenciones():
        payload = request.get_json(silent=True) or {}
        try:
            return jsonify({'message': 'Borrador mensual consolidado.', 'informe': atenciones_service.guardar_borrador(payload, current_user())}), 201
        except (TypeError, ValueError) as exc:
            return jsonify({'error': str(exc)}), 422

    @bp.route('/9-atenciones/informes/<int:informe_id>', methods=['GET'])
    @require_roles(*ALLOWED_ROLES)
    def detalle_nueve_atenciones(informe_id: int):
        try:
            user = current_user()
            return jsonify(atenciones_service.detalle(informe_id, user['fundacion_id']))
        except LookupError as exc:
            return jsonify({'error': str(exc)}), 404

    @bp.route('/9-atenciones/informes/<int:informe_id>/atenciones/<codigo>', methods=['PUT'])
    @require_roles(*ALLOWED_ROLES)
    def actualizar_nueve_atenciones(informe_id: int, codigo: str):
        try:
            resultado = atenciones_service.actualizar_atencion(informe_id, codigo, request.get_json(silent=True) or {}, current_user())
            return jsonify({'message': 'Atención actualizada.', 'resultado': resultado})
        except LookupError as exc:
            return jsonify({'error': str(exc)}), 404
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 422

    @bp.route('/9-atenciones/informes/<int:informe_id>/atenciones/<codigo>/evidencias', methods=['POST'])
    @require_roles(*ALLOWED_ROLES)
    def evidencia_nueve_atenciones(informe_id: int, codigo: str):
        upload=request.files.get('file')
        if not upload: return jsonify({'error':'Selecciona una evidencia.'}),400
        try:
            item=atenciones_service.guardar_evidencia(informe_id,codigo,upload,request.form.to_dict(),current_user())
            return jsonify({'message':'Evidencia cargada y pendiente de revisión.','evidencia':item}),201
        except LookupError as exc:
            return jsonify({'error':str(exc)}),404
        except ValueError as exc:
            return jsonify({'error':str(exc)}),422

    @bp.route('/9-atenciones/plantilla-pptx', methods=['GET', 'POST'])
    @require_roles(*ALLOWED_ROLES)
    def plantilla_pptx_nueve_atenciones():
        user=current_user()
        if request.method == 'GET':
            return jsonify({'plantilla':atenciones_service.plantilla_pptx_activa(user['fundacion_id'])})
        if str(user.get('rol') or '').upper() not in {'SUPERADMIN','GERENTE','COORDINADOR'}:
            return jsonify({'error':'No tienes permiso para reemplazar la plantilla oficial.'}),403
        upload=request.files.get('file')
        if not upload: return jsonify({'error':'Selecciona la plantilla PowerPoint .pptx.'}),400
        try:
            item=atenciones_service.guardar_plantilla_pptx(upload,request.form.to_dict(),user)
            return jsonify({'message':'Plantilla PowerPoint oficial registrada y activada.','plantilla':item}),201
        except ValueError as exc:
            return jsonify({'error':str(exc)}),422

    @bp.route('/9-atenciones/informes/<int:informe_id>/aprobar', methods=['POST'])
    @require_roles('SUPERADMIN', 'GERENTE', 'COORDINADOR')
    def aprobar_nueve_atenciones(informe_id: int):
        try:
            return jsonify({'message': 'Informe aprobado y fotografía histórica creada.', 'informe': atenciones_service.aprobar(informe_id, current_user())})
        except LookupError as exc:
            return jsonify({'error': str(exc)}), 404
        except ValueError as exc:
            return jsonify({'error': str(exc), 'code': 'RG9_VALIDATION_FAILED'}), 422

    @bp.route('/9-atenciones/informes/<int:informe_id>/generar', methods=['POST'])
    @require_roles(*ALLOWED_ROLES)
    def generar_archivos_nueve_atenciones(informe_id: int):
        try:
            user = current_user(); files = atenciones_service.generar_exportaciones(informe_id, user['fundacion_id'])
            return jsonify({'message': 'PowerPoint, PDF, Excel y ZIP generados.', 'archivos': {key: os.path.basename(value) for key,value in files.items()}})
        except LookupError as exc:
            return jsonify({'error': str(exc)}), 404
        except Exception as exc:
            return jsonify({'error': f'No se pudieron generar los archivos: {exc}'}), 422

    @bp.route('/9-atenciones/informes/<int:informe_id>/descargar/<tipo>', methods=['GET'])
    @require_roles(*ALLOWED_ROLES)
    def descargar_archivo_nueve_atenciones(informe_id: int, tipo: str):
        try:
            user=current_user(); files=atenciones_service.generar_exportaciones(informe_id,user['fundacion_id']); path=files.get(str(tipo).lower())
            if not path or not os.path.isfile(path): return jsonify({'error':'Tipo de archivo no disponible.'}),404
            return send_file(path,as_attachment=True,download_name=os.path.basename(path))
        except LookupError as exc:
            return jsonify({'error': str(exc)}), 404

    @bp.route('/generar', methods=['POST'])
    @require_roles(*ALLOWED_ROLES)
    def generar():
        payload = request.get_json(silent=True) or request.form.to_dict() or {}
        hoy = datetime.now()
        mes = int(payload.get('mes') or payload.get('month') or hoy.month)
        anio = int(payload.get('anio') or payload.get('año') or payload.get('year') or hoy.year)
        try:
            resultado = service.generar_reporte_ejecutivo(mes, anio, current_user(), registrar=True)
            data = resultado.get('data') or {}
            return jsonify({
                'message': 'Reporte gerencial ejecutivo generado correctamente.',
                'reporte': {
                    'id': resultado.get('id'),
                    'periodo': resultado.get('periodo'),
                    'nombre_excel': resultado.get('nombre_excel'),
                    'nombre_pdf': resultado.get('nombre_pdf'),
                },
                'resumen_ejecutivo': data.get('resumen_ejecutivo'),
                'indicadores': data.get('indicadores'),
                'hallazgos': data.get('hallazgos'),
                'alertas': data.get('alertas'),
                'recomendaciones': data.get('recomendaciones'),
                'pendientes': data.get('pendientes'),
                'responsables': data.get('responsables'),
                'conclusion': data.get('conclusion'),
            })
        except Exception as exc:
            return jsonify({'error': f'No se pudo generar el reporte gerencial: {exc}'}), 500

    @bp.route('/historial', methods=['GET'])
    @require_roles(*ALLOWED_ROLES)
    def historial():
        user = current_user()
        limit = int(request.args.get('limit') or 50)
        return jsonify({'reportes': service.historial(user.get('fundacion_id'), limit)})

    @bp.route('/<int:reporte_id>', methods=['GET'])
    @require_roles(*ALLOWED_ROLES)
    def detalle(reporte_id: int):
        row = service.obtener_reporte(reporte_id)
        if not row:
            return jsonify({'error': 'Reporte no encontrado.'}), 404
        return jsonify({'reporte': row})

    @bp.route('/<int:reporte_id>/descargar/<tipo>', methods=['GET'])
    @require_roles(*ALLOWED_ROLES)
    def descargar(reporte_id: int, tipo: str):
        row = service.obtener_reporte(reporte_id)
        if not row:
            return jsonify({'error': 'Reporte no encontrado.'}), 404
        tipo = (tipo or '').lower()
        ruta = row.get('ruta_pdf') if tipo == 'pdf' else row.get('ruta_excel')
        nombre = row.get('nombre_pdf') if tipo == 'pdf' else row.get('nombre_excel')
        if not ruta or not os.path.exists(ruta):
            return jsonify({'error': 'Archivo del reporte no encontrado.'}), 404
        return send_file(ruta, as_attachment=True, download_name=nombre or os.path.basename(ruta))

    app.register_blueprint(bp)
