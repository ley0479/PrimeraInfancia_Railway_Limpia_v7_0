"""Rutas Flask del Calendario Inteligente de Entregables y Alertas Operativas."""
from __future__ import annotations

import os
from datetime import date

from flask import Blueprint, g, jsonify, request, send_from_directory, send_file
from modules.seguridad.tenant_context import tenant_path
from modules.runtime_schema import migration_mode
from werkzeug.utils import secure_filename
from modules.operational_jobs import start_job

from .repository import CalendarioInteligenteRepository
from .services import parse_fecha

ALLOWED_CRONOGRAMA = {".xlsx", ".xls", ".xlsm", ".ods", ".csv", ".txt", ".tsv", ".tab", ".dat", ".docx", ".pdf", ".pptx", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
ALLOWED_EVIDENCE = {".pdf", ".doc", ".docx", ".xlsx", ".xls", ".xlsm", ".csv", ".txt", ".png", ".jpg", ".jpeg", ".zip", ".rar"}


def _json_payload() -> dict:
    return request.get_json(silent=True) or {}


def _filters_from_request() -> dict:
    return {
        "periodo": request.args.get("periodo"),
        "anio": request.args.get("anio"),
        "coordinador": request.args.get("coordinador"),
        "unidad": request.args.get("unidad"),
        "modulo": request.args.get("modulo"),
        "estado": request.args.get("estado"),
        "responsable_nombre": request.args.get("responsable"),
        "municipio": request.args.get("municipio"),
        "fecha": request.args.get("fecha"),
    }


def _current_user() -> dict:
    return dict(getattr(g, "current_user", None) or {})


def _can_manage_checklist(user: dict) -> bool:
    return str(user.get("rol") or "").upper() in {"SUPERADMIN", "GERENTE", "COORDINADOR", "AUXILIAR_ADMINISTRATIVO"}


def _owns_target(repo, entity: str, entity_id: int, user: dict) -> bool:
    if _can_manage_checklist(user):
        return True
    target = repo.get_entregable(entity_id) if entity == "ENTREGABLE" else repo.get_asignacion(entity_id)
    if not target:
        return False
    names = {str(user.get("username") or "").casefold(), str(user.get("nombre_completo") or "").casefold()}
    return int(target.get("responsable_id") or 0) == int(user.get("id") or 0) or str(target.get("responsable_nombre") or "").casefold() in names


def register_calendario_inteligente(app, database_path: str, upload_folder: str) -> None:
    repo = CalendarioInteligenteRepository(database_path, upload_folder)
    repo.init_schema(force=migration_mode())
    # La ruta se resuelve al usarla, dentro del tenant autenticado.
    module_upload = tenant_path(upload_folder, "calendario_inteligente")

    bp = Blueprint("calendario_inteligente", __name__, url_prefix="/api/calendario-inteligente")

    @bp.route("/dashboard", methods=["GET"])
    def dashboard():
        periodo = request.args.get("periodo") or date.today().isoformat()[:7]
        anio = request.args.get("anio") or periodo[:4]
        filters = {k: v for k, v in _filters_from_request().items() if v and k not in {"periodo", "anio"}}
        return jsonify(repo.dashboard(periodo=periodo, anio=anio, filters=filters)), 200

    @bp.route("/catalogos", methods=["GET"])
    def catalogos():
        return jsonify(repo.catalogos()), 200

    @bp.route("/mis-pendientes", methods=["GET"])
    def mis_pendientes():
        user = _current_user()
        if not user.get("id"):
            return jsonify({"error": "Usuario no autenticado."}), 401
        return jsonify({"pendientes": repo.list_mis_pendientes(user)}), 200

    @bp.route("/cumplimiento", methods=["GET"])
    def cumplimiento():
        periodo = request.args.get("periodo") or date.today().isoformat()[:7]
        return jsonify(repo.tablero_cumplimiento(periodo)), 200

    @bp.route("/checklist", methods=["GET", "POST"])
    def checklist():
        user = _current_user()
        if request.method == "GET":
            periodo = request.args.get("periodo") or date.today().isoformat()[:7]
            return jsonify(repo.list_checklist(periodo, user)), 200
        if not _can_manage_checklist(user):
            return jsonify({"error": "No tienes permiso para crear obligaciones institucionales."}), 403
        try:
            assignment = repo.create_obligacion(_json_payload(), user)
            return jsonify({"message": "Obligación y asignación creadas.", "asignacion": assignment}), 201
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 422

    @bp.route("/checklist/<int:assignment_id>/estado", methods=["PATCH"])
    def checklist_estado(assignment_id: int):
        user = _current_user()
        data = _json_payload()
        state = str(data.get("estado") or "").upper()
        current = repo.get_asignacion(assignment_id)
        if not current:
            return jsonify({"error": "Asignación no encontrada."}), 404
        if not _can_manage_checklist(user):
            names = {str(user.get("username") or "").casefold(), str(user.get("nombre_completo") or "").casefold()}
            owns = int(current.get("responsable_id") or 0) == int(user.get("id") or 0) or str(current.get("responsable_nombre") or "").casefold() in names
            if not owns:
                return jsonify({"error": "No tienes acceso a esta asignación."}), 403
        if state in {"APROBADO", "DEVUELTO", "NO_APLICA"} and not _can_manage_checklist(user):
            return jsonify({"error": "Este estado requiere rol de coordinación."}), 403
        try:
            updated = repo.update_asignacion_estado(assignment_id, state, data.get("motivo") or data.get("justificacion") or "", user)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 422
        if not updated:
            return jsonify({"error": "Asignación no encontrada."}), 404
        return jsonify({"message": "Estado actualizado.", "asignacion": updated}), 200

    @bp.route("/checklist/importar", methods=["POST"])
    def importar_checklist():
        user = _current_user()
        if not _can_manage_checklist(user):
            return jsonify({"error": "No tienes permiso para importar listas institucionales."}), 403
        file = request.files.get("file")
        if not file or not file.filename:
            return jsonify({"error": "Archivo de lista de chequeo requerido."}), 400
        ext = os.path.splitext(file.filename.lower())[1]
        if ext not in ALLOWED_CRONOGRAMA:
            return jsonify({"error": "Formato no soportado. Usa Word, Excel, PowerPoint o PDF."}), 422
        original = file.filename
        saved = f"CHECKLIST_{date.today().isoformat()}_{secure_filename(original)}"
        path = os.path.join(module_upload, saved)
        file.save(path)
        try:
            preview = repo.registrar_preview_cronograma(path, original, usuario=user.get("username") or "sistema")
        except Exception as exc:
            return jsonify({"error": f"No se pudo leer la lista de chequeo: {exc}"}), 422
        propuestas = []
        for item in preview.get("actividades") or []:
            propuestas.append({
                "componente": item.get("componente") or "",
                "numero": item.get("numero") or "",
                "actividad": item.get("titulo") or "",
                "responsables_sugeridos": item.get("responsable_nombre") or "",
                "entregables": item.get("entregables") or "",
                "fecha_sugerida": item.get("fecha_limite") or None,
                "fecha_estado": "ASIGNADA" if item.get("fecha_limite") else "PENDIENTE_ASIGNACION",
                "origen": original,
                "confianza": item.get("confianza", 0),
                "errores": item.get("errores") or [],
            })
        auto_confirmar = str(request.form.get("auto_confirmar") or "").lower() in {"1", "true", "si", "sí"}
        checklist_result = None
        calendar_result = None
        if auto_confirmar:
            checklist_result = repo.confirmar_importacion_checklist(preview["cronograma_id"], propuestas, request.form.get("periodo") or date.today().isoformat()[:7], user)
            validas = [item for item in (preview.get("actividades") or []) if item.get("fecha_limite") and item.get("titulo")]
            calendar_result = repo.confirmar_cronograma(preview["cronograma_id"], validas, usuario=user.get("username") or "sistema")
        return jsonify({
            "message": "Lista incorporada al checklist y al calendario." if auto_confirmar else "Lista detectada. Revisa las propuestas antes de incorporarlas.",
            "importacion_id": preview["cronograma_id"], "propuestas": propuestas,
            "resultado": checklist_result, "resultado_calendario": calendar_result,
        }), 200

    @bp.route("/checklist/importar/<int:importacion_id>/confirmar", methods=["POST"])
    def confirmar_importacion_checklist(importacion_id: int):
        user = _current_user()
        if not _can_manage_checklist(user):
            return jsonify({"error": "No tienes permiso para confirmar importaciones."}), 403
        data = _json_payload()
        try:
            result = repo.confirmar_importacion_checklist(importacion_id, data.get("propuestas") or [], data.get("periodo") or date.today().isoformat()[:7], user)
            actividades = [{
                "fecha_limite": item.get("fecha_sugerida") or item.get("fecha"),
                "titulo": item.get("actividad") or item.get("titulo"),
                "componente": item.get("componente") or "Checklist institucional",
                "responsable_nombre": item.get("responsable_nombre") or "",
                "entregables": item.get("entregables") or "",
                "descartar": bool(item.get("ignorar") or item.get("descartar")),
            } for item in (data.get("propuestas") or [])]
            calendar_result = repo.confirmar_cronograma(importacion_id, actividades, usuario=user.get("username") or "sistema")
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 422
        return jsonify({"message": "Propuestas incorporadas al checklist y al calendario.", "resultado": result, "resultado_calendario": calendar_result}), 201

    @bp.route("/entregables", methods=["GET", "POST"])
    def entregables():
        if request.method == "GET":
            filters = {k: v for k, v in _filters_from_request().items() if v}
            return jsonify({"entregables": repo.list_entregables(filters)}), 200
        data = _json_payload()
        user = _current_user()
        data["usuario_creador_id"] = user.get("id")
        data["creado_por"] = user.get("username") or user.get("email") or "sistema"
        if not data.get("responsable_id") and not data.get("responsable_nombre"):
            data["responsable_id"] = user.get("id")
            data["responsable_nombre"] = user.get("nombre_completo") or user.get("nombre") or user.get("username") or user.get("email")
        try:
            created = repo.create_recurrentes(data, origen="manual")
            return jsonify({
                "message": "Entregable creado correctamente." if len(created) == 1 else f"Serie creada con {len(created)} actividades.",
                "entregable": created[0],
                "entregables": created,
                "total_creados": len(created),
            }), 201
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400

    @bp.route("/entregables/<int:entregable_id>", methods=["GET", "PUT", "PATCH", "DELETE"])
    def entregable_detalle(entregable_id: int):
        if request.method == "GET":
            entregable = repo.get_entregable(entregable_id)
            if not entregable:
                return jsonify({"error": "Entregable no encontrado."}), 404
            return jsonify({"entregable": entregable}), 200
        if request.method in {"PUT", "PATCH"}:
            try:
                updated = repo.update_entregable(entregable_id, _json_payload())
            except Exception as exc:
                return jsonify({"error": str(exc)}), 400
            if not updated:
                return jsonify({"error": "Entregable no encontrado."}), 404
            return jsonify({"message": "Entregable actualizado.", "entregable": updated}), 200
        if not repo.delete_entregable(entregable_id):
            return jsonify({"error": "Entregable no encontrado."}), 404
        return jsonify({"message": "Entregable eliminado."}), 200

    @bp.route("/entregables/<int:entregable_id>/entregar", methods=["POST"])
    def marcar_entregado(entregable_id: int):
        data = request.form.to_dict() if request.form else _json_payload()
        updated = repo.marcar_entregado(entregable_id, observaciones=data.get("observaciones"))
        if not updated:
            return jsonify({"error": "Entregable no encontrado."}), 404
        return jsonify({"message": "Entregable marcado como entregado.", "entregable": updated}), 200

    @bp.route("/cargar-cronograma", methods=["POST"])
    def cargar_cronograma():
        if "file" not in request.files:
            return jsonify({"error": "Archivo requerido."}), 400
        file = request.files["file"]
        if not file.filename:
            return jsonify({"error": "Archivo sin nombre."}), 400
        ext = os.path.splitext(file.filename.lower())[1]
        if ext not in ALLOWED_CRONOGRAMA:
            return jsonify({"error": "Extensión no permitida para cronograma. Usa Excel, CSV, TXT, Word, PDF, PowerPoint o imagen."}), 400
        original_filename = file.filename
        saved = f"CRONOGRAMA_{date.today().isoformat()}_{secure_filename(original_filename)}"
        path = os.path.join(module_upload, saved)
        file.save(path)

        usuario = request.form.get("usuario") or request.headers.get("X-User-Name") or "sistema"
        auto_confirmar = str(request.form.get("auto_confirmar") or request.args.get("auto_confirmar") or "").lower() in {"1", "true", "si", "sí"}
        # ALPHA33: por defecto NO guarda actividades. Primero devuelve vista previa editable.
        guardar_directo = str(request.args.get("guardar_directo") or request.form.get("guardar_directo") or "").lower() in {"1", "true", "si", "sí"}
        if not guardar_directo:
            try:
                preview = repo.registrar_preview_cronograma(path, original_filename, usuario=usuario)
            except Exception as exc:
                return jsonify({
                    "error": f"No se pudo leer el cronograma cargado: {exc}",
                    "archivo": saved,
                    "recomendacion": "Verifique que el documento tenga fecha, actividad, módulo/responsable o que la imagen tenga texto legible. Si es foto o PDF escaneado, revise OCR/Tesseract."
                }), 400
            resultado = None
            if auto_confirmar:
                validas = [item for item in (preview.get("actividades") or []) if item.get("fecha_limite") and item.get("titulo")]
                resultado = repo.confirmar_cronograma(preview["cronograma_id"], validas, usuario=usuario)
            return jsonify({
                "message": "Cronograma leído y actividades incorporadas al calendario." if auto_confirmar else "Cronograma leído. Revisa la vista previa antes de guardar en calendario.",
                "archivo": saved,
                "cronograma_id": preview.get("cronograma_id"),
                "preview": preview,
                "resultado": resultado,
                "modo": "preview",
            }), 200

        sync_mode = str(request.args.get("sync") or request.form.get("sync") or "").lower() in {"1", "true", "si", "sí"}
        if sync_mode:
            try:
                result = repo.import_cronograma(path, original_filename)
            except Exception as exc:
                return jsonify({
                    "error": f"No se pudo leer el cronograma cargado: {exc}",
                    "archivo": saved,
                    "recomendacion": "Verifique que el documento tenga fecha, actividad, módulo/responsable o que la imagen tenga texto legible."
                }), 400
            return jsonify({"message": "Cronograma procesado.", "archivo": saved, "resultado": result}), 200

        def _job(update):
            update(progreso=10, etapa="Leyendo cronograma", log=f"Archivo: {original_filename}")
            result = repo.import_cronograma(path, original_filename)
            update(progreso=100, etapa="Cronograma procesado")
            return {"message": "Cronograma procesado.", "archivo": saved, "resultado": result}

        job = start_job(
            "cargar_cronograma_calendario",
            _job,
            metadata={"archivo": saved, "ruta": path},
            descripcion="Carga de cronograma mensual al calendario inteligente",
        )
        return jsonify({
            "message": "Cronograma recibido. Se está procesando en segundo plano para evitar errores por túnel.",
            "job_id": job["id"],
            "job": job,
            "status_url": f"/api/jobs/{job['id']}",
            "archivo": saved,
            "modo": "segundo_plano",
        }), 202

    @bp.route("/confirmar-cronograma", methods=["POST"])
    def confirmar_cronograma():
        data = _json_payload()
        cronograma_id = int(data.get("cronograma_id") or 0)
        if not cronograma_id:
            return jsonify({"error": "cronograma_id es obligatorio."}), 400
        usuario = data.get("usuario") or request.headers.get("X-User-Name") or "sistema"
        try:
            result = repo.confirmar_cronograma(cronograma_id, data.get("actividades") or [], usuario=usuario)
            return jsonify({"message": "Cronograma guardado en calendario.", "resultado": result}), 200
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400

    @bp.route("/exportar-excel", methods=["GET"])
    def exportar_excel():
        filters = {k: v for k, v in _filters_from_request().items() if v}
        try:
            out_path = repo.exportar_cronograma_excel(filters)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400
        return send_file(out_path, as_attachment=True, download_name=os.path.basename(out_path))

    @bp.route("/exportar-pdf", methods=["GET"])
    def exportar_pdf():
        filters = {k: v for k, v in _filters_from_request().items() if v}
        try:
            out_path = repo.exportar_cronograma_pdf(filters)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400
        return send_file(out_path, as_attachment=True, download_name=os.path.basename(out_path))

    @bp.route("/evidencias/upload", methods=["POST"])
    def subir_evidencia():
        files = request.files.getlist("files") or request.files.getlist("file")
        if not files:
            return jsonify({"error": "Archivo requerido."}), 400
        entregable_id = request.form.get("entregable_id", type=int)
        if not entregable_id:
            return jsonify({"error": "entregable_id es obligatorio."}), 400
        return _upload_evidencias("ENTREGABLE", entregable_id, files)

    def _upload_evidencias(entity: str, entity_id: int, files=None):
        user = _current_user()
        entity = str(entity).upper()
        if entity not in {"ENTREGABLE", "CHECKLIST"}:
            return jsonify({"error": "Tipo de entidad no permitido."}), 422
        if not _owns_target(repo, entity, entity_id, user):
            return jsonify({"error": "No tienes acceso a esta actividad."}), 403
        files = files or request.files.getlist("files") or request.files.getlist("file")
        if not files:
            return jsonify({"error": "Selecciona al menos un archivo."}), 400
        if len(files) > 10:
            return jsonify({"error": "Puedes cargar máximo 10 archivos por operación."}), 422
        saved = []
        try:
            for file in files:
                saved.append(repo.add_evidencia(entity, entity_id, request.form.get("requisito_id", type=int), file, request.form.get("descripcion") or "", user))
        except LookupError as exc:
            return jsonify({"error": str(exc)}), 404
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 422
        return jsonify({"message": f"{len(saved)} evidencia(s) cargada(s).", "evidencias": saved}), 201

    @bp.route("/evidencias/<string:entity>/<int:entity_id>", methods=["GET", "POST"])
    def evidencias_entidad(entity: str, entity_id: int):
        entity = entity.upper()
        if entity not in {"ENTREGABLE", "CHECKLIST"}:
            return jsonify({"error": "Tipo de entidad no permitido."}), 422
        if not _owns_target(repo, entity, entity_id, _current_user()):
            return jsonify({"error": "No tienes acceso a esta actividad."}), 403
        if request.method == "POST":
            return _upload_evidencias(entity, entity_id)
        return jsonify({"evidencias": repo.list_evidencias(entity, entity_id)}), 200

    @bp.route("/evidencias/<string:entity>/<int:entity_id>/enviar", methods=["POST"])
    def enviar_evidencias(entity: str, entity_id: int):
        entity = entity.upper()
        if not _owns_target(repo, entity, entity_id, _current_user()):
            return jsonify({"error": "No tienes acceso a esta actividad."}), 403
        try:
            result = repo.enviar_evidencias_revision(entity, entity_id)
        except LookupError as exc:
            return jsonify({"error": str(exc)}), 404
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 422
        return jsonify({"message": "Evidencias enviadas a revisión.", "resultado": result}), 200

    @bp.route("/evidencias/<string:entity>/<int:entity_id>/revision", methods=["PATCH"])
    def revisar_evidencias(entity: str, entity_id: int):
        user = _current_user()
        if not _can_manage_checklist(user):
            return jsonify({"error": "La revisión requiere rol de coordinación."}), 403
        data = _json_payload()
        try:
            result = repo.revisar_evidencias(entity, entity_id, data.get("decision"), data.get("observacion") or "", user)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 422
        if not result.get("actualizadas"):
            return jsonify({"error": "No hay evidencias nuevas pendientes de revisión."}), 409
        return jsonify({"message": "Revisión registrada.", "resultado": result}), 200

    @bp.route("/evidencias/<int:evidence_id>/descargar", methods=["GET"])
    def descargar_evidencia_id(evidence_id: int):
        evidence = repo.get_evidencia(evidence_id)
        if not evidence or not _owns_target(repo, evidence["entidad_tipo"], int(evidence["entidad_id"]), _current_user()):
            return jsonify({"error": "Evidencia no encontrada o sin acceso."}), 404
        resolved = repo.evidencia_path(evidence_id)
        if not resolved:
            return jsonify({"error": "El archivo no existe o no superó la verificación de integridad."}), 404
        path, original, mime = resolved
        return send_file(path, as_attachment=True, download_name=original, mimetype=mime)

    @bp.route("/evidencias/<path:nombre>", methods=["GET"])
    def descargar_evidencia(nombre: str):
        return send_from_directory(module_upload, nombre, as_attachment=True)

    @bp.route("/sincronizar-entrega", methods=["POST"])
    def sincronizar_entrega():
        try:
            entregable = repo.sincronizar_entrega(_json_payload())
            return jsonify({"message": "Calendario actualizado desde módulo operativo.", "entregable": entregable}), 200
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400


    # ALPHA33: alias compatibles con el requerimiento /api/calendario sin retirar rutas existentes.
    alias_bp = Blueprint("calendario_alias", __name__, url_prefix="/api/calendario")

    @alias_bp.route("/cargar-cronograma", methods=["POST"])
    def alias_cargar_cronograma():
        return cargar_cronograma()

    @alias_bp.route("/confirmar-cronograma", methods=["POST"])
    def alias_confirmar_cronograma():
        return confirmar_cronograma()

    @alias_bp.route("/actividades", methods=["GET"])
    def alias_actividades():
        filters = {k: v for k, v in _filters_from_request().items() if v}
        return jsonify({"actividades": repo.list_entregables(filters)}), 200

    @alias_bp.route("/resumen", methods=["GET"])
    def alias_resumen():
        periodo = request.args.get("periodo") or date.today().isoformat()[:7]
        anio = request.args.get("anio") or periodo[:4]
        filters = {k: v for k, v in _filters_from_request().items() if v and k not in {"periodo", "anio"}}
        data = repo.dashboard(periodo=periodo, anio=anio, filters=filters)
        return jsonify({"resumen": data.get("resumen"), "alertas": data.get("alertas")}), 200

    @alias_bp.route("/actividad/<int:entregable_id>", methods=["PUT", "PATCH"])
    def alias_actualizar_actividad(entregable_id: int):
        try:
            updated = repo.update_entregable(entregable_id, _json_payload())
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400
        if not updated:
            return jsonify({"error": "Actividad no encontrada."}), 404
        return jsonify({"message": "Actividad actualizada.", "actividad": updated}), 200

    @alias_bp.route("/actividad/<int:entregable_id>/entregar", methods=["POST"])
    def alias_entregar_actividad(entregable_id: int):
        return marcar_entregado(entregable_id)

    @alias_bp.route("/actividad/<int:entregable_id>", methods=["DELETE"])
    def alias_eliminar_actividad(entregable_id: int):
        if not repo.delete_entregable(entregable_id):
            return jsonify({"error": "Actividad no encontrada."}), 404
        return jsonify({"message": "Actividad eliminada."}), 200

    @alias_bp.route("/exportar-excel", methods=["GET"])
    def alias_exportar_excel():
        return exportar_excel()

    @alias_bp.route("/exportar-pdf", methods=["GET"])
    def alias_exportar_pdf():
        return exportar_pdf()

    app.register_blueprint(bp)
    app.register_blueprint(alias_bp)
