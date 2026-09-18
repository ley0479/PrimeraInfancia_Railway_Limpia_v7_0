"""
Rutas Flask del módulo independiente Salud y Nutrición Inteligente.
"""
from __future__ import annotations

import json
import os
from datetime import datetime

from flask import Blueprint, jsonify, request, send_from_directory, send_file
from modules.seguridad.services import require_roles
from modules.seguridad.tenant_context import tenant_path
from werkzeug.utils import secure_filename

from .repository import SaludNutricionRepository
from .integral import register_integral_routes
from .entregables import EntregablesSaludNutricionService
from .tematicas import register_tematicas_routes
from .reportes import (
    generar_excel_comparacion,
    generar_pdf_comparacion,
    generar_excel_dashboard,
    generar_pdf_dashboard,
)
from .services import (
    calcular_alertas_valoracion,
    comparar_bases,
    normalizar_base_comparacion,
    normalizar_base_personas,
    now_iso,
    read_tabular_file,
)

ENTREGABLES_READ_ROLES = ('SUPERADMIN', 'GERENTE', 'COORDINADOR', 'AUXILIAR_ADMINISTRATIVO', 'NUTRICIONISTA')
ENTREGABLES_EDIT_ROLES = ('SUPERADMIN', 'GERENTE', 'COORDINADOR', 'NUTRICIONISTA')


def health_themes_enabled() -> bool:
    return str(os.environ.get('ENABLE_HEALTH_THEMES','true')).strip().lower() in {'1','true','yes','on','si','sí'}


def allowed_data_file(filename: str) -> bool:
    return os.path.splitext(filename.lower())[1] in {'.xlsx', '.xls', '.xlsm', '.csv', '.txt'}


def save_upload(file, upload_folder: str, prefix: str) -> dict:
    os.makedirs(upload_folder, exist_ok=True)
    nombre_original = file.filename or 'archivo'
    nombre_seguro = secure_filename(nombre_original)
    nombre_guardado = f"{prefix}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{nombre_seguro}"
    ruta = os.path.join(upload_folder, nombre_guardado)
    file.save(ruta)
    return {'nombre_original': nombre_original, 'nombre_guardado': nombre_guardado, 'ruta': ruta}


def register_salud_nutricion(app, database_path: str, upload_folder: str, output_folder: str) -> None:
    repo = SaludNutricionRepository(database_path)
    repo.init_schema()

    bp = Blueprint('salud_nutricion_inteligente', __name__, url_prefix='/api/salud-nutricion')
    module_upload = tenant_path(upload_folder, 'salud_nutricion')
    module_reports = tenant_path(output_folder, 'salud_nutricion')
    os.makedirs(module_upload, exist_ok=True)
    os.makedirs(module_reports, exist_ok=True)
    entregables_service = EntregablesSaludNutricionService(repo, module_reports, module_upload)
    entregables_service.init_schema()
    data_dir = os.environ.get('DATA_DIR') or os.path.dirname(os.path.abspath(upload_folder))
    integral_service = register_integral_routes(bp, repo, data_dir)
    tematicas_service = register_tematicas_routes(bp, repo, integral_service, database_path, data_dir)

    @bp.before_request
    def _ensure_schema():
        if request.path.startswith('/api/salud-nutricion/tematicas') and not health_themes_enabled():
            return jsonify({'error':'Temáticas, actividades e informes está desactivado por configuración.','codigo':'FEATURE_DISABLED'}),404
        repo.init_schema()
        entregables_service.init_schema()
        integral_service.init_schema()
        tematicas_service.init_schema()

    @bp.route('/dashboard', methods=['GET'])
    def dashboard():
        periodo = request.args.get('periodo') or None
        data = repo.dashboard_data(periodo)
        return jsonify(data), 200

    @bp.route('/valoraciones', methods=['GET'])
    def valoraciones():
        periodo = request.args.get('periodo') or None
        unidad = request.args.get('unidad') or None
        diagnostico = request.args.get('diagnostico') or None
        nivel = request.args.get('nivel') or None
        limit = request.args.get('limit', default=500, type=int)

        where = ['activo = 1']
        params = []
        if periodo:
            where.append('periodo = ?')
            params.append(periodo)
        if unidad:
            where.append('unidad = ?')
            params.append(unidad)
        if diagnostico:
            where.append('diagnostico_global = ?')
            params.append(diagnostico)
        if nivel:
            where.append('nivel_alerta = ?')
            params.append(nivel)

        rows = repo.fetch_all(
            f"""
            SELECT *
            FROM sn_valoraciones
            WHERE {' AND '.join(where)}
            ORDER BY fecha_valoracion DESC, unidad, nombre_completo
            LIMIT ?
            """,
            params + [max(1, min(limit, 5000))]
        )
        return jsonify({'valoraciones': rows}), 200

    @bp.route('/importar', methods=['POST'])
    def importar_valoraciones():
        if 'file' not in request.files:
            return jsonify({'error': 'Falta el archivo de salud y nutrición.'}), 400
        file = request.files['file']
        if not file.filename:
            return jsonify({'error': 'Archivo no seleccionado.'}), 400
        if not allowed_data_file(file.filename):
            return jsonify({'error': 'Formato no permitido. Usa Excel, CSV o TXT.'}), 400

        saved = save_upload(file, module_upload, 'VALORACION')
        usuario = request.form.get('usuario', 'sistema')
        try:
            df = read_tabular_file(saved['ruta'])
            registros = normalizar_base_personas(df)
        except Exception as exc:
            return jsonify({'error': f'No se pudo leer el archivo: {exc}'}), 400

        errores = []
        validos = 0
        alertas_count = 0

        for idx, registro in enumerate(registros, start=1):
            if not registro.get('documento'):
                errores.append({'fila': idx, 'error': 'Documento vacío'})
                continue
            anterior = repo.ultima_valoracion(registro['documento'])
            valoracion_id = repo.guardar_valoracion(registro, saved['nombre_original'], usuario)
            alertas = calcular_alertas_valoracion(registro, anterior)
            repo.guardar_alertas(valoracion_id, alertas)
            validos += 1
            alertas_count += len(alertas)

        carga_id = repo.execute(
            """
            INSERT INTO sn_cargas
            (tipo, archivo_original, archivo_guardado, total_registros, registros_validos,
             registros_con_alerta, errores_json, fecha_carga, usuario)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                'valoraciones',
                saved['nombre_original'],
                saved['nombre_guardado'],
                len(registros),
                validos,
                alertas_count,
                json.dumps(errores, ensure_ascii=False),
                now_iso(),
                usuario,
            )
        )
        repo.log('IMPORTAR_VALORACIONES_SN', 'sn_cargas', carga_id, usuario=usuario, nuevos={'validos': validos, 'alertas': alertas_count})
        return jsonify({
            'message': f'Valoraciones importadas correctamente. Registros válidos: {validos}. Alertas generadas: {alertas_count}.',
            'carga_id': carga_id,
            'registros_validos': validos,
            'alertas_generadas': alertas_count,
            'errores': errores[:50],
            'dashboard': repo.dashboard_data(request.form.get('periodo') or None)
        }), 201

    @bp.route('/ficha/<documento>', methods=['GET'])
    @bp.route('/historial/<documento>', methods=['GET'])
    def ficha(documento: str):
        historial = repo.historial_documento(documento)
        if not historial:
            return jsonify({'error': 'No existe historial nutricional para este documento.'}), 404
        return jsonify(historial), 200

    @bp.route('/alertas', methods=['GET'])
    def alertas():
        nivel = request.args.get('nivel') or None
        atendida = request.args.get('atendida')
        where = ['1=1']
        params = []
        if nivel:
            where.append('nivel = ?')
            params.append(nivel)
        if atendida is not None and atendida != '':
            where.append('atendida = ?')
            params.append(1 if str(atendida).lower() in {'1', 'true', 'si', 'sí'} else 0)

        rows = repo.fetch_all(
            f"""
            SELECT *
            FROM sn_alertas
            WHERE {' AND '.join(where)}
            ORDER BY CASE nivel WHEN 'ROJO' THEN 1 WHEN 'AMARILLO' THEN 2 ELSE 3 END, fecha_creacion DESC
            LIMIT 1000
            """,
            params,
        )
        return jsonify({'alertas': rows}), 200

    @bp.route('/alertas/<int:alerta_id>/atender', methods=['PUT', 'PATCH'])
    def atender_alerta(alerta_id: int):
        data = request.get_json(silent=True) or {}
        repo.execute(
            """
            UPDATE sn_alertas
            SET atendida = 1, observaciones = ?
            WHERE id = ?
            """,
            (data.get('observaciones', ''), alerta_id),
        )
        alerta = repo.fetch_one("SELECT * FROM sn_alertas WHERE id = ?", (alerta_id,))
        return jsonify({'message': 'Alerta marcada como atendida.', 'alerta': alerta}), 200

    @bp.route('/comparar', methods=['POST'])
    def comparar():
        if 'base_anterior' not in request.files or 'base_actual' not in request.files:
            return jsonify({'error': 'Debes cargar base_anterior y base_actual.'}), 400
        anterior_file = request.files['base_anterior']
        actual_file = request.files['base_actual']
        if not anterior_file.filename or not actual_file.filename:
            return jsonify({'error': 'Selecciona ambos archivos.'}), 400
        if not allowed_data_file(anterior_file.filename) or not allowed_data_file(actual_file.filename):
            return jsonify({'error': 'Las bases deben ser Excel, CSV o TXT.'}), 400

        saved_ant = save_upload(anterior_file, module_upload, 'BASE_ANTERIOR')
        saved_act = save_upload(actual_file, module_upload, 'BASE_ACTUAL')
        usuario = request.form.get('usuario', 'sistema')

        try:
            df_ant = read_tabular_file(saved_ant['ruta'])
            df_act = read_tabular_file(saved_act['ruta'])
            ant = normalizar_base_comparacion(df_ant)
            act = normalizar_base_comparacion(df_act)
            resultado = comparar_bases(ant, act)
            excel_path = generar_excel_comparacion(resultado, module_reports)
            pdf_path = generar_pdf_comparacion(resultado, module_reports)
        except Exception as exc:
            return jsonify({'error': f'No se pudo comparar: {exc}'}), 400

        resumen = resultado['resumen']
        comparacion_id = repo.execute(
            """
            INSERT INTO sn_comparaciones
            (archivo_anterior, archivo_actual, total_anterior, total_actual, nuevos, retirados,
             trasladados, cambios, resumen_json, reporte_excel, reporte_pdf, fecha_comparacion, usuario)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                saved_ant['nombre_original'],
                saved_act['nombre_original'],
                resumen['total_anterior'],
                resumen['total_actual'],
                resumen['nuevos'],
                resumen['retirados'],
                resumen['trasladados'],
                resumen['cambios'],
                json.dumps(resultado, ensure_ascii=False),
                os.path.basename(excel_path),
                os.path.basename(pdf_path),
                now_iso(),
                usuario,
            )
        )
        repo.log('COMPARAR_BASES_SN', 'sn_comparaciones', comparacion_id, usuario=usuario, nuevos=resumen)

        return jsonify({
            'message': 'Comparación generada correctamente.',
            'comparacion_id': comparacion_id,
            'resumen': resumen,
            'resultado': resultado,
            'reporte_excel': os.path.basename(excel_path),
            'reporte_pdf': os.path.basename(pdf_path),
        }), 201

    @bp.route('/comparaciones', methods=['GET'])
    def comparaciones():
        rows = repo.fetch_all(
            """
            SELECT id, archivo_anterior, archivo_actual, total_anterior, total_actual, nuevos,
                   retirados, trasladados, cambios, reporte_excel, reporte_pdf, fecha_comparacion, usuario
            FROM sn_comparaciones
            ORDER BY fecha_comparacion DESC
            LIMIT 100
            """
        )
        return jsonify({'comparaciones': rows}), 200

    @bp.route('/calendario', methods=['GET'])
    @bp.route('/calendario-nutricional', methods=['GET'])
    def calendario():
        periodo = request.args.get('periodo') or None
        return jsonify(repo.calendario_nutricional(periodo)), 200

    @bp.route('/boa', methods=['GET'])
    def boa_nutricional():
        periodo = request.args.get('periodo') or None
        unidad = request.args.get('unidad') or None
        diagnostico = request.args.get('diagnostico') or None
        nivel = request.args.get('nivel') or None
        return jsonify({'boa': repo.boa_data(periodo, unidad, diagnostico, nivel)}), 200

    @bp.route('/seguimientos-trimestrales', methods=['GET'])
    def seguimientos_trimestrales():
        periodo = request.args.get('periodo') or None
        eventos = repo.calendario_nutricional(periodo).get('eventos', [])
        seguimientos = [e for e in eventos if (e.get('tipo_evento') or e.get('tipo')) in {'SEGUIMIENTO_TRIMESTRAL', 'Valoración nutricional trimestral'}]
        return jsonify({'seguimientos': seguimientos}), 200

    @bp.route('/reportes/dashboard', methods=['GET'])
    def reporte_dashboard():
        periodo = request.args.get('periodo') or None
        formato = (request.args.get('formato') or 'excel').lower()
        data = repo.dashboard_data(periodo)
        if formato == 'pdf':
            path = generar_pdf_dashboard(data, module_reports, periodo)
        else:
            path = generar_excel_dashboard(data, module_reports, periodo)
        return jsonify({'message': 'Reporte generado.', 'archivo': os.path.basename(path)}), 200

    @bp.route('/reportes/<nombre_archivo>', methods=['GET'])
    def descargar_reporte(nombre_archivo: str):
        nombre_seguro = secure_filename(nombre_archivo)
        ruta = os.path.join(module_reports, nombre_seguro)
        if not os.path.exists(ruta):
            return jsonify({'error': 'Reporte no encontrado.'}), 404
        return send_from_directory(module_reports, nombre_seguro, as_attachment=True)

    @bp.route('/referencias/importar', methods=['POST'])
    def importar_referencias():
        if 'file' not in request.files:
            return jsonify({'error': 'Falta el archivo de referencias OMS/ICBF.'}), 400
        file = request.files['file']
        if not file.filename or not allowed_data_file(file.filename):
            return jsonify({'error': 'Carga un archivo Excel, CSV o TXT con referencias.'}), 400
        saved = save_upload(file, module_upload, 'REFERENCIAS')
        try:
            df = read_tabular_file(saved['ruta'])
            df.columns = [str(c).strip().lower() for c in df.columns]
            rows = []
            for _, row in df.iterrows():
                rows.append((
                    row.get('indicador') or row.get('indicator') or '',
                    row.get('sexo') or row.get('sex') or '',
                    row.get('edad_meses') or row.get('age_months') or None,
                    row.get('talla_cm') or row.get('height_cm') or None,
                    row.get('medida') or row.get('measure') or None,
                    row.get('sd3neg') or row.get('sd3neg') or None,
                    row.get('sd2neg') or None,
                    row.get('sd1neg') or None,
                    row.get('mediana') or row.get('median') or None,
                    row.get('sd1') or None,
                    row.get('sd2') or None,
                    row.get('sd3') or None,
                    saved['nombre_original'],
                    now_iso(),
                ))
            repo.execute_many(
                """
                INSERT INTO sn_referencias_oms
                (indicador, sexo, edad_meses, talla_cm, medida, sd3neg, sd2neg, sd1neg, mediana, sd1, sd2, sd3, fuente, fecha_carga)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            return jsonify({'message': f'Referencias importadas: {len(rows)}.'}), 201
        except Exception as exc:
            return jsonify({'error': f'No se pudieron importar referencias: {exc}'}), 400


    # ==============================================================
    # ALPHA51 — Entregables Salud y Nutrición
    # ============================================================== 
    @bp.route('/entregables/plantillas', methods=['GET'])
    @require_roles(*ENTREGABLES_READ_ROLES)
    def entregables_listar_plantillas():
        return jsonify({'plantillas': entregables_service.listar_plantillas(request.args.get('codigo'))}), 200

    @bp.route('/entregables/plantillas/<codigo>/<tipo>', methods=['POST'])
    @require_roles(*ENTREGABLES_EDIT_ROLES)
    def entregables_registrar_plantilla(codigo: str, tipo: str):
        archivo = request.files.get('file')
        if not archivo or not archivo.filename:
            return jsonify({'error': 'Seleccione una plantilla oficial.'}), 400
        try:
            plantilla = entregables_service.registrar_plantilla(codigo, tipo, archivo)
            return jsonify({
                'message': f'Plantilla oficial {tipo} registrada. Se preservarán su diseño, logos, tablas y hojas.',
                'plantilla': plantilla,
            }), 201
        except Exception as exc:
            return jsonify({'error': f'No se pudo registrar la plantilla oficial: {exc}'}), 400

    @bp.route('/entregables/catalogo', methods=['GET'])
    @require_roles(*ENTREGABLES_READ_ROLES)
    def entregables_catalogo():
        return jsonify({'catalogo': entregables_service.catalogo()}), 200

    @bp.route('/entregables/crear-mes', methods=['POST'])
    @require_roles(*ENTREGABLES_EDIT_ROLES)
    def entregables_crear_mes():
        data = request.get_json(silent=True) or request.form.to_dict() or {}
        try:
            result = entregables_service.crear_mes(data)
            return jsonify({'message': 'Entregables del mes creados o actualizados.', **result}), 201
        except Exception as exc:
            return jsonify({'error': f'No se pudieron crear entregables del mes: {exc}'}), 400

    @bp.route('/entregables', methods=['GET'])
    @require_roles(*ENTREGABLES_READ_ROLES)
    def entregables_listar():
        filtros = {
            'mes': request.args.get('mes') or None,
            'anio': request.args.get('anio') or None,
            'uds': request.args.get('uds') or None,
            'coordinador': request.args.get('coordinador') or None,
            'estado': request.args.get('estado') or None,
        }
        return jsonify(entregables_service.listar(filtros)), 200

    @bp.route('/entregables/<int:entregable_id>', methods=['GET'])
    @require_roles(*ENTREGABLES_READ_ROLES)
    def entregables_detalle(entregable_id: int):
        detalle = entregables_service.detalle(entregable_id)
        if not detalle:
            return jsonify({'error': 'Entregable no encontrado.'}), 404
        return jsonify({'entregable': detalle}), 200

    @bp.route('/entregables/<int:entregable_id>/actividades', methods=['POST'])
    @require_roles(*ENTREGABLES_EDIT_ROLES)
    def entregables_guardar_actividad(entregable_id: int):
        data = request.get_json(silent=True) or request.form.to_dict() or {}
        try:
            actividad = entregables_service.guardar_actividad(entregable_id, data)
            estado = 'confirmada' if actividad.get('confirmado') else 'guardada como borrador'
            return jsonify({'message': f'Actividad {estado}.', 'actividad': actividad}), 201
        except Exception as exc:
            return jsonify({'error': f'No se pudo guardar la actividad: {exc}'}), 400

    @bp.route('/entregables/<int:entregable_id>/acta', methods=['POST'])
    @require_roles(*ENTREGABLES_EDIT_ROLES)
    def entregables_generar_acta(entregable_id: int):
        try:
            archivo = entregables_service.generar_acta(entregable_id)
            return jsonify({'message': 'Acta generada correctamente.', 'archivo': archivo}), 201
        except Exception as exc:
            return jsonify({'error': f'No se pudo generar acta: {exc}'}), 400

    @bp.route('/entregables/<int:entregable_id>/listado', methods=['POST'])
    @require_roles(*ENTREGABLES_EDIT_ROLES)
    def entregables_generar_listado(entregable_id: int):
        try:
            archivo = entregables_service.generar_listado(entregable_id)
            return jsonify({'message': 'Listado generado correctamente.', 'archivo': archivo}), 201
        except Exception as exc:
            return jsonify({'error': f'No se pudo generar listado: {exc}'}), 400

    @bp.route('/entregables/<int:entregable_id>/oficio', methods=['POST'])
    @require_roles(*ENTREGABLES_EDIT_ROLES)
    def entregables_generar_oficio(entregable_id: int):
        try:
            archivo = entregables_service.generar_oficio(entregable_id)
            return jsonify({'message': 'Oficio generado correctamente.', 'archivo': archivo}), 201
        except Exception as exc:
            return jsonify({'error': f'No se pudo generar oficio: {exc}'}), 400

    @bp.route('/entregables/<int:entregable_id>/formato', methods=['POST'])
    @require_roles(*ENTREGABLES_EDIT_ROLES)
    def entregables_generar_formato(entregable_id: int):
        try:
            archivo = entregables_service.generar_formato(entregable_id)
            return jsonify({'message': 'Formato Excel generado correctamente.', 'archivo': archivo}), 201
        except Exception as exc:
            return jsonify({'error': f'No se pudo generar formato: {exc}'}), 400

    @bp.route('/entregables/<int:entregable_id>/evidencias', methods=['POST'])
    @require_roles(*ENTREGABLES_EDIT_ROLES)
    def entregables_subir_evidencias(entregable_id: int):
        files = request.files.getlist('files') or ([] if 'file' not in request.files else [request.files['file']])
        if not files:
            return jsonify({'error': 'No se recibieron evidencias.'}), 400
        meta = request.form.to_dict()
        subidas = []
        try:
            for f in files:
                if f and f.filename:
                    subidas.append(entregables_service.subir_evidencia(entregable_id, f, meta))
            return jsonify({'message': f'Evidencias cargadas: {len(subidas)}.', 'evidencias': subidas}), 201
        except Exception as exc:
            return jsonify({'error': f'No se pudieron cargar evidencias: {exc}'}), 400

    @bp.route('/entregables/<int:entregable_id>/validar', methods=['POST'])
    @require_roles(*ENTREGABLES_EDIT_ROLES)
    def entregables_validar(entregable_id: int):
        try:
            result = entregables_service.validar(entregable_id)
            status = 200 if result.get('valido') else 409
            message = 'Entregable completo.' if result.get('valido') else 'Entregable con pendientes.'
            return jsonify({'message': message, **result}), status
        except Exception as exc:
            return jsonify({'error': f'No se pudo validar entregable: {exc}'}), 400

    @bp.route('/entregables/matriz', methods=['POST'])
    @require_roles(*ENTREGABLES_EDIT_ROLES)
    def entregables_matriz():
        data = request.get_json(silent=True) or request.form.to_dict() or {}
        try:
            archivo = entregables_service.generar_matriz(data)
            return jsonify({'message': 'Matriz de control generada.', 'archivo': archivo}), 201
        except Exception as exc:
            return jsonify({'error': f'No se pudo generar matriz: {exc}'}), 400

    @bp.route('/entregables/informe', methods=['POST'])
    @require_roles(*ENTREGABLES_EDIT_ROLES)
    def entregables_informe():
        data = request.get_json(silent=True) or request.form.to_dict() or {}
        try:
            archivo = entregables_service.generar_informe(data)
            return jsonify({'message': 'Informe consolidado generado.', 'archivo': archivo}), 201
        except Exception as exc:
            return jsonify({'error': f'No se pudo generar informe: {exc}'}), 400

    @bp.route('/entregables/zip', methods=['POST'])
    @require_roles(*ENTREGABLES_EDIT_ROLES)
    def entregables_zip():
        data = request.get_json(silent=True) or request.form.to_dict() or {}
        try:
            archivo = entregables_service.generar_zip(data)
            return jsonify({'message': 'Paquete ZIP generado.', 'archivo': archivo}), 201
        except Exception as exc:
            return jsonify({'error': f'No se pudo generar ZIP: {exc}'}), 400

    @bp.route('/entregables/archivo/<int:archivo_id>', methods=['GET'])
    @require_roles(*ENTREGABLES_READ_ROLES)
    def entregables_descargar_archivo(archivo_id: int):
        archivo = entregables_service.archivo(archivo_id)
        if not archivo or not archivo.get('ruta_archivo') or not os.path.exists(archivo['ruta_archivo']):
            return jsonify({'error': 'Archivo no encontrado.'}), 404
        return send_file(archivo['ruta_archivo'], as_attachment=True, download_name=archivo.get('nombre_archivo') or os.path.basename(archivo['ruta_archivo']))

    app.register_blueprint(bp)
