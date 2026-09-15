from __future__ import annotations

import os

from flask import g, jsonify, request, send_file
from werkzeug.security import check_password_hash
from modules.dbapi_compat import sqlite3

from modules.seguridad.services import require_roles

from .services import BackupService


def current_user() -> dict:
    return getattr(g, 'current_user', None) or {'username': 'sistema', 'fundacion_id': 1}


def register_backups(app, database_path: str, backups_folder: str) -> None:
    service = BackupService(database_path, backups_folder)
    service.init()
    # Durante init_hosting hay DDL pendiente en la misma aplicación. Lanzar
    # pg_dump en ese punto intenta bloquear las tablas que el proceso padre aún
    # está modificando y ambos procesos quedan esperándose. El backup diario se
    # ejecuta únicamente en el worker ya inicializado.
    migration_mode = os.getenv('APP_SCHEMA_MIGRATION_MODE', '').strip().lower() in {
        '1', 'true', 'yes', 'si', 'sí', 'on',
    }
    if not migration_mode:
        try:
            service.create_daily_if_needed({'username': 'sistema', 'fundacion_id': 1})
        except Exception as exc:
            print(f'Backup diario no pudo crearse: {exc}')

    @app.route('/api/backups', methods=['GET'])
    @require_roles('SUPERADMIN', 'GERENTE')
    def backups_listar():
        limit = int(request.args.get('limit') or 100)
        return jsonify({'backups': service.list_backups(limit)})

    @app.route('/api/backups/estado', methods=['GET'])
    @require_roles('SUPERADMIN', 'GERENTE')
    def backups_estado():
        return jsonify({'estado': service.status()})

    @app.route('/api/backups/crear', methods=['POST'])
    @require_roles('SUPERADMIN', 'GERENTE')
    def backups_crear():
        data = request.get_json(silent=True) or request.form.to_dict() or {}
        motivo = data.get('motivo') or 'MANUAL'
        descripcion = data.get('descripcion') or 'Backup manual creado desde la plataforma.'
        try:
            backup = service.create_backup(motivo, descripcion, current_user(), request.remote_addr)
            return jsonify({'message': 'Backup creado correctamente.', 'backup': backup})
        except Exception as exc:
            return jsonify({'error': f'No se pudo crear el backup: {exc}'}), 500

    @app.route('/api/backups/<int:backup_id>/validar', methods=['POST'])
    @require_roles('SUPERADMIN', 'GERENTE')
    def backups_validar(backup_id: int):
        try:
            backup = service.validate_backup(backup_id)
            service.audit('BACKUP_VALIDADO', backup_id, 'Validación manual ejecutada desde UI.', current_user(), request.remote_addr)
            return jsonify({'message': 'Backup válido.', 'backup': backup})
        except Exception as exc:
            return jsonify({'error': str(exc)}), 400

    @app.route('/api/backups/<int:backup_id>/descargar', methods=['GET'])
    @require_roles('SUPERADMIN', 'GERENTE')
    def backups_descargar(backup_id: int):
        try:
            backup = service.validate_backup(backup_id)
            service.audit('BACKUP_DESCARGADO', backup_id, 'Descarga de backup.', current_user(), request.remote_addr)
            return send_file(backup['ruta_archivo'], as_attachment=True, download_name=backup['archivo'])
        except Exception as exc:
            return jsonify({'error': str(exc)}), 404

    @app.route('/api/backups/<int:backup_id>/restaurar', methods=['POST'])
    @require_roles('SUPERADMIN')
    def backups_restaurar(backup_id: int):
        data = request.get_json(silent=True) or {}
        confirmar = str(data.get('confirmar') or '').upper()
        if confirmar != 'RESTAURAR':
            return jsonify({'error': 'Para restaurar debes enviar confirmar=RESTAURAR. Esta acción solo la puede hacer SUPERADMIN.'}), 400
        password=str(data.get('password_actual') or '')
        user=current_user();conn=sqlite3.connect(database_path);conn.row_factory=sqlite3.Row
        try:row=conn.execute('SELECT password_hash FROM usuarios_app WHERE id=? AND fundacion_id=? AND COALESCE(activo,1)=1',(int(user.get('id') or 0),int(user.get('fundacion_id') or 1))).fetchone()
        finally:conn.close()
        if not row or not password or not check_password_hash(str(row['password_hash'] or ''),password):
            service.audit('BACKUP_RESTAURACION_REAUTENTICACION_FALLIDA',backup_id,'La contraseña actual no fue validada.',user,request.remote_addr)
            return jsonify({'error':'Debes reautenticarte con tu contraseña actual antes de restaurar.'}),403
        try:
            service.audit('BACKUP_RESTAURACION_REAUTENTICADA',backup_id,'Confirmación reforzada validada.',user,request.remote_addr)
            resultado = service.restore_backup(backup_id, user, request.remote_addr)
            return jsonify(resultado)
        except Exception as exc:
            return jsonify({'error': f'No se pudo restaurar el backup: {exc}'}), 500
