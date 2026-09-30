from __future__ import annotations

import os
import zipfile
from pathlib import Path

from flask import Blueprint, g, jsonify, request, send_file

from modules.seguridad.services import require_roles
from modules.seguridad.tenant_context import current_tenant_id
from modules.seguridad.tenant_context import tenant_path
from modules.importaciones_universales.repository import UniversalImportRepository
from modules.calendario_inteligente.repository import CalendarioInteligenteRepository

from .generator import generate_pages, template_sha256
from .repository import ProgramasIcbfRepository, json_hash

ROLES = ("SUPERADMIN", "GERENTE", "COORDINADOR", "AUXILIAR_ADMINISTRATIVO", "NUTRICIONISTA")
WRITE_ROLES = ("SUPERADMIN", "GERENTE", "AUXILIAR_ADMINISTRATIVO", "NUTRICIONISTA")


def register_programas_icbf(app, database_path: str, output_folder: str | None = None) -> None:
    enabled = str(app.config.get("ENABLE_ICBF_MULTIPROGRAM", os.getenv("ENABLE_ICBF_MULTIPROGRAM", "false"))).lower() in {"1", "true", "yes", "si", "sí", "on"}
    if not enabled:
        return
    UniversalImportRepository(database_path).init_schema()
    repo = ProgramasIcbfRepository(database_path)
    repo.init_schema()
    bp = Blueprint("programas_icbf", __name__, url_prefix="/api/programas-icbf")

    def context():
        user = getattr(g, "current_user", {}) or {}
        return int(current_tenant_id(user.get("fundacion_id") or 1) or 1), user.get("id")

    def public_generation(item: dict) -> dict:
        data = dict(item)
        generation_id = int(data["id"])
        data["archivos"] = [
            {**{key: value for key, value in file.items() if key != "path"}, "descarga": f"/api/programas-icbf/generaciones/{generation_id}/archivos/{index}"}
            for index, file in enumerate(data.get("archivos") or [])
        ]
        data["paquete_descarga"] = f"/api/programas-icbf/generaciones/{generation_id}/paquete" if len(data["archivos"]) > 1 else None
        return data

    @bp.get("/perfiles")
    @require_roles(*ROLES)
    def profiles():
        tenant, _ = context()
        return jsonify({"perfiles": repo.list_profiles(tenant)})

    @bp.get("/perfiles/<int:profile_id>/cargas")
    @require_roles(*ROLES)
    def list_loads(profile_id):
        tenant, _ = context()
        return jsonify({"cargas": repo.list_loads(tenant, profile_id)})

    @bp.get("/perfiles/<int:profile_id>/comunidades")
    @require_roles(*ROLES)
    def list_communities(profile_id):
        tenant, _ = context()
        return jsonify({"comunidades": repo.list_communities(tenant, profile_id)})

    @bp.post("/perfiles/servicio-integrado")
    @require_roles(*WRITE_ROLES)
    def ensure_profile():
        tenant, user_id = context()
        return jsonify(repo.ensure_profile(tenant, user_id)), 201

    @bp.post("/perfiles")
    @require_roles("SUPERADMIN", "GERENTE")
    def register_profile():
        tenant, user_id = context()
        try:
            return jsonify(repo.register_profile(tenant, request.get_json(silent=True) or {}, user_id)), 201
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    @bp.put("/perfiles/<int:profile_id>/estado")
    @require_roles("SUPERADMIN", "GERENTE")
    def update_profile_state(profile_id):
        tenant, user_id = context()
        body = request.get_json(silent=True) or {}
        production_allowed = str(app.config.get("ENABLE_ICBF_MULTIPROGRAM_PRODUCTION", os.getenv("ENABLE_ICBF_MULTIPROGRAM_PRODUCTION", "false"))).lower() in {"1", "true", "yes", "si", "sí", "on"}
        try:
            return jsonify(repo.set_profile_state(tenant, profile_id, body.get("estado"), user_id, allow_active=production_allowed))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 409

    @bp.put("/perfiles/<int:profile_id>/orden")
    @require_roles(*WRITE_ROLES)
    def update_order(profile_id):
        tenant, user_id = context()
        try:
            return jsonify(repo.set_sort_criterion(tenant, profile_id, (request.get_json(silent=True) or {}).get("criterio"), user_id))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    @bp.post("/perfiles/<int:profile_id>/cargas")
    @require_roles(*WRITE_ROLES)
    def create_load(profile_id):
        tenant, user_id = context()
        try:
            return jsonify(repo.create_snapshot(tenant, profile_id, int((request.get_json(silent=True) or {}).get("importacion_id") or 0), user_id)), 201
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    @bp.get("/cargas/<int:load_id>")
    @require_roles(*ROLES)
    def get_load(load_id):
        tenant, _ = context()
        try:
            return jsonify(repo.get_load(tenant, load_id))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 404

    @bp.get("/cargas/<int:load_id>/participantes")
    @require_roles(*ROLES)
    def participants(load_id):
        tenant, _ = context()
        pending = str(request.args.get("sin_comunidad") or "").lower() in {"1", "true", "si", "sí"}
        return jsonify({"participantes": repo.list_participants(tenant, load_id, pending)})

    @bp.post("/perfiles/<int:profile_id>/comunidades")
    @require_roles(*WRITE_ROLES)
    def create_community(profile_id):
        tenant, user_id = context()
        body = request.get_json(silent=True) or {}
        try:
            return jsonify(repo.create_community(tenant, profile_id, body.get("nombre"), body.get("codigo"), user_id)), 201
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    @bp.put("/cargas/<int:load_id>/participantes/<int:participant_id>/comunidad")
    @require_roles(*WRITE_ROLES)
    def assign(load_id, participant_id):
        tenant, user_id = context()
        body = request.get_json(silent=True) or {}
        try:
            return jsonify(repo.assign_community(tenant, load_id, participant_id, int(body.get("comunidad_id") or 0), user_id, body.get("motivo")))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    @bp.post("/cargas/<int:load_id>/generar")
    @require_roles(*WRITE_ROLES)
    def generate(load_id):
        tenant, user_id = context()
        body = request.get_json(silent=True) or {}
        format_code = str(body.get("formato") or "").strip().upper()
        period = str(body.get("periodo") or "").strip()
        community_id = int(body.get("comunidad_id") or 0)
        if format_code not in {"RFPP", "F2"} or not period or not community_id:
            return jsonify({"error": "Formato, periodo y comunidad son obligatorios."}), 400
        config_key = "ICBF_RFPP_TEMPLATE_PATH" if format_code == "RFPP" else "ICBF_F2_TEMPLATE_PATH"
        template = Path(str(app.config.get(config_key) or os.getenv(config_key, "")))
        if not template.is_file():
            return jsonify({"error": f"La plantilla {format_code} aún no está configurada en almacenamiento autorizado."}), 409
        try:
            generation_context = repo.generation_context(tenant, load_id, community_id)
            header = dict(body.get("encabezado") or {})
            activity_link_id = int(body.get("actividad_vinculada_id") or 0) or None
            facts = repo.confirmed_delivery_facts(tenant, activity_link_id, load_id, community_id) if activity_link_id else {}
            template_sha = template_sha256(template)
            request_sha = json_hash({"fundacion_id": tenant, "load_snapshot": generation_context["load"]["snapshot_sha256"], "community_id": community_id, "format": format_code, "period": period, "criterion": generation_context["load"]["criterio_orden"], "template": template_sha, "header": header, "activity_link_id": activity_link_id, "facts": facts})
            existing = repo.find_generation(tenant, request_sha)
            if existing:
                return jsonify(public_generation(existing)), 200
            root = tenant_path(output_folder or app.config.get("OUTPUT_FOLDER") or "outputs", "programas_icbf", request_sha[:16])
            files = generate_pages(format_code, template, root, generation_context["community"]["nombre"], generation_context["participants"], generation_context["load"]["criterio_orden"], header, facts)
            pending = ["hechos_de_entrega", "asistencia_recepcion", "firmas_huellas"]
            if format_code == "F2":
                pending.extend(["productos_lotes", "cantidades", "receptor_confirmado"])
            saved = repo.save_generation(tenant, generation_context, format_code, period, template_sha, request_sha, files, pending, user_id)
            return jsonify(public_generation(saved)), 201
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 409

    @bp.get("/generaciones/<int:generation_id>/archivos/<int:file_index>")
    @require_roles(*ROLES)
    def download_generation(generation_id, file_index):
        tenant, _ = context()
        try:
            generation = repo.get_generation(tenant, generation_id)
            files = generation["archivos"]
            if file_index < 0 or file_index >= len(files):
                raise ValueError("Archivo no encontrado.")
            path = Path(files[file_index]["path"]).resolve()
            allowed = Path(os.fspath(tenant_path(output_folder or app.config.get("OUTPUT_FOLDER") or "outputs", "programas_icbf"))).resolve()
            if allowed not in path.parents or not path.is_file():
                raise ValueError("Archivo no disponible en el almacenamiento autorizado.")
            return send_file(path, as_attachment=True, download_name=files[file_index]["filename"])
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 404

    @bp.get("/generaciones/<int:generation_id>/paquete")
    @require_roles(*ROLES)
    def download_generation_package(generation_id):
        tenant, _ = context()
        try:
            generation = repo.get_generation(tenant, generation_id)
            files = generation["archivos"]
            if len(files) < 2:
                raise ValueError("Esta generación no requiere un paquete de archivos.")
            allowed = Path(os.fspath(tenant_path(output_folder or app.config.get("OUTPUT_FOLDER") or "outputs", "programas_icbf"))).resolve()
            resolved = []
            for item in files:
                path = Path(item["path"]).resolve()
                if allowed not in path.parents or not path.is_file():
                    raise ValueError("Uno o más archivos del paquete ya no están disponibles.")
                resolved.append((path, str(item.get("filename") or path.name)))
            package = resolved[0][0].parent / f"paquete_{generation_id}_{generation['formato']}.zip"
            temporary = package.with_suffix(".zip.tmp")
            with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for path, filename in resolved:
                    archive.write(path, arcname=filename)
            temporary.replace(package)
            return send_file(package, as_attachment=True, download_name=f"{generation['formato']}_generacion_{generation_id}.zip")
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 404

    @bp.post("/perfiles/<int:profile_id>/puntos-entrega")
    @require_roles(*WRITE_ROLES)
    def save_delivery_point(profile_id):
        tenant, user_id = context()
        try:
            return jsonify(repo.save_delivery_point(tenant, profile_id, request.get_json(silent=True) or {}, user_id)), 201
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    @bp.post("/perfiles/<int:profile_id>/actividades-vinculadas")
    @require_roles(*WRITE_ROLES)
    def link_activity(profile_id):
        tenant, user_id = context()
        body = request.get_json(silent=True) or {}
        try:
            result = repo.link_health_activity(tenant, profile_id, int(body.get("carga_id") or 0), int(body.get("comunidad_id") or 0), int(body.get("actividad_salud_id") or 0), body.get("periodo"), int(body.get("punto_entrega_id") or 0) or None, user_id)
            calendar_payload = repo.calendar_payload(tenant, int(result["id"]))
            calendar = calendar_payload
            if calendar_payload.get("estado") != "PENDIENTE_FECHA":
                calendar_repo = CalendarioInteligenteRepository(database_path)
                calendar_repo.init_schema()
                existing = calendar_repo.find_by_clave(calendar_payload["clave_unica"])
                calendar = existing or calendar_repo.create_entregable(calendar_payload, origen="programas_icbf")
            return jsonify({"vinculacion": result, "calendario": calendar}), 201
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    @bp.post("/actividades-vinculadas/<int:activity_link_id>/entregas")
    @require_roles(*WRITE_ROLES)
    def create_delivery(activity_link_id):
        tenant, user_id = context()
        body = request.get_json(silent=True) or {}
        try:
            return jsonify(repo.create_delivery_draft(tenant, activity_link_id, int(body.get("participante_id") or 0), body, user_id)), 201
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    @bp.post("/entregas/<int:delivery_id>/confirmar")
    @require_roles(*WRITE_ROLES)
    def confirm_delivery(delivery_id):
        tenant, user_id = context()
        try:
            return jsonify(repo.confirm_delivery(tenant, delivery_id, user_id)), 200
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 409

    app.register_blueprint(bp)
