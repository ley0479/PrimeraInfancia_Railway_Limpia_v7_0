from __future__ import annotations

from pathlib import Path
import os
import re
import uuid

from flask import Blueprint, g, jsonify, request, send_file
from werkzeug.utils import secure_filename

from modules.seguridad.services import require_roles
from modules.seguridad.tenant_context import tenant_storage_root

from .repository import IDPRepository
from .services import ALLOWED_EXTENSIONS, MAX_FILE_SIZE, attendance_official_payload, canonicalize, classify_document, connect, read_document, read_document_intelligent, sha256_file, validate_file_signature


ALLOWED_ROLES = ('SUPERADMIN', 'GERENTE', 'COORDINADOR', 'AUXILIAR_ADMINISTRATIVO')


def _user() -> dict:
    raw = getattr(g, 'current_user', {}) or {}
    return {'id': raw.get('id'), 'fundacion_id': max(1, int(raw.get('fundacion_id') or 1)), 'rol': str(raw.get('rol') or '').upper()}


def register_idp_documental(app, database_path: str, data_dir: str) -> None:
    repo = IDPRepository(database_path)
    bp = Blueprint('idp_documental', __name__, url_prefix='/api/idp')

    def storage(tenant_id: int) -> Path:
        path = tenant_storage_root(data_dir, tenant_id) / 'idp' / 'originales'
        path.mkdir(parents=True, exist_ok=True)
        return path

    @bp.route('/documentos', methods=['GET'])
    @require_roles(*ALLOWED_ROLES)
    def list_documents():
        user = _user()
        return jsonify({'documentos': repo.list_documents(user['fundacion_id'])})

    @bp.route('/documentos', methods=['POST'])
    @require_roles(*ALLOWED_ROLES)
    def upload_document():
        user = _user()
        uploaded = request.files.get('file')
        if not uploaded or not uploaded.filename:
            return jsonify({'error': 'Selecciona un documento.'}), 400
        original = secure_filename(uploaded.filename) or 'documento'
        extension = Path(original).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            return jsonify({'error': 'Formato no permitido. Usa Excel, Word, PowerPoint, PDF o una imagen compatible.'}), 400
        temporary = storage(user['fundacion_id']) / f'.upload_{uuid.uuid4().hex}{extension}'
        uploaded.save(temporary)
        try:
            size = temporary.stat().st_size
            if size <= 0:
                return jsonify({'error': 'El archivo está vacío.'}), 400
            if size > MAX_FILE_SIZE:
                return jsonify({'error': 'El archivo supera el límite de 50 MB.'}), 413
            validate_file_signature(temporary)
            digest = sha256_file(temporary)
            duplicate = repo.find_duplicate(user['fundacion_id'], digest)
            if duplicate:
                return jsonify({'error': 'Este archivo ya fue cargado para la fundación.', 'duplicado': duplicate}), 409
            safe_stem = re.sub(r'[^A-Za-z0-9_.-]+', '_', Path(original).stem)[:80] or 'documento'
            stored_name = f'{digest[:16]}_{safe_stem}{extension}'
            destination = storage(user['fundacion_id']) / stored_name
            temporary.replace(destination)
            document_id = repo.create_document({'fundacion_id':user['fundacion_id'],'nombre_original':original,'nombre_guardado':stored_name,'ruta_privada':str(destination),'extension':extension,'mime_type':uploaded.mimetype,'tamano_bytes':size,'sha256':digest,'usuario_id':user['id']})
            if str(os.environ.get('IDP_ASYNC_ENABLED','0')).strip().lower() in {'1','true','yes','on'}:
                job=repo.enqueue_extraction(document_id,user['fundacion_id'])
                return jsonify({'message':'Documento recibido y enviado a la cola persistente.','trabajo':job,'documento':repo.get_document(document_id,user['fundacion_id'])}),202
            try:
                raw = read_document(destination)
                classification = classify_document(raw.get('texto') or '', original)
                canonical, fields = canonicalize(raw, classification[0])
                canonical['fundacion']['id'] = user['fundacion_id']
                repo.complete_extraction(document_id,user['fundacion_id'],raw,canonical,fields,classification,user['id'])
            except Exception as exc:
                repo.fail_extraction(document_id,user['fundacion_id'],type(exc).__name__.upper(),user['id'])
                return jsonify({'error':'El archivo quedó almacenado, pero la extracción no pudo completarse. Revísalo desde el módulo.','documento_id':document_id}),422
            return jsonify({'message':'Documento recibido y procesado para revisión.','documento':repo.get_document(document_id,user['fundacion_id'])}), 201
        finally:
            temporary.unlink(missing_ok=True)

    @bp.route('/documentos/<int:document_id>', methods=['GET'])
    @require_roles(*ALLOWED_ROLES)
    def get_document(document_id: int):
        user=_user(); item=repo.get_document(document_id,user['fundacion_id'])
        if not item: return jsonify({'error':'Documento no encontrado.'}),404
        return jsonify({'documento':item})

    @bp.route('/documentos/<int:document_id>/original', methods=['GET'])
    @require_roles(*ALLOWED_ROLES)
    def download_original(document_id: int):
        user=_user(); conn=repo.get_document(document_id,user['fundacion_id'])
        if not conn: return jsonify({'error':'Documento no encontrado.'}),404
        from .services import connect
        db=connect(database_path); row=db.execute('SELECT ruta_privada,nombre_original FROM idp_documentos WHERE id=? AND fundacion_id=?',(document_id,user['fundacion_id'])).fetchone(); db.close()
        path=Path(row['ruta_privada']) if row else None
        if not path or not path.exists(): return jsonify({'error':'Original privado no disponible.'}),404
        repo.audit(user['fundacion_id'],'DOCUMENTO_DESCARGADO',document_id,user['id'],'REVISION_HUMANA',conn.get('estado'))
        return send_file(path,as_attachment=True,download_name=row['nombre_original'])

    @bp.route('/documentos/<int:document_id>/vista-previa', methods=['GET'])
    @require_roles(*ALLOWED_ROLES)
    def preview_original(document_id: int):
        user=_user(); db=connect(database_path); row=db.execute('SELECT ruta_privada,nombre_original,extension,estado FROM idp_documentos WHERE id=? AND fundacion_id=?',(document_id,user['fundacion_id'])).fetchone(); db.close()
        if not row: return jsonify({'error':'Documento no encontrado.'}),404
        if str(row['extension']).lower() not in ({'.pdf'} | {'.png','.jpg','.jpeg','.bmp','.tif','.tiff','.heif','.heic'}):
            return jsonify({'error':'Este formato se revisa mediante descarga del original.'}),415
        path=Path(row['ruta_privada'])
        if not path.exists(): return jsonify({'error':'Original privado no disponible.'}),404
        repo.audit(user['fundacion_id'],'DOCUMENTO_VISUALIZADO',document_id,user['id'],'REVISION_HUMANA',row['estado'])
        response=send_file(path,as_attachment=False,download_name=row['nombre_original'],conditional=True)
        response.headers['Cache-Control']='private, no-store, max-age=0'; response.headers['Pragma']='no-cache'
        return response

    @bp.route('/documentos/<int:document_id>/campos/<int:field_id>', methods=['PATCH'])
    @require_roles(*ALLOWED_ROLES)
    def correct_field(document_id: int, field_id: int):
        user=_user(); data=request.get_json(silent=True) or {}
        if 'valor' not in data: return jsonify({'error':'Falta el valor corregido.'}),400
        try: repo.correct_field(document_id,field_id,user['fundacion_id'],data.get('valor'),user['id'],data.get('motivo'))
        except KeyError as exc: return jsonify({'error':str(exc)}),404
        return jsonify({'message':'Corrección guardada con trazabilidad.','documento':repo.get_document(document_id,user['fundacion_id'])})

    @bp.route('/documentos/<int:document_id>/aprobar', methods=['POST'])
    @require_roles('SUPERADMIN','GERENTE','COORDINADOR')
    def approve_document(document_id: int):
        user=_user()
        try: repo.approve(document_id,user['fundacion_id'],user['id'])
        except KeyError as exc: return jsonify({'error':str(exc)}),404
        except ValueError as exc: return jsonify({'error':str(exc)}),409
        return jsonify({'message':'Documento aprobado. Aún no se ha importado a módulos funcionales.','documento':repo.get_document(document_id,user['fundacion_id'])})

    @bp.route('/documentos/<int:document_id>/preparar-calendario', methods=['POST'])
    @require_roles(*ALLOWED_ROLES)
    def prepare_calendar(document_id: int):
        user=_user(); document=repo.get_document(document_id,user['fundacion_id'])
        if not document: return jsonify({'error':'Documento no encontrado.'}),404
        if document.get('tipo_documento')!='CRONOGRAMA': return jsonify({'error':'Solo los cronogramas o tableros de entregables pueden enviarse al calendario.'}),409
        if document.get('estado')!='APROBADO': return jsonify({'error':'Primero revise y apruebe la extracción documental.'}),409
        activities=(document.get('resultado_canonico') or {}).get('actividades') or []
        if not activities: return jsonify({'error':'No hay actividades estructuradas para enviar. Corrija el mapeo o la lectura OCR.'}),409
        from modules.calendario_inteligente.repository import CalendarioInteligenteRepository
        calendar=CalendarioInteligenteRepository(database_path,data_dir)
        preview=calendar.registrar_preview_actividades(activities,document.get('nombre_original') or '',str(user.get('id') or 'sistema'),f'IDP:{document_id}')
        repo.audit(user['fundacion_id'],'CALENDARIO_PREPARADO',document_id,user['id'],document.get('estado'),'LISTO_PARA_REVISION',{'cronograma_id':preview['cronograma_id'],'actividades':len(activities)})
        return jsonify({'message':'Actividades preparadas. Revise la vista previa antes de guardarlas en el calendario.','preview':preview}),201

    @bp.route('/documentos/<int:document_id>/reintentar-ocr', methods=['POST'])
    @require_roles(*ALLOWED_ROLES)
    def retry_ocr(document_id: int):
        user=_user(); db=connect(database_path); row=db.execute('SELECT ruta_privada,nombre_original,estado FROM idp_documentos WHERE id=? AND fundacion_id=?',(document_id,user['fundacion_id'])).fetchone(); db.close()
        if not row: return jsonify({'error':'Documento no encontrado.'}),404
        if row['estado'] not in {'REQUIERE_OCR','ERROR'}: return jsonify({'error':'El documento no está pendiente de OCR.'}),409
        try:
            repo.restart_extraction(document_id,user['fundacion_id'],user['id'])
            raw=read_document_intelligent(Path(row['ruta_privada'])); classification=classify_document(raw.get('texto') or '',row['nombre_original']); canonical,fields=canonicalize(raw,classification[0]); canonical['fundacion']['id']=user['fundacion_id']
            repo.complete_extraction(document_id,user['fundacion_id'],raw,canonical,fields,classification,user['id'])
        except Exception as exc:
            repo.fail_extraction(document_id,user['fundacion_id'],type(exc).__name__.upper(),user['id'])
            return jsonify({'error':str(exc),'documento':repo.get_document(document_id,user['fundacion_id'])}),409
        return jsonify({'message':'OCR ejecutado. Revisa los campos y validaciones antes de aprobar.','documento':repo.get_document(document_id,user['fundacion_id'])})

    @bp.route('/documentos/<int:document_id>/listado-oficial', methods=['GET'])
    @require_roles(*ALLOWED_ROLES)
    def download_official_attendance(document_id: int):
        user = _user(); document = repo.get_document(document_id,user['fundacion_id'])
        if not document: return jsonify({'error':'Documento no encontrado.'}),404
        try:
            users, metadata = attendance_official_payload(document)
            from services.listado_asistencia_usuarios_service import generate_list
            generated = tenant_storage_root(data_dir,user['fundacion_id']) / 'idp' / 'generados'
            generated.mkdir(parents=True,exist_ok=True)
            output = generated / f'LISTADO_ASISTENCIA_OFICIAL_IDP_{document_id}_{uuid.uuid4().hex[:8]}.xlsx'
            generate_list(data_dir,output,users,metadata=metadata,tenant_id=user['fundacion_id'])
        except (ValueError,FileNotFoundError) as exc:
            return jsonify({'error':str(exc)}),409
        repo.audit(user['fundacion_id'],'LISTADO_OFICIAL_GENERADO',document_id,user['id'],'APROBADO','APROBADO',{'archivo':output.name,'participantes':len(users)})
        return send_file(output,as_attachment=True,download_name=f'LISTADO_ASISTENCIA_OFICIAL_{document_id}.xlsx')

    @bp.route('/documentos/<int:document_id>/importar-asistencia', methods=['POST'])
    @require_roles('SUPERADMIN','GERENTE','COORDINADOR')
    def import_attendance(document_id: int):
        user=_user(); data=request.get_json(silent=True) or {}
        try: lot=repo.import_attendance(document_id,user['fundacion_id'],user['id'],data.get('fecha_actividad'),data.get('actividad'))
        except KeyError as exc: return jsonify({'error':str(exc)}),404
        except ValueError as exc: return jsonify({'error':str(exc)}),409
        message='El documento ya estaba importado; no se duplicaron registros.' if lot.get('ya_importado') else 'Asistencia importada con trazabilidad.'
        return jsonify({'message':message,'lote':lot,'documento':repo.get_document(document_id,user['fundacion_id'])})

    app.register_blueprint(bp)
