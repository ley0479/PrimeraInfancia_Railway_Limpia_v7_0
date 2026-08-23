from __future__ import annotations

from datetime import datetime
import hashlib
import os
from pathlib import Path
import shutil
import uuid

from flask import Blueprint, current_app, g, jsonify, request, send_file
from werkzeug.utils import secure_filename

from modules.seguridad.services import require_roles
from modules.seguridad.tenant_context import tenant_storage_root
from .repository import CentroDocumentalRepository
from .template_inspector_service import inspect_template, propose_mapping
from .theme_generation_service import generate_planning
from .narrative_service import assemble_narrative
from .data_context_service import search_participants, search_professionals
from .validators import validate_special_state
from .document_builder_service import build_docx,build_package,convert_pdf


ADMIN_ROLES = ("SUPERADMIN", "GERENTE", "COORDINADOR", "AUXILIAR_ADMINISTRATIVO")
PROFESSIONAL_ROLES = ADMIN_ROLES + ("DOCENTE", "NUTRICIONISTA", "PSICOSOCIAL")
ALLOWED_EXTENSIONS = {".docx", ".xlsx", ".xlsm", ".pdf"}
MIME_BY_EXTENSION = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xlsm": "application/vnd.ms-excel.sheet.macroEnabled.12",
    ".pdf": "application/pdf",
}


def _enabled(name: str, default: bool = False) -> bool:
    value = current_app.config.get(name, os.environ.get(name, "true" if default else "false"))
    return str(value).strip().lower() in {"1", "true", "yes", "si", "sí", "on"}


def _user() -> dict:
    raw = dict(getattr(g, "current_user", {}) or {})
    return {"id": raw.get("id"), "fundacion_id": int(raw.get("fundacion_id") or 1), "rol": str(raw.get("rol") or "").upper()}


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def register_centro_documental(app, database_path: str, data_dir: str) -> None:
    repository = CentroDocumentalRepository(database_path)
    blueprint = Blueprint("centro_documental", __name__, url_prefix="/api/documentos")

    @blueprint.before_request
    def feature_guard():
        if not _enabled("ENABLE_DOCUMENT_AUTOMATION", True):
            return jsonify({"error": "El Centro Documental todavía no está habilitado.", "codigo": "FEATURE_DISABLED"}), 404
        return None

    @blueprint.get("/estado")
    @require_roles(*PROFESSIONAL_ROLES)
    def state():
        user = _user()
        capture_enabled = _enabled("ENABLE_CAPTURE_FORMAT", True)
        return jsonify({
            "habilitado": True,
            "mapeo_plantillas": _enabled("ENABLE_TEMPLATE_MAPPING", True),
            "catalogos_respuesta": _enabled("ENABLE_RESPONSE_CATALOGS", True),
            "ia_borradores": _enabled("ENABLE_AI_DOCUMENT_DRAFTS", False),
            "ia_finalizacion": False,
            "capture": repository.capture_status(user["fundacion_id"], capture_enabled),
        })

    @blueprint.get("/plantillas")
    @require_roles(*PROFESSIONAL_ROLES)
    def templates():
        user = _user()
        return jsonify({"plantillas": repository.list_templates(user["fundacion_id"])})

    @blueprint.post("/plantillas")
    @require_roles(*ADMIN_ROLES)
    def upload_template():
        if not _enabled("ENABLE_TEMPLATE_MAPPING", True):
            return jsonify({"error": "El mapeo de plantillas no está habilitado."}), 409
        upload = request.files.get("file")
        if not upload or not upload.filename:
            return jsonify({"error": "Falta la plantilla oficial."}), 400
        extension = Path(upload.filename).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            return jsonify({"error": "Solo se permiten DOCX, XLSX, XLSM o PDF."}), 415
        user = _user(); tenant = user["fundacion_id"]
        root = tenant_storage_root(data_dir, tenant) / "official_templates" / "centro_documental"
        root.mkdir(parents=True, exist_ok=True)
        temporary = root / f".upload_{uuid.uuid4().hex}{extension}"
        upload.save(temporary)
        try:
            inspection = inspect_template(temporary)
            digest = _hash(temporary)
            safe_original = secure_filename(upload.filename) or f"plantilla{extension}"
            destination = root / f"{digest}_{safe_original}"
            if not destination.exists():
                shutil.copy2(temporary, destination)
            code = str(request.form.get("codigo") or Path(safe_original).stem).strip().upper()[:100]
            document_type = str(request.form.get("tipo_documento") or code).strip().upper()[:100]
            if document_type.replace("_", " ") in {"CACTURE", "FORMATO CACTURE", "FORMATO CAPTURE"}:
                document_type = "CAPTURE"
            component = str(request.form.get("componente") or "PEDAGOGICO").strip().upper()[:50]
            if document_type == "CAPTURE" and not _enabled("ENABLE_CAPTURE_FORMAT", False):
                state_value = "MAPEO_PROPUESTO"
            else:
                state_value = "MAPEO_PROPUESTO"
            version = repository.create_template_version(
                {"codigo":code,"nombre":request.form.get("nombre") or safe_original,"componente":component,"tipo_documento":document_type,"scope":"FUNDACION","fundacion_id":tenant},
                {"version":request.form.get("version") or datetime.now().strftime("%Y.%m.%d.%H%M%S"),"nombre_original":upload.filename,"nombre_seguro":destination.name,"ruta_privada":str(destination),"mime_type":MIME_BY_EXTENSION[extension],"extension":extension,"hash_sha256":digest,"estado":state_value,"inspeccion":inspection},
                user["id"],
            )
            mapping = repository.save_mapping(version["id"],tenant,propose_mapping(inspection),user["id"])
            return jsonify({"message":"Plantilla registrada; el original permanece intacto y el mapa requiere aprobación.","plantilla_version":version,"mapeo":mapping}),201
        except ValueError as exc:
            return jsonify({"error":str(exc)}),409
        except (OSError, RuntimeError, KeyError) as exc:
            current_app.logger.exception("No se pudo registrar la plantilla documental")
            return jsonify({
                "error": "No se pudo inspeccionar o registrar la plantilla. Verifique que el archivo sea un documento válido y vuelva a intentarlo.",
                "codigo": "TEMPLATE_PROCESSING_FAILED",
            }), 422
        finally:
            temporary.unlink(missing_ok=True)

    @blueprint.get("/plantillas/<int:version_id>/original")
    @require_roles(*ADMIN_ROLES)
    def original(version_id: int):
        user=_user(); version=repository.get_version(version_id,user["fundacion_id"])
        if not version: return jsonify({"error":"Plantilla no encontrada."}),404
        path=Path(version["ruta_privada"])
        if not path.exists(): return jsonify({"error":"Original privado no disponible."}),404
        repository.audit(user["fundacion_id"],"PLANTILLA_VERSION",version_id,"DESCARGADA",user["id"])
        return send_file(path,as_attachment=True,download_name=version["nombre_original"])

    @blueprint.put("/plantillas/<int:version_id>/mapeo")
    @require_roles(*ADMIN_ROLES)
    def update_mapping(version_id: int):
        user=_user(); payload=request.get_json(silent=True) or {}
        try: result=repository.save_mapping(version_id,user["fundacion_id"],payload,user["id"])
        except KeyError as exc: return jsonify({"error":str(exc)}),404
        return jsonify({"mapeo":result})

    @blueprint.post("/plantillas/<int:version_id>/aprobar")
    @require_roles(*ADMIN_ROLES)
    def approve_mapping(version_id: int):
        user=_user(); version=repository.get_version(version_id,user["fundacion_id"])
        if not version: return jsonify({"error":"Plantilla no encontrada."}),404
        if version["tipo_documento"] == "CAPTURE" and not _enabled("ENABLE_CAPTURE_FORMAT",True):
            return jsonify({"error":"CAPTURE permanece desactivado hasta completar su prueba oficial.","codigo":"CAPTURE_PILOT_REQUIRED"}),409
        try: approved=repository.approve_mapping(version_id,user["fundacion_id"],user["id"])
        except ValueError as exc: return jsonify({"error":str(exc)}),409
        return jsonify({"message":"Mapa aprobado.","mapeo":approved})

    @blueprint.post("/tema/generar-planeacion")
    @require_roles(*PROFESSIONAL_ROLES)
    def planning():
        payload=request.get_json(silent=True) or {}
        try: result=generate_planning(payload.get("tema"),payload.get("componente"),payload.get("tipo_actividad") or "",payload.get("grupo_poblacional") or "")
        except ValueError as exc: return jsonify({"error":str(exc)}),400
        return jsonify({"planeacion":result})

    @blueprint.post("/narrativa")
    @require_roles(*PROFESSIONAL_ROLES)
    def narrative():
        payload=request.get_json(silent=True) or {}
        try: result=assemble_narrative(payload.get("selecciones") or [])
        except ValueError as exc: return jsonify({"error":str(exc),"codigo":"CONTRADICCION"}),409
        return jsonify({"narrativa":result})

    @blueprint.get("/contexto/participantes")
    @require_roles(*PROFESSIONAL_ROLES)
    def participants_context():
        user=_user()
        return jsonify(search_participants(database_path,user["fundacion_id"],request.args.get("q", ""),request.args.get("uds", ""),request.args.get("limit",25,type=int),request.args.get("offset",0,type=int)))

    @blueprint.get("/contexto/profesionales")
    @require_roles(*PROFESSIONAL_ROLES)
    def professionals_context():
        user=_user()
        return jsonify(search_professionals(database_path,user["fundacion_id"],request.args.get("q", ""),request.args.get("uds", ""),request.args.get("limit",25,type=int)))

    @blueprint.get("/catalogos")
    @require_roles(*PROFESSIONAL_ROLES)
    def catalogs():
        if not _enabled("ENABLE_RESPONSE_CATALOGS",True): return jsonify({"error":"Los catálogos documentales aún no están habilitados."}),409
        user=_user(); return jsonify({"catalogos":repository.list_catalogs(user["fundacion_id"],request.args.get("componente", ""))})

    @blueprint.post("")
    @require_roles(*PROFESSIONAL_ROLES)
    def create_document():
        user=_user(); payload=request.get_json(silent=True) or {}
        if not payload.get("tipo_documento") or not payload.get("componente"): return jsonify({"error":"Tipo de documento y componente son obligatorios."}),400
        if str(payload.get("tipo_documento")).upper()=="CAPTURE": return jsonify({"error":"CAPTURE requiere una plantilla oficial real aprobada.","codigo":"PLANTILLA_PENDIENTE"}),409
        if payload.get("tema") and not payload.get("planeacion"):
            payload["planeacion"]=generate_planning(payload["tema"],payload["componente"],payload.get("tipo_actividad", ""),payload.get("grupo_poblacional", ""))
        item=repository.create_instance(user["fundacion_id"],payload,user["id"])
        return jsonify({"documento":item}),201

    @blueprint.get("")
    @require_roles(*PROFESSIONAL_ROLES)
    def list_documents():
        user=_user()
        return jsonify(repository.list_instances(user["fundacion_id"],request.args.get("limit",25,type=int),request.args.get("offset",0,type=int),request.args.get("componente", ""),request.args.get("estado", "")))

    @blueprint.get("/<int:document_id>")
    @require_roles(*PROFESSIONAL_ROLES)
    def get_document(document_id: int):
        user=_user(); item=repository.get_instance(document_id,user["fundacion_id"])
        return jsonify({"documento":item}) if item else (jsonify({"error":"Documento no encontrado."}),404)

    @blueprint.get("/<int:document_id>/auditoria")
    @require_roles(*PROFESSIONAL_ROLES)
    def document_audit(document_id: int):
        user=_user()
        try: history=repository.document_history(document_id,user["fundacion_id"])
        except KeyError as exc: return jsonify({"error":str(exc)}),404
        return jsonify(history)

    @blueprint.patch("/<int:document_id>")
    @require_roles(*PROFESSIONAL_ROLES)
    def update_document(document_id: int):
        user=_user(); payload=request.get_json(silent=True) or {}
        if "narrativa" not in payload:
            return jsonify({"error":"No se recibieron campos documentales editables."}),400
        narrative=str(payload.get("narrativa") or "").strip()
        if not narrative:
            return jsonify({"error":"La narrativa no puede quedar vacía."}),400
        try: item=repository.save_narrative(document_id,user["fundacion_id"],narrative,user["id"])
        except KeyError as exc: return jsonify({"error":str(exc)}),404
        return jsonify({"message":"Narrativa revisada y guardada.","documento":item})

    @blueprint.post("/<int:document_id>/selecciones")
    @require_roles(*PROFESSIONAL_ROLES)
    def save_selections(document_id: int):
        user=_user(); selections=(request.get_json(silent=True) or {}).get("selecciones") or []
        try:
            for item in selections: validate_special_state(item.get("estado_especial"),item.get("justificacion"))
            saved=repository.replace_selections(document_id,user["fundacion_id"],selections,user["id"])
        except KeyError as exc: return jsonify({"error":str(exc)}),404
        except ValueError as exc: return jsonify({"error":str(exc)}),400
        return jsonify({"selecciones":saved})

    @blueprint.post("/<int:document_id>/generar-borrador")
    @require_roles(*PROFESSIONAL_ROLES)
    def generate_draft(document_id: int):
        user=_user(); item=repository.get_instance(document_id,user["fundacion_id"])
        if not item: return jsonify({"error":"Documento no encontrado."}),404
        selections=[{"categoria":value.get("categoria"),"codigo":value.get("codigo"),"texto":value.get("texto") or value.get("texto_personalizado")} for value in item["selecciones"]]
        try: draft=assemble_narrative(selections)
        except ValueError as exc: return jsonify({"error":str(exc),"codigo":"CONTRADICCION"}),409
        updated=repository.save_narrative(document_id,user["fundacion_id"],draft["texto"],user["id"])
        return jsonify({"narrativa":draft,"documento":updated})

    @blueprint.post("/<int:document_id>/<action>")
    @require_roles(*PROFESSIONAL_ROLES)
    def transition_document(document_id: int, action: str):
        names={"enviar-revision":"ENVIAR_REVISION","devolver":"DEVOLVER","reenviar":"REENVIAR","aprobar":"APROBAR","archivar":"ARCHIVAR"}
        if action not in names: return jsonify({"error":"Acción documental no encontrada."}),404
        user=_user(); payload=request.get_json(silent=True) or {}
        if names[action] in {"DEVOLVER","APROBAR","ARCHIVAR"} and user["rol"] not in ADMIN_ROLES:
            return jsonify({"error":"El rol actual no puede revisar o aprobar documentos."}),403
        try: item=repository.transition(document_id,user["fundacion_id"],names[action],user["id"],str(payload.get("observacion") or ""))
        except KeyError as exc: return jsonify({"error":str(exc)}),404
        except ValueError as exc: return jsonify({"error":str(exc)}),409
        return jsonify({"documento":item})

    def _generate_word(document_id: int, user: dict):
        item=repository.get_instance(document_id,user["fundacion_id"])
        if not item: raise KeyError("Documento no encontrado.")
        if not item.get("plantilla_version_id"): raise ValueError("Seleccione una plantilla oficial aprobada.")
        template=repository.get_version(item["plantilla_version_id"],user["fundacion_id"])
        if not template or template.get("estado") not in {"APROBADA","ACTIVA"}: raise ValueError("La plantilla todavía no tiene un mapa aprobado.")
        if template.get("tipo_documento")=="CAPTURE": raise ValueError("CAPTURE permanece pendiente de piloto con plantilla oficial.")
        folder=tenant_storage_root(data_dir,user["fundacion_id"])/"documents"/str(document_id)
        output=folder/f"documento_{document_id}_v{int(item.get('version_actual') or 0)+1}.docx"
        context=dict(item.get("datos") or {}); context.update({"uds":item.get("uds"),"tema":item.get("tema"),"mapped_fields":[field.get("field_key") for field in (context.get("mapeo_campos") or [])]})
        generated=build_docx(Path(template["ruta_privada"]),output,context,item.get("narrativa") or "")
        version=repository.record_version(document_id,user["fundacion_id"],{"estado":item["estado"],"tema":item.get("tema")},str(output),None,generated["sha256"],user["id"])
        return generated,version

    @blueprint.post("/<int:document_id>/generar-word")
    @require_roles(*PROFESSIONAL_ROLES)
    def generate_word(document_id: int):
        user=_user()
        try: generated,version=_generate_word(document_id,user)
        except KeyError as exc: return jsonify({"error":str(exc)}),404
        except (ValueError,FileNotFoundError,RuntimeError) as exc: return jsonify({"error":str(exc)}),409
        return jsonify({"message":"Word generado sobre una copia; el original permanece intacto.","archivo":{"version":version,"integridad":generated}}),201

    @blueprint.post("/<int:document_id>/generar-pdf")
    @require_roles(*PROFESSIONAL_ROLES)
    def generate_pdf(document_id: int):
        user=_user(); version=repository.get_generated_version(document_id,user["fundacion_id"])
        if not version or not version.get("archivo_word"): return jsonify({"error":"Primero genere el documento Word."}),409
        try: pdf=convert_pdf(Path(version["archivo_word"]),Path(version["archivo_word"]).parent)
        except RuntimeError as exc: return jsonify({"error":str(exc),"word_disponible":True}),503
        recorded=repository.record_version(document_id,user["fundacion_id"],{"origen_version":version["version"]},version["archivo_word"],str(pdf),version.get("hash_sha256"),user["id"])
        return jsonify({"message":"PDF generado.","archivo":recorded}),201

    @blueprint.post("/<int:document_id>/generar-paquete")
    @require_roles(*PROFESSIONAL_ROLES)
    def generate_package(document_id: int):
        user=_user(); item=repository.get_instance(document_id,user["fundacion_id"]); version=repository.get_generated_version(document_id,user["fundacion_id"])
        if not item or not version: return jsonify({"error":"El documento y su Word deben existir antes de crear el paquete."}),409
        files=[]
        if version.get("archivo_word"): files.append(("01_DOCUMENTO.docx",Path(version["archivo_word"])))
        if version.get("archivo_pdf"): files.append(("07_PDF_APROBADOS/documento.pdf",Path(version["archivo_pdf"])))
        folder=tenant_storage_root(data_dir,user["fundacion_id"])/"packages"/str(document_id); output=folder/f"PAQUETE_DOCUMENTAL_{document_id}.zip"
        package=build_package(output,files,{"documento_id":document_id,"fundacion_id":user["fundacion_id"],"estado":item["estado"],"capture":"PENDIENTE_PLANTILLA"})
        repository.audit(user["fundacion_id"],"DOCUMENTO",document_id,"PAQUETE_GENERADO",user["id"],{"archivo":output.name,"hash_sha256":package["sha256"]})
        return jsonify({"message":"Paquete documental generado.","paquete":package}),201

    @blueprint.get("/<int:document_id>/descargar-paquete")
    @require_roles(*PROFESSIONAL_ROLES)
    def download_package(document_id: int):
        user=_user()
        if not repository.get_instance(document_id,user["fundacion_id"]): return jsonify({"error":"Documento no encontrado."}),404
        root=(tenant_storage_root(data_dir,user["fundacion_id"])/"packages").resolve()
        try:
            path=(root/str(document_id)/f"PAQUETE_DOCUMENTAL_{document_id}.zip").resolve(strict=True); path.relative_to(root)
        except (OSError,ValueError): return jsonify({"error":"Paquete documental no disponible."}),404
        repository.audit(user["fundacion_id"],"DOCUMENTO",document_id,"PAQUETE_DESCARGADO",user["id"],{"hash_sha256":_hash(path)})
        return send_file(path,as_attachment=True,download_name=path.name,mimetype="application/zip")

    @blueprint.get("/<int:document_id>/descargar")
    @require_roles(*PROFESSIONAL_ROLES)
    def download_generated(document_id: int):
        user=_user(); version=repository.get_generated_version(document_id,user["fundacion_id"],request.args.get("version",type=int)); kind=request.args.get("tipo","word")
        if not version: return jsonify({"error":"Versión no encontrada."}),404
        path=Path(version.get("archivo_pdf") if kind=="pdf" else version.get("archivo_word") or "")
        if not path.exists(): return jsonify({"error":"Archivo no disponible."}),404
        repository.audit(user["fundacion_id"],"DOCUMENTO",document_id,"DESCARGADO",user["id"],{"tipo":kind,"version":version["version"]})
        return send_file(path,as_attachment=True,download_name=path.name)

    @blueprint.route("/<int:document_id>/participantes",methods=["GET","PUT"])
    @require_roles(*PROFESSIONAL_ROLES)
    def save_participants(document_id: int):
        user=_user(); payload=request.get_json(silent=True) or {}
        if request.method=="GET":
            if not repository.get_instance(document_id,user["fundacion_id"]): return jsonify({"error":"Documento no encontrado."}),404
            return jsonify({"participantes":repository.participants(document_id,user["fundacion_id"])})
        try: result=repository.replace_participants(document_id,user["fundacion_id"],payload.get("participantes") or [])
        except KeyError as exc: return jsonify({"error":str(exc)}),404
        except ValueError as exc: return jsonify({"error":str(exc)}),409
        return jsonify({"participantes":result})

    @blueprint.route("/<int:document_id>/evidencias",methods=["GET","POST"])
    @require_roles(*PROFESSIONAL_ROLES)
    def evidence(document_id: int):
        user=_user()
        if request.method=="GET": return jsonify({"evidencias":repository.list_evidence(document_id,user["fundacion_id"])})
        upload=request.files.get("file")
        if not upload or not upload.filename: return jsonify({"error":"Selecciona una evidencia."}),400
        forbidden={".exe",".com",".bat",".cmd",".ps1",".sh",".html",".htm"}; extension=Path(upload.filename).suffix.lower()
        if extension in forbidden or str(upload.mimetype or "").lower() in {"text/html","application/x-msdownload","application/x-sh"}: return jsonify({"error":"Tipo de evidencia no permitido."}),415
        root=tenant_storage_root(data_dir,user["fundacion_id"])/"evidence"/str(document_id); root.mkdir(parents=True,exist_ok=True)
        safe=secure_filename(upload.filename) or "evidencia"; temporary=root/f".upload_{uuid.uuid4().hex}{extension}"; upload.save(temporary)
        try:
            size=temporary.stat().st_size
            if size<=0 or size>50*1024*1024: return jsonify({"error":"La evidencia está vacía o supera 50 MB."}),413
            digest=_hash(temporary); destination=root/f"{digest[:20]}_{safe}"
            if not destination.exists(): shutil.copy2(temporary,destination)
            try: saved=repository.add_evidence(document_id,user["fundacion_id"],{"actividad_id":request.form.get("actividad_id",type=int),"requisito":request.form.get("requisito"),"nombre_original":upload.filename,"nombre_seguro":destination.name,"ruta_privada":str(destination),"mime_type":upload.mimetype,"tamano_bytes":size,"hash_sha256":digest},user["id"])
            except KeyError as exc: return jsonify({"error":str(exc)}),404
            return jsonify({"message":"Evidencia privada cargada con integridad verificable.","evidencia":saved}),201
        finally: temporary.unlink(missing_ok=True)

    @blueprint.get("/evidencias/<int:evidence_id>/descargar")
    @require_roles(*PROFESSIONAL_ROLES)
    def download_evidence(evidence_id: int):
        user=_user(); item=repository.get_evidence(evidence_id,user["fundacion_id"])
        if not item: return jsonify({"error":"Evidencia no encontrada."}),404
        try:
            path=Path(item["ruta_privada"]).resolve(strict=True); root=(tenant_storage_root(data_dir,user["fundacion_id"])/"evidence").resolve(); path.relative_to(root)
        except (OSError,ValueError): return jsonify({"error":"Evidencia privada no disponible."}),404
        if _hash(path)!=item["hash_sha256"]: return jsonify({"error":"La evidencia no superó la verificación de integridad."}),409
        repository.audit(user["fundacion_id"],"EVIDENCIA",evidence_id,"DESCARGADA",user["id"])
        return send_file(path,as_attachment=True,download_name=item["nombre_original"],mimetype=item.get("mime_type"))

    @blueprint.get("/<int:document_id>/calendario")
    @require_roles(*PROFESSIONAL_ROLES)
    def calendar_link(document_id: int):
        user=_user()
        try: result=repository.calendar_requirements(document_id,user["fundacion_id"])
        except KeyError as exc: return jsonify({"error":str(exc)}),404
        return jsonify(result)

    @blueprint.post("/<int:document_id>/generar-listado-asistencia")
    @require_roles(*PROFESSIONAL_ROLES)
    def official_attendance(document_id: int):
        user=_user(); item=repository.get_instance(document_id,user["fundacion_id"])
        if not item: return jsonify({"error":"Documento no encontrado."}),404
        participants=repository.participants(document_id,user["fundacion_id"])
        if not participants: return jsonify({"error":"Confirma al menos un participante antes de generar el listado."}),409
        try:
            from services.listado_asistencia_usuarios_service import generate_list
            folder=tenant_storage_root(data_dir,user["fundacion_id"])/"documents"/str(document_id); output=folder/f"LISTADO_ASISTENCIA_OFICIAL_{document_id}.xlsx"
            generate_list(data_dir,output,participants,metadata={"unidad":item.get("uds"),"tema":item.get("tema")},tenant_id=user["fundacion_id"])
        except (FileNotFoundError,ValueError) as exc: return jsonify({"error":str(exc)}),409
        repository.audit(user["fundacion_id"],"DOCUMENTO",document_id,"LISTADO_OFICIAL_GENERADO",user["id"],{"participantes":len(participants)})
        return send_file(output,as_attachment=True,download_name=output.name)

    app.register_blueprint(blueprint)
