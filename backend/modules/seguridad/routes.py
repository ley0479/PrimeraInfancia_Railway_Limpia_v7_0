from __future__ import annotations

import os
import re
import secrets
from modules.dbapi_compat import sqlite3
import string
import time
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit

from flask import jsonify, request, g, current_app
from werkzeug.security import generate_password_hash, check_password_hash

from .schema import ROLES_SISTEMA
from .tenant_context import ensure_tenant_directories
from .services import (
    audit,
    clear_rate_limit,
    connect,
    create_session,
    create_login_session_atomic,
    extract_token,
    get_request_user_context,
    hash_token,
    is_sqlite_busy_error,
    load_login_state,
    invalidate_user_sessions,
    is_superadmin,
    now_iso,
    password_policy_errors,
    rate_limit_status,
    register_rate_limit_failure,
    record_login_failure_atomic,
    require_roles,
    send_password_reset_email,
    build_password_reset_url,
    user_dict,
)


def payload() -> dict:
    return request.get_json(silent=True) or {}


def _rate_limited_response(seconds: int):
    response = jsonify({
        'error': 'Demasiados intentos. Intenta nuevamente más tarde.',
        'code': 'RATE_LIMITED',
        'retry_after': seconds,
    })
    response.status_code = 429
    response.headers['Retry-After'] = str(max(1, seconds))
    return response


def _password_error(password: str):
    errors = password_policy_errors(password)
    if not errors:
        return None
    return jsonify({
        'error': 'La contraseña requiere ' + ', '.join(errors) + '.',
        'code': 'WEAK_PASSWORD',
    }), 400


_USERNAME_PATTERN = re.compile(r'^[A-Za-z0-9._@-]{3,100}$')


def _normalize_username(value) -> str:
    return str(value or '').strip()


def _normalize_email(value) -> str:
    return str(value or '').strip().lower()


def _normalize_foundation_identity(value) -> str:
    normalized = unicodedata.normalize('NFKD', str(value or ''))
    without_marks = ''.join(char for char in normalized if not unicodedata.combining(char))
    return ' '.join(without_marks.casefold().split())


def _identity_error(username: str, email: str):
    if not username or not email:
        return 'Usuario y correo son obligatorios.'
    if any(char.isspace() for char in username) or not _USERNAME_PATTERN.fullmatch(username):
        return 'El usuario debe tener entre 3 y 100 caracteres y usar solo letras, números, punto, guion o guion bajo.'
    if '@' not in email or email.startswith('@') or email.endswith('@'):
        return 'Escribe un correo válido.'
    return None


def _temporary_password(length: int = 18) -> str:
    """Genera una clave que cumple la política sin depender de datos personales."""
    alphabet = string.ascii_letters + string.digits + '!@#$%*-_'
    required = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice('!@#$%*-_'),
    ]
    required.extend(secrets.choice(alphabet) for _ in range(max(12, length) - len(required)))
    secrets.SystemRandom().shuffle(required)
    return ''.join(required)


def _local_recovery_allowed(app) -> bool:
    if str(app.config.get('APP_ENV') or '').lower() == 'production':
        return False
    if bool(app.config.get('PUBLIC_TUNNEL_MODE', False)):
        return False
    if not bool(app.config.get('ALLOW_LOCAL_RECOVERY_CODE', False)):
        return False
    remote = str(request.remote_addr or '').split('%', 1)[0]
    raw_host = str(request.host or '').strip().lower()
    if raw_host.startswith('[') and ']' in raw_host:
        host = raw_host[1:raw_host.index(']')]
    else:
        host = raw_host.rsplit(':', 1)[0] if raw_host.count(':') == 1 else raw_host
    return remote in {'127.0.0.1', '::1'} and host in {'127.0.0.1', 'localhost', '::1'}


def _generate_local_code(app) -> str:
    length = max(8, min(24, int(app.config.get('LOCAL_RECOVERY_CODE_LENGTH', 10))))
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def _clear_login_limits(database_path: str, *identifiers) -> None:
    for identifier in identifiers:
        normalized = str(identifier or '').strip()
        if normalized:
            clear_rate_limit(database_path, 'login', normalized)


def _safe_warning(message: str, *args) -> None:
    """Registra una advertencia sin convertir el diagnóstico en otro fallo."""
    try:
        current_app.logger.warning(message, *args)
    except Exception:
        pass


def _safe_info(message: str, *args) -> None:
    """Registra telemetría sin incluir identificadores o credenciales."""
    try:
        current_app.logger.info(message, *args)
    except Exception:
        pass


def _auth_debug(message: str, *args) -> None:
    """Traza opt-in del login sin secretos ni identificadores en claro."""
    try:
        env_enabled = os.getenv('AUTH_LOGIN_DEBUG', '').strip().lower() in {'1', 'true', 'yes', 'si', 'sí', 'on'}
        if current_app.config.get('AUTH_LOGIN_DEBUG', False) or env_enabled:
            # WARNING garantiza visibilidad incluso si el despliegue filtra INFO.
            # Solo se activa explícitamente y nunca contiene secretos.
            current_app.logger.warning('AUTH_DEBUG ' + message, *args)
    except Exception:
        pass


def _dependency_counts(conn: sqlite3.Connection, column: str, value: int, *, excluded: set[str] | None = None) -> dict:
    """Cuenta referencias sin construir nombres desde datos del usuario."""
    if column not in {'fundacion_id', 'usuario_id', 'usuario_creador_id', 'creado_por', 'actualizado_por'}:
        raise ValueError('Columna de dependencia no permitida.')
    excluded = excluded or set()
    details = []
    total = 0
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
    for row in tables:
        table = str(row['name'])
        if table in excluded or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', table):
            continue
        columns = {str(item['name']) for item in conn.execute(f'PRAGMA table_info("{table}")').fetchall()}
        if column not in columns:
            continue
        try:
            count = int(conn.execute(f'SELECT COUNT(*) AS total FROM "{table}" WHERE "{column}"=?', (value,)).fetchone()['total'] or 0)
        except Exception:
            continue
        if count:
            details.append({'tabla': table, 'columna': column, 'registros': count})
            total += count
    return {'total': total, 'detalle': sorted(details, key=lambda item: (-item['registros'], item['tabla']))}


def _user_dependency_summary(conn: sqlite3.Connection, user_id: int) -> dict:
    merged = []
    total = 0
    for column in ('usuario_id', 'usuario_creador_id', 'creado_por', 'actualizado_por'):
        result = _dependency_counts(conn, column, user_id, excluded={'usuarios_app'})
        merged.extend(result['detalle'])
        total += int(result['total'])
    return {'total': total, 'detalle': sorted(merged, key=lambda item: (-item['registros'], item['tabla'], item['columna']))}


def register_seguridad(app, database_path: str) -> None:
    def attach_auth_correlation_headers(response):
        """Permite demostrar que navegador y diagnóstico llegan a la misma instancia."""
        if request.path == '/api/auth/login':
            try:
                from modules.seguridad.runtime_diagnostics import project_instance_id
                database_url = str(app.config.get('DATABASE_URL', ''))
                parsed_database = urlsplit(database_url.replace('postgresql+psycopg://', 'postgresql://', 1))
                database_target = ''
                if parsed_database.hostname:
                    database_target = f"{parsed_database.hostname}:{parsed_database.port or 5432}{parsed_database.path or ''}"
                response.headers['X-Auth-Instance-ID'] = project_instance_id(app.config)
                response.headers['X-Auth-Environment'] = str(app.config.get('APP_ENV', 'unknown'))
                response.headers['X-Auth-Database-Backend'] = (
                    'postgresql' if database_url.startswith('postgresql')
                    else 'sqlite' if database_url.startswith('sqlite') else 'unknown'
                )
                response.headers['X-Auth-Request-ID'] = str(
                    (getattr(g, 'error_context', {}) or {}).get('client_request_id') or ''
                )
                response.headers['X-Auth-Database-Target'] = database_target
                response.headers['X-Auth-Env-SHA256'] = str(os.getenv('PROJECT_ENV_SHA256') or '')
            except Exception:
                pass
        return response

    # Los tests de contrato usan una aplicación mínima sin el hook de Flask.
    # La ruta de producción sí lo registra; el doble conserva compatibilidad.
    if hasattr(app, 'after_request'):
        app.after_request(attach_auth_correlation_headers)

    def single_tenant_mode() -> bool:
        return bool(app.config.get('SINGLE_TENANT_MODE', True))

    @app.route('/api/auth/login', methods=['POST'])
    def auth_login_seguro():
        started = time.monotonic()
        data = payload()
        username = (data.get('username') or data.get('email') or '').strip()
        password = data.get('password') or ''
        client_request_id = (request.headers.get('X-Client-Request-ID') or secrets.token_hex(8)).strip()[:100]
        identifier_hash = hash_token(username.lower())[:16] if username else ''
        db_retries = 0
        g.error_context = {
            'component': 'auth.login',
            'stage': 'input',
            'client_request_id': client_request_id,
            'identifier_hash': identifier_hash,
        }

        database_url = str(app.config.get('DATABASE_URL', ''))
        database_backend = 'postgresql' if database_url.startswith('postgresql') else 'sqlite' if database_url.startswith('sqlite') else 'unknown'
        _auth_debug(
            'request_started request_id=%s app_env=%s database_backend=%s database_configured=%s identifier_present=%s identifier_hash=%s content_type=%s content_length=%s payload_keys=%s password_length=%s',
            client_request_id,
            app.config.get('APP_ENV'),
            database_backend,
            bool(database_url),
            bool(username),
            identifier_hash,
            getattr(request, 'content_type', None),
            getattr(request, 'content_length', None),
            sorted(str(key) for key in data.keys()),
            len(password),
        )

        if not username or not password:
            _auth_debug(
                'input_rejected request_id=%s username_present=%s password_present=%s',
                client_request_id, bool(username), bool(password),
            )
            return jsonify({
                'error': 'Usuario/correo y contraseña requeridos.',
                'code': 'LOGIN_FIELDS_REQUIRED',
                'request_id': client_request_id,
            }), 400

        try:
            g.error_context['stage'] = 'load_login_state'
            retry_after, usuario, read_meta = load_login_state(database_path, username)
            db_retries += int(read_meta.get('db_retries', 0))
            _auth_debug(
                'database_read_ok request_id=%s user_found=%s user_id=%s role=%s active=%s state=%s retry_after=%s db_retries=%s',
                client_request_id,
                bool(usuario),
                usuario['id'] if usuario else None,
                usuario['rol'] if usuario else None,
                usuario['activo'] if usuario else None,
                usuario['estado'] if usuario else None,
                retry_after,
                db_retries,
            )
            if retry_after:
                _auth_debug('rate_limited request_id=%s retry_after=%s', client_request_id, retry_after)
                return _rate_limited_response(retry_after)

            valid_password = False
            if usuario:
                g.error_context['stage'] = 'verify_password_hash'
                try:
                    valid_password = bool(check_password_hash(str(usuario['password_hash'] or ''), password))
                except (TypeError, ValueError) as hash_exc:
                    # Un hash legado o dañado nunca debe provocar un 500 ni
                    # revelar información de la cuenta. Se trata como inválido.
                    _safe_warning(
                        'Hash de contraseña inválido para usuario_id=%s request_id=%s: %s',
                        usuario['id'], client_request_id, type(hash_exc).__name__,
                    )
                    valid_password = False

            _auth_debug(
                'password_checked request_id=%s user_found=%s hash_present=%s password_valid=%s',
                client_request_id,
                bool(usuario),
                bool(usuario and usuario['password_hash']),
                valid_password,
            )

            if not usuario or not valid_password:
                g.error_context['stage'] = 'record_failed_login_atomic'
                blocked, failure_meta = record_login_failure_atomic(
                    database_path,
                    username,
                    maximum=max(1, int(app.config.get('LOGIN_MAX_ATTEMPTS', 5))),
                    window_seconds=max(60, int(app.config.get('LOGIN_WINDOW_SECONDS', 900))),
                    lock_seconds=max(60, int(app.config.get('LOGIN_LOCK_SECONDS', 900))),
                    request_id=client_request_id,
                    ip=request.remote_addr,
                    user_agent=request.headers.get('User-Agent'),
                )
                db_retries += int(failure_meta.get('db_retries', 0))
                _auth_debug(
                    'login_rejected request_id=%s reason=%s blocked=%s db_retries=%s',
                    client_request_id,
                    'user_not_found' if not usuario else 'invalid_password',
                    bool(blocked),
                    db_retries,
                )
                if blocked:
                    return _rate_limited_response(blocked)
                duration_ms = int((time.monotonic() - started) * 1000)
                response = jsonify({
                    'error': 'Credenciales inválidas.',
                    'code': 'INVALID_CREDENTIALS',
                    'request_id': client_request_id,
                })
                response.status_code = 401
                response.headers['X-Client-Request-ID'] = client_request_id
                response.headers['X-Login-Duration-Ms'] = str(duration_ms)
                response.headers['X-Login-DB-Retries'] = str(db_retries)
                return response

            g.error_context['usuario_id'] = usuario['id']
            g.error_context['stage'] = 'validate_account_state'
            if int(usuario['activo'] or 0) != 1 or str(usuario['estado'] or 'ACTIVO').upper() != 'ACTIVO':
                audit(database_path, 'LOGIN_USUARIO_INACTIVO', despues={'usuario_id': usuario['id']})
                return jsonify({'error': 'Usuario inactivo o suspendido.', 'code': 'USER_INACTIVE'}), 403
            if usuario['rol'] != 'SUPERADMIN' and str(usuario['fundacion_estado'] or 'ACTIVA').upper() != 'ACTIVA':
                audit(database_path, 'LOGIN_FUNDACION_SUSPENDIDA', despues={
                    'usuario_id': usuario['id'],
                    'fundacion_id': usuario['fundacion_id'],
                })
                return jsonify({'error': 'La fundación está suspendida o vencida.', 'code': 'FOUNDATION_INACTIVE'}), 403

            # Una credencial correcta no crea sesión si la organización ya no
            # tiene servicio pagado o saldo. SUPERADMIN conserva acceso para
            # regularizar la cuenta sin quedar bloqueado por la misma regla.
            subscription = {}
            if usuario['rol'] != 'SUPERADMIN' and current_app.config.get('ENFORCE_LOGIN_BILLING', False):
                g.error_context['stage'] = 'validate_subscription_before_session'
                try:
                    from modules.facturacion_suscripcion.repository import BillingRepository
                    from modules.facturacion_suscripcion.services import BillingService
                    billing_service = BillingService(BillingRepository(database_path))
                    subscription = billing_service.get_subscription_snapshot(int(usuario['fundacion_id']), trusted_internal=True)
                except Exception as billing_exc:
                    _safe_warning('No se pudo validar facturación antes del login usuario_id=%s: %s', usuario['id'], type(billing_exc).__name__)
                    return jsonify({'error':'No fue posible validar el estado de facturación. Intenta nuevamente.','code':'BILLING_VALIDATION_UNAVAILABLE'}),503
                if not subscription:
                    audit(database_path,'LOGIN_SIN_SUSCRIPCION',despues={'usuario_id':usuario['id'],'fundacion_id':usuario['fundacion_id']})
                    return jsonify({'error':'Acceso bloqueado: la fundación no tiene una suscripción configurada.','code':'SUBSCRIPTION_MISSING'}),402
                subscription_state = str(subscription.get('estado') or '').upper()
                if subscription_state in {'VENCIDA','SUSPENDIDA','CANCELADA'}:
                    audit(database_path,'LOGIN_BLOQUEADO_PAGO',despues={'usuario_id':usuario['id'],'fundacion_id':usuario['fundacion_id'],'estado':subscription_state})
                    return jsonify({'error':'Acceso bloqueado por falta de pago o suscripción vencida. Comunícate con el administrador.','code':'SUBSCRIPTION_PAYMENT_REQUIRED'}),402
                if int(subscription.get('creditos_disponibles') or 0) <= 0:
                    audit(database_path,'LOGIN_BLOQUEADO_CREDITOS',despues={'usuario_id':usuario['id'],'fundacion_id':usuario['fundacion_id']})
                    return jsonify({'error':'Acceso bloqueado: la fundación agotó sus créditos. Solicita una recarga para ingresar.','code':'CREDITS_EXHAUSTED'}),402

            g.error_context['stage'] = 'create_session_atomic'
            token, user_payload, session_meta = create_login_session_atomic(
                database_path,
                usuario,
                identifiers=(username, usuario['username'], usuario['email']),
                request_id=client_request_id,
                ip=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
            )
            db_retries += int(session_meta.get('db_retries', 0))
            _auth_debug(
                'session_created request_id=%s user_id=%s token_type=opaque_session token_returned=%s db_retries=%s',
                client_request_id,
                usuario['id'],
                bool(token),
                db_retries,
            )

            # La sesión ya fue validada. La lectura de facturación usa un camino
            # interno explícito, sin modificar ``flask.g`` antes de que termine
            # la solicitud pública de autenticación.
            try:
                from modules.facturacion_suscripcion.repository import BillingRepository
                from modules.facturacion_suscripcion.services import BillingService
                billing_service = BillingService(BillingRepository(database_path))
                if subscription:
                    user_payload['suscripcion'] = subscription
                elif user_payload.get('fundacion_id'):
                    subscription = billing_service.get_subscription_snapshot(int(user_payload['fundacion_id']), trusted_internal=True)
                    if subscription:
                        user_payload['suscripcion'] = subscription
            except Exception as billing_exc:
                # La facturación complementa el payload, pero jamás debe impedir
                # que una credencial válida inicie sesión.
                _safe_warning(
                    'Suscripción no disponible durante login usuario_id=%s request_id=%s: %s',
                    usuario['id'], client_request_id, type(billing_exc).__name__,
                )

            duration_ms = int((time.monotonic() - started) * 1000)
            if duration_ms >= int(app.config.get('LOGIN_SLOW_THRESHOLD_MS', 1500)):
                _safe_warning(
                    'Login lento usuario_id=%s request_id=%s duration_ms=%s db_retries=%s stage=%s',
                    usuario['id'], client_request_id, duration_ms, db_retries, g.error_context.get('stage'),
                )
            else:
                _safe_info(
                    'Login exitoso usuario_id=%s request_id=%s duration_ms=%s db_retries=%s',
                    usuario['id'], client_request_id, duration_ms, db_retries,
                )

            response = jsonify({'token': token, 'usuario': user_payload, 'request_id': client_request_id})
            response.headers['X-Client-Request-ID'] = client_request_id
            response.headers['X-Login-Duration-Ms'] = str(duration_ms)
            response.headers['X-Login-DB-Retries'] = str(db_retries)
            response.headers['Server-Timing'] = f'auth;dur={duration_ms}'
            _auth_debug(
                'request_completed request_id=%s status=200 duration_ms=%s user_id=%s',
                client_request_id, duration_ms, usuario['id'],
            )
            return response

        except sqlite3.OperationalError as exc:
            if is_sqlite_busy_error(exc):
                duration_ms = int((time.monotonic() - started) * 1000)
                _safe_warning(
                    'SQLite ocupado durante login stage=%s request_id=%s duration_ms=%s db_retries=%s',
                    g.error_context.get('stage'), client_request_id, duration_ms, db_retries,
                )
                response = jsonify({
                    'error': 'La base local estaba ocupada y agotó los reintentos internos. La plataforma reintentará una vez.',
                    'code': 'LOGIN_DATABASE_BUSY',
                    'retry_after': 1,
                    'request_id': client_request_id,
                })
                response.status_code = 503
                response.headers['Retry-After'] = '1'
                response.headers['X-Client-Request-ID'] = client_request_id
                response.headers['X-Login-Duration-Ms'] = str(duration_ms)
                response.headers['X-Login-DB-Retries'] = str(db_retries)
                return response
            raise

    @app.route('/api/auth/me', methods=['GET'])
    def auth_me():
        usuario = user_dict(getattr(g, 'current_user', None) or {})
        if usuario.get('fundacion_id'):
            try:
                from modules.facturacion_suscripcion.repository import BillingRepository
                from modules.facturacion_suscripcion.services import BillingService
                billing_service = BillingService(BillingRepository(database_path))
                subscription = billing_service.get_subscription_snapshot(int(usuario['fundacion_id']))
                if subscription:
                    usuario['suscripcion'] = subscription
            except Exception:
                pass
        return jsonify({'usuario': usuario})

    @app.route('/api/auth/logout', methods=['POST'])
    def auth_logout():
        session_id = getattr(g, 'current_session_id', None)
        conn = connect(database_path)
        if session_id:
            conn.execute(
                "UPDATE sesiones_usuario SET activa=0, fecha_cierre=? WHERE id=?",
                (now_iso(), session_id),
            )
        else:
            token = extract_token()
            if token:
                conn.execute(
                    "UPDATE sesiones_usuario SET activa=0, fecha_cierre=? WHERE token_hash=?",
                    (now_iso(), hash_token(token)),
                )
        conn.commit()
        conn.close()
        audit(database_path, 'LOGOUT')
        return jsonify({'message': 'Sesión cerrada correctamente.'})

    @app.route('/api/auth/recuperar', methods=['POST'])
    def auth_recuperar():
        generic_message = 'Si la cuenta existe y tiene recuperación configurada, recibirás instrucciones de un solo uso.'
        data = payload()
        identifier = (data.get('email') or data.get('username') or '').strip()
        if not identifier:
            return jsonify({'message': generic_message})

        retry_after = rate_limit_status(database_path, 'recovery', identifier)
        if retry_after:
            return _rate_limited_response(retry_after)
        blocked = register_rate_limit_failure(
            database_path,
            'recovery',
            identifier,
            maximum=max(1, int(app.config.get('RECOVERY_MAX_ATTEMPTS', 5))),
            window_seconds=max(60, int(app.config.get('RECOVERY_WINDOW_SECONDS', 3600))),
            lock_seconds=max(60, int(app.config.get('RECOVERY_LOCK_SECONDS', 3600))),
        )

        conn = connect(database_path)
        usuario = conn.execute(
            """
            SELECT u.*, f.estado AS fundacion_estado
            FROM usuarios_app u LEFT JOIN fundaciones f ON f.id=u.fundacion_id
            WHERE lower(u.email)=lower(?) OR lower(u.username)=lower(?)
            """,
            (identifier, identifier),
        ).fetchone()
        if not usuario or str(usuario['estado'] or 'ACTIVO').upper() == 'ELIMINADO':
            conn.close()
            return jsonify({'message': generic_message, 'proximo_intento_en': blocked or 0})

        token = secrets.token_urlsafe(40)
        expires_minutes = max(10, int(app.config.get('PASSWORD_RESET_EXPIRES_MINUTES', 30)))
        exp = datetime.now() + timedelta(minutes=expires_minutes)
        conn.execute("UPDATE recuperacion_password SET usado=1 WHERE usuario_id=? AND usado=0", (usuario['id'],))
        cur = conn.execute(
            """
            INSERT INTO recuperacion_password
            (usuario_id, fundacion_id, token_hash, metodo, solicitado_por, ip, usado, fecha_creacion, fecha_expiracion)
            VALUES (?, ?, ?, 'EMAIL_LINK', NULL, ?, 0, ?, ?)
            """,
            (
                usuario['id'], usuario['fundacion_id'], hash_token(token), request.remote_addr,
                now_iso(), exp.isoformat(timespec='seconds'),
            ),
        )
        reset_request_id = int(cur.lastrowid)
        conn.commit()
        conn.close()

        reset_url = build_password_reset_url(token)
        delivered = bool(usuario['email']) and send_password_reset_email(usuario['email'], reset_url)
        response = {'message': generic_message, 'proximo_intento_en': blocked or 0}

        if delivered:
            # En producción se conserva una respuesta indistinguible para evitar
            # enumerar cuentas. La UI puede mostrar el mismo mensaje genérico.
            if str(app.config.get('APP_ENV') or '').lower() != 'production':
                response['delivery'] = 'email'
            audit(
                database_path,
                'RECUPERAR_PASSWORD_EMAIL',
                despues={'usuario_id': usuario['id'], 'fundacion_id': usuario['fundacion_id']},
            )
        elif _local_recovery_allowed(app):
            local_code = _generate_local_code(app)
            conn = connect(database_path)
            conn.execute(
                "UPDATE recuperacion_password SET token_hash=?, metodo='LOCAL_CODE' WHERE id=?",
                (hash_token(local_code), reset_request_id),
            )
            conn.commit()
            conn.close()
            response.update({
                'delivery': 'local_code',
                'local_recovery_code': local_code,
                'expira': exp.isoformat(timespec='seconds'),
                'message': 'Código temporal local generado. Úsalo una sola vez antes de que expire.',
            })
            audit(
                database_path,
                'RECUPERAR_PASSWORD_CODIGO_LOCAL',
                despues={'usuario_id': usuario['id'], 'fundacion_id': usuario['fundacion_id']},
            )
        else:
            debug_token_allowed = (
                bool(app.config.get('ALLOW_PASSWORD_RESET_TOKEN_RESPONSE', False))
                and app.config.get('APP_ENV') != 'production'
                and not bool(app.config.get('PUBLIC_TUNNEL_MODE', False))
            )
            if debug_token_allowed:
                response.update({
                    'delivery': 'development_token',
                    'development_reset_token': token,
                    'expira': exp.isoformat(timespec='seconds'),
                })
            else:
                conn = connect(database_path)
                conn.execute("UPDATE recuperacion_password SET usado=1 WHERE id=?", (reset_request_id,))
                conn.commit()
                conn.close()
                audit(
                    database_path,
                    'RECUPERACION_NO_ENVIADA',
                    despues={'usuario_id': usuario['id'], 'fundacion_id': usuario['fundacion_id']},
                )
        return jsonify(response)

    @app.route('/api/auth/restablecer', methods=['POST'])
    def auth_restablecer():
        data = payload()
        token = str(data.get('token') or data.get('codigo') or '').strip()
        password = data.get('password') or ''
        if not token:
            return jsonify({'error': 'Enlace o código requerido.'}), 400

        # La clave se deriva del código/token y de la IP dentro del servicio de
        # rate limiting. Un código errado no bloquea todas las recuperaciones de
        # la misma red, y el token nunca se guarda en texto plano.
        reset_identifier = hash_token(token)[:24]
        retry_after = rate_limit_status(database_path, 'password_reset', reset_identifier)
        if retry_after:
            return _rate_limited_response(retry_after)
        weak = _password_error(password)
        if weak:
            return weak

        conn = connect(database_path)
        rec = conn.execute(
            """
            SELECT r.*, u.username, u.email, u.fundacion_id, u.estado AS usuario_estado
            FROM recuperacion_password r
            JOIN usuarios_app u ON u.id=r.usuario_id
            WHERE r.token_hash=? AND r.usado=0
            """,
            (hash_token(token),),
        ).fetchone()
        if not rec:
            conn.close()
            blocked = register_rate_limit_failure(
                database_path,
                'password_reset',
                reset_identifier,
                maximum=max(3, int(app.config.get('RESET_MAX_ATTEMPTS', 8))),
                window_seconds=max(60, int(app.config.get('RESET_WINDOW_SECONDS', 900))),
                lock_seconds=max(60, int(app.config.get('RESET_LOCK_SECONDS', 900))),
            )
            if blocked:
                return _rate_limited_response(blocked)
            return jsonify({'error': 'Enlace o código inválido, usado o vencido.'}), 400
        try:
            expired = datetime.fromisoformat(rec['fecha_expiracion']) < datetime.now()
        except Exception:
            expired = True
        if expired:
            conn.execute("UPDATE recuperacion_password SET usado=1 WHERE id=?", (rec['id'],))
            conn.commit()
            conn.close()
            return jsonify({'error': 'Enlace o código inválido, usado o vencido.'}), 400
        if str(rec['usuario_estado'] or 'ACTIVO').upper() == 'ELIMINADO':
            conn.close()
            return jsonify({'error': 'La cuenta fue eliminada y debe ser restaurada por un administrador.'}), 409

        password_hash = generate_password_hash(password)
        if not check_password_hash(password_hash, password):
            conn.close()
            return jsonify({'error': 'No fue posible validar la nueva contraseña.'}), 500
        conn.execute(
            "UPDATE usuarios_app SET password_hash=?, debe_cambiar_password=0, fecha_actualizacion=? WHERE id=?",
            (password_hash, now_iso(), rec['usuario_id']),
        )
        conn.execute("UPDATE recuperacion_password SET usado=1 WHERE usuario_id=?", (rec['usuario_id'],))
        conn.execute(
            "UPDATE sesiones_usuario SET activa=0, fecha_cierre=? WHERE usuario_id=? AND activa=1",
            (now_iso(), rec['usuario_id']),
        )
        conn.commit()
        conn.close()
        clear_rate_limit(database_path, 'password_reset', reset_identifier)
        _clear_login_limits(database_path, rec['username'], rec['email'])
        audit(
            database_path,
            'PASSWORD_RESTABLECIDO',
            despues={
                'usuario_id': rec['usuario_id'],
                'fundacion_id': rec['fundacion_id'],
                'metodo': rec['metodo'],
            },
        )
        return jsonify({'message': 'Contraseña actualizada. Inicia sesión nuevamente.'})

    @app.route('/api/auth/cambiar-password', methods=['POST'])
    def auth_cambiar_password():
        user = getattr(g, 'current_user', {})
        data = payload()
        current_password = data.get('password_actual') or ''
        new_password = data.get('password_nueva') or ''
        weak = _password_error(new_password)
        if weak:
            return weak
        conn = connect(database_path)
        row = conn.execute("SELECT * FROM usuarios_app WHERE id=?", (user.get('id'),)).fetchone()
        if not row or not check_password_hash(row['password_hash'], current_password):
            conn.close()
            return jsonify({'error': 'La contraseña actual no es correcta.'}), 400
        if check_password_hash(row['password_hash'], new_password):
            conn.close()
            return jsonify({'error': 'La nueva contraseña debe ser diferente.'}), 400
        conn.execute(
            "UPDATE usuarios_app SET password_hash=?, debe_cambiar_password=0, fecha_actualizacion=? WHERE id=?",
            (generate_password_hash(new_password), now_iso(), row['id']),
        )
        conn.execute(
            "UPDATE sesiones_usuario SET activa=0, fecha_cierre=? WHERE usuario_id=? AND activa=1",
            (now_iso(), row['id']),
        )
        conn.commit()
        conn.close()
        audit(database_path, 'PASSWORD_CAMBIADO', despues={'usuario_id': row['id']})
        return jsonify({'message': 'Contraseña cambiada. Inicia sesión nuevamente.', 'reauthenticate': True})

    @app.route('/api/fundaciones', methods=['GET', 'POST'])
    def fundaciones():
        user = getattr(g, 'current_user', {})
        conn = connect(database_path)
        if request.method == 'GET':
            if single_tenant_mode():
                filas = conn.execute("SELECT * FROM fundaciones WHERE id=1").fetchall()
            elif user.get('rol') == 'SUPERADMIN':
                filas = conn.execute("SELECT * FROM fundaciones ORDER BY nombre").fetchall()
            else:
                filas = conn.execute("SELECT * FROM fundaciones WHERE id=?", (user.get('fundacion_id'),)).fetchall()
            conn.close()
            return jsonify({
                'fundaciones': [dict(f) for f in filas],
                'single_tenant_mode': single_tenant_mode(),
                'multi_tenant_strict': bool(app.config.get('MULTI_TENANT_STRICT', True)),
                'tenant_storage_isolation': bool(app.config.get('TENANT_STORAGE_ISOLATION', True)),
                'schema_version': int(app.config.get('MULTI_TENANT_SCHEMA_VERSION', 0) or 0),
            })
        if single_tenant_mode():
            conn.close()
            return jsonify({
                'error': 'Esta entrega segura funciona con una sola fundación. La creación multi-fundación está desactivada.',
                'code': 'SINGLE_TENANT_MODE',
            }), 403
        if user.get('rol') != 'SUPERADMIN':
            conn.close()
            return jsonify({'error': 'Solo SUPERADMIN puede crear fundaciones.'}), 403
        data = payload()
        nombre = str(data.get('nombre') or '').strip()
        foundation_email = _normalize_email(data.get('email')) if data.get('email') else None
        if not nombre:
            conn.close()
            return jsonify({'error': 'Nombre de fundación requerido.'}), 400
        nombre_identidad = _normalize_foundation_identity(nombre)
        duplicate = next((
            row for row in conn.execute("SELECT * FROM fundaciones ORDER BY id").fetchall()
            if _normalize_foundation_identity(row['nombre']) == nombre_identidad
        ), None)
        if duplicate:
            existing = dict(duplicate)
            estado_existente = str(existing.get('estado') or 'ACTIVA').upper()
            conn.close()
            return jsonify({
                'error': 'La fundación ya existe. Reutiliza el registro existente.',
                'code': 'FUNDACION_EXISTENTE',
                'fundacion_id': existing.get('id'),
                'fundacion': existing,
                'reutilizable': estado_existente == 'ACTIVA',
                'accion': 'USAR_EXISTENTE' if estado_existente == 'ACTIVA' else 'REACTIVAR',
            }), 409
        now = now_iso()
        try:
            cur = conn.execute("""
                INSERT INTO fundaciones
                (nombre, nit, representante, email, telefono, direccion, municipio, departamento, estado, plan, fecha_inicio, fecha_vencimiento, observaciones, fecha_creacion, fecha_actualizacion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                nombre, data.get('nit'), data.get('representante'), foundation_email, data.get('telefono'),
                data.get('direccion'), data.get('municipio'), data.get('departamento'), data.get('estado', 'ACTIVA'),
                data.get('plan', 'PRUEBA'), data.get('fecha_inicio') or now[:10], data.get('fecha_vencimiento'),
                data.get('observaciones'), now, now
            ))
            conn.commit()
            fid = int(cur.lastrowid)
            conn.close()

            # Cada fundación recibe almacenamiento físico independiente y una
            # suscripción inicial antes de quedar disponible para usuarios.
            try:
                storage = ensure_tenant_directories(app.config['DATA_DIR'], fid)

                # Suscripción inicial PREMIUM de piloto, corporación operativa,
                # catálogo UDS y minuta sanitizada. No se copian beneficiarios,
                # usuarios ni archivos de otra fundación.
                from modules.facturacion_suscripcion.repository import BillingRepository
                from modules.base_maestra.repository import BaseMaestraRepository
                from services.uds_catalog import ensure_catalog_units_sqlite
                from services.rpp_minutas_service import seed_minuta_sanitizada_desde_json

                BillingRepository(database_path).init_schema()
                base_repo = BaseMaestraRepository(database_path)
                corporacion_id = base_repo.ensure_corporacion_for_foundation(
                    fid,
                    nombre,
                    data.get('nit'),
                    data.get('representante'),
                    data.get('estado', 'ACTIVA'),
                )
                uds_seed = ensure_catalog_units_sqlite(database_path, fundacion_id=fid)

                compliance_conn = connect(database_path)
                compliance_conn.execute(
                    """
                    INSERT INTO reglas_cumplimiento
                    (documento_id, codigo, componente, descripcion, frecuencia, criterio,
                     nivel_alerta, activa, fundacion_id, fecha_creacion)
                    SELECT NULL, origen.codigo, origen.componente, origen.descripcion,
                           origen.frecuencia, origen.criterio, origen.nivel_alerta,
                           origen.activa, ?, ?
                    FROM reglas_cumplimiento AS origen
                    WHERE origen.fundacion_id=1
                      AND NOT EXISTS (
                          SELECT 1 FROM reglas_cumplimiento AS destino
                          WHERE destino.fundacion_id=? AND destino.codigo=origen.codigo
                      )
                    """,
                    (fid, now_iso(), fid),
                )
                compliance_conn.commit()
                compliance_conn.close()

                rpp_seed = seed_minuta_sanitizada_desde_json(
                    database_path,
                    Path(app.config['BASE_DIR']) / 'seed_data' / 'config' / 'rpp_minuta_base_2026_05.json',
                    fundacion_id=fid,
                    corporacion_id=corporacion_id,
                )
                bootstrap = {
                    'corporacion_id': corporacion_id,
                    'uds': uds_seed,
                    'reglas_cumplimiento': True,
                    'rpp': rpp_seed,
                }
            except Exception as exc:
                recovery = connect(database_path)
                recovery.execute(
                    "UPDATE fundaciones SET estado='CONFIGURACION_PENDIENTE', fecha_actualizacion=? WHERE id=?",
                    (now_iso(), fid),
                )
                recovery.commit()
                recovery.close()
                audit(
                    database_path,
                    'CREAR_FUNDACION_INCOMPLETA',
                    'fundaciones',
                    fid,
                    despues={'error': str(exc)},
                )
                return jsonify({
                    'error': 'La fundación fue creada, pero su almacenamiento o suscripción no pudo inicializarse.',
                    'code': 'TENANT_INITIALIZATION_FAILED',
                    'fundacion_id': fid,
                }), 500

            final_conn = connect(database_path)
            fundacion = final_conn.execute("SELECT * FROM fundaciones WHERE id=?", (fid,)).fetchone()
            final_conn.close()
            audit(database_path, 'CREAR_FUNDACION', 'fundaciones', fid, despues=dict(fundacion))
            return jsonify({
                'message': 'Fundación creada correctamente.',
                'fundacion': dict(fundacion),
                'storage': storage,
                'bootstrap': bootstrap,
            }), 201
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'error': 'Ya existe una fundación con ese nombre.'}), 409

    @app.route('/api/fundaciones/<int:fundacion_id>/dependencias', methods=['GET'])
    @require_roles('SUPERADMIN')
    def fundacion_dependencias(fundacion_id: int):
        conn = connect(database_path)
        foundation = conn.execute("SELECT * FROM fundaciones WHERE id=?", (fundacion_id,)).fetchone()
        if not foundation:
            conn.close()
            return jsonify({'error': 'Fundación no encontrada.'}), 404
        summary = _dependency_counts(conn, 'fundacion_id', fundacion_id, excluded={'fundaciones'})
        conn.close()
        return jsonify({
            'fundacion': dict(foundation),
            'dependencias': summary,
            'eliminacion': 'LOGICA',
            'nota': 'Los datos relacionados se conservan para auditoría; la fundación queda bloqueada y sin sesiones activas.',
        })

    @app.route('/api/fundaciones/<int:fundacion_id>', methods=['PUT', 'DELETE'])
    @require_roles('SUPERADMIN')
    def fundacion_detalle(fundacion_id: int):
        if single_tenant_mode() and fundacion_id != 1:
            return jsonify({'error': 'Fundación no disponible en modo de una sola fundación.', 'code': 'SINGLE_TENANT_MODE'}), 404
        if single_tenant_mode() and request.method == 'DELETE':
            return jsonify({'error': 'No se puede desactivar la única fundación del entorno.', 'code': 'SINGLE_TENANT_MODE'}), 403

        current_user = getattr(g, 'current_user', {}) or {}
        conn = connect(database_path)
        actual = conn.execute("SELECT * FROM fundaciones WHERE id=?", (fundacion_id,)).fetchone()
        if not actual:
            conn.close()
            return jsonify({'error': 'Fundación no encontrada.'}), 404

        if request.method == 'DELETE':
            accion = str(request.args.get('accion') or 'estado').strip().lower()
            nuevo_estado = str(request.args.get('estado') or 'SUSPENDIDA').strip().upper()
            if fundacion_id == int(current_user.get('fundacion_id') or 0) and nuevo_estado != 'ACTIVA':
                conn.close()
                return jsonify({
                    'error': 'No puedes suspender o eliminar la fundación de tu sesión actual.',
                    'code': 'CURRENT_TENANT_SUSPENSION_FORBIDDEN',
                }), 409

            if accion == 'eliminar':
                remaining = conn.execute(
                    """
                    SELECT COUNT(*) AS total FROM fundaciones
                    WHERE id<>? AND upper(COALESCE(estado,'ACTIVA'))='ACTIVA'
                    """,
                    (fundacion_id,),
                ).fetchone()
                if not remaining or int(remaining['total'] or 0) < 1:
                    conn.close()
                    return jsonify({
                        'error': 'Debe permanecer al menos una fundación activa.',
                        'code': 'LAST_ACTIVE_FOUNDATION_PROTECTED',
                    }), 409
                dependencies = _dependency_counts(conn, 'fundacion_id', fundacion_id, excluded={'fundaciones'})
                reason = str(request.args.get('motivo') or 'Eliminación solicitada desde administración')[:500]
                timestamp = now_iso()
                conn.execute(
                    """
                    UPDATE fundaciones
                    SET estado='ELIMINADA', eliminado_en=?, eliminado_por=?, motivo_eliminacion=?, fecha_actualizacion=?
                    WHERE id=?
                    """,
                    (timestamp, current_user.get('id'), reason, timestamp, fundacion_id),
                )
                conn.execute(
                    """
                    UPDATE usuarios_app
                    SET activo=0, estado=CASE WHEN upper(COALESCE(estado,'ACTIVO'))='ELIMINADO' THEN estado ELSE 'INACTIVO' END,
                        fecha_actualizacion=?
                    WHERE fundacion_id=?
                    """,
                    (timestamp, fundacion_id),
                )
                conn.execute(
                    "UPDATE sesiones_usuario SET activa=0, fecha_cierre=? WHERE fundacion_id=? AND activa=1",
                    (timestamp, fundacion_id),
                )
                conn.commit()
                conn.close()
                audit(
                    database_path,
                    'ELIMINAR_FUNDACION_LOGICA',
                    'fundaciones',
                    fundacion_id,
                    antes=dict(actual),
                    despues={'estado': 'ELIMINADA', 'dependencias': dependencies['total']},
                )
                return jsonify({
                    'message': 'Fundación eliminada de forma segura. Los registros se conservaron para auditoría.',
                    'eliminacion': 'LOGICA',
                    'dependencias': dependencies,
                })

            if nuevo_estado not in {'ACTIVA', 'SUSPENDIDA', 'VENCIDA', 'CONFIGURACION_PENDIENTE'}:
                conn.close()
                return jsonify({'error': 'Estado de fundación inválido.'}), 400
            timestamp = now_iso()
            if nuevo_estado == 'ACTIVA':
                conn.execute(
                    """
                    UPDATE fundaciones
                    SET estado='ACTIVA', eliminado_en=NULL, eliminado_por=NULL, motivo_eliminacion=NULL, fecha_actualizacion=?
                    WHERE id=?
                    """,
                    (timestamp, fundacion_id),
                )
            else:
                conn.execute(
                    "UPDATE fundaciones SET estado=?, fecha_actualizacion=? WHERE id=?",
                    (nuevo_estado, timestamp, fundacion_id),
                )
                conn.execute(
                    "UPDATE sesiones_usuario SET activa=0, fecha_cierre=? WHERE fundacion_id=? AND activa=1",
                    (timestamp, fundacion_id),
                )
            conn.commit()
            conn.close()
            audit(
                database_path,
                'CAMBIAR_ESTADO_FUNDACION',
                'fundaciones',
                fundacion_id,
                antes=dict(actual),
                despues={'estado': nuevo_estado},
            )
            return jsonify({
                'message': f'Fundación actualizada a estado {nuevo_estado}.',
                'nota': 'Al reactivar una fundación, sus usuarios deben activarse individualmente.' if nuevo_estado == 'ACTIVA' else '',
            })

        data = payload()
        fields = [
            'nombre', 'nit', 'representante', 'email', 'telefono', 'direccion',
            'municipio', 'departamento', 'estado', 'plan', 'fecha_inicio',
            'fecha_vencimiento', 'observaciones',
        ]
        values = {field: data.get(field, actual[field]) for field in fields}
        values['nombre'] = str(values['nombre'] or '').strip()
        values['email'] = _normalize_email(values['email']) if values['email'] else None
        values['estado'] = str(values['estado'] or 'ACTIVA').upper()
        if not values['nombre']:
            conn.close()
            return jsonify({'error': 'Nombre de fundación requerido.'}), 400
        if values['estado'] not in {'ACTIVA', 'SUSPENDIDA', 'VENCIDA', 'CONFIGURACION_PENDIENTE'}:
            conn.close()
            return jsonify({
                'error': 'Estado de fundación inválido. Usa la acción Eliminar para una eliminación lógica.',
                'code': 'FOUNDATION_DELETE_REQUIRES_ACTION',
            }), 400
        if fundacion_id == int(current_user.get('fundacion_id') or 0) and values['estado'] != 'ACTIVA':
            conn.close()
            return jsonify({'error': 'No puedes desactivar la fundación de tu sesión actual.'}), 409
        duplicate = conn.execute(
            "SELECT id FROM fundaciones WHERE id<>? AND lower(trim(nombre))=lower(trim(?))",
            (fundacion_id, values['nombre']),
        ).fetchone()
        if duplicate:
            conn.close()
            return jsonify({'error': 'Ya existe una fundación con ese nombre.'}), 409

        timestamp = now_iso()
        try:
            conn.execute(
                """
                UPDATE fundaciones
                SET nombre=?, nit=?, representante=?, email=?, telefono=?, direccion=?, municipio=?, departamento=?,
                    estado=?, plan=?, fecha_inicio=?, fecha_vencimiento=?, observaciones=?, fecha_actualizacion=?,
                    eliminado_en=CASE WHEN ?='ACTIVA' THEN NULL ELSE eliminado_en END,
                    eliminado_por=CASE WHEN ?='ACTIVA' THEN NULL ELSE eliminado_por END,
                    motivo_eliminacion=CASE WHEN ?='ACTIVA' THEN NULL ELSE motivo_eliminacion END
                WHERE id=?
                """,
                tuple(values[field] for field in fields)
                + (timestamp, values['estado'], values['estado'], values['estado'], fundacion_id),
            )
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'error': 'Ya existe una fundación con ese nombre o NIT.'}), 409
        if values['estado'] != 'ACTIVA':
            conn.execute(
                "UPDATE sesiones_usuario SET activa=0, fecha_cierre=? WHERE fundacion_id=? AND activa=1",
                (timestamp, fundacion_id),
            )
        conn.commit()
        updated = conn.execute("SELECT * FROM fundaciones WHERE id=?", (fundacion_id,)).fetchone()
        conn.close()
        audit(database_path, 'EDITAR_FUNDACION', 'fundaciones', fundacion_id, antes=dict(actual), despues=dict(updated))
        return jsonify({'message': 'Fundación actualizada.', 'fundacion': dict(updated)})

    @app.route('/api/usuarios', methods=['GET', 'POST'])
    def usuarios():
        user = getattr(g, 'current_user', {})
        conn = connect(database_path)
        if request.method == 'GET':
            select_sql = """
                SELECT u.id, u.username, u.email, u.rol, u.fundacion_id, u.activo, u.estado, u.nombre_completo,
                       u.telefono, u.fecha_creacion, u.fecha_ultima_conexion, u.debe_cambiar_password,
                       u.eliminado_en, u.eliminado_por, u.motivo_eliminacion,
                       f.nombre AS fundacion_nombre
                FROM usuarios_app u LEFT JOIN fundaciones f ON f.id = u.fundacion_id
            """
            if user.get('rol') == 'SUPERADMIN' and not single_tenant_mode():
                rows = conn.execute(select_sql + " ORDER BY f.nombre, u.username").fetchall()
            else:
                rows = conn.execute(select_sql + " WHERE u.fundacion_id=? ORDER BY u.username", (user.get('fundacion_id'),)).fetchall()
            conn.close()
            return jsonify({'usuarios': [dict(row) for row in rows], 'roles': ROLES_SISTEMA})

        data = payload()
        username = _normalize_username(data.get('username'))
        email = _normalize_email(data.get('email'))
        password = str(data.get('password') or '')
        role = str(data.get('rol') or '').upper()
        identity_error = _identity_error(username, email)
        if identity_error:
            conn.close()
            return jsonify({'error': identity_error}), 400
        if not password:
            conn.close()
            return jsonify({'error': 'password requerido.'}), 400
        weak = _password_error(password)
        if weak:
            conn.close()
            return weak
        if role not in ROLES_SISTEMA:
            conn.close()
            return jsonify({'error': 'Rol inválido.'}), 400

        foundation_id = 1 if single_tenant_mode() else (data.get('fundacion_id') or user.get('fundacion_id'))
        if user.get('rol') != 'SUPERADMIN':
            foundation_id = user.get('fundacion_id')
            if role == 'SUPERADMIN':
                conn.close()
                return jsonify({'error': 'No puedes crear usuarios SUPERADMIN.'}), 403
        try:
            foundation_id = int(foundation_id)
        except (TypeError, ValueError):
            conn.close()
            return jsonify({'error': 'Fundación inválida.'}), 400

        foundation = conn.execute("SELECT id, estado FROM fundaciones WHERE id=?", (foundation_id,)).fetchone()
        if not foundation:
            conn.close()
            return jsonify({'error': 'Fundación no encontrada.'}), 404
        if str(foundation['estado'] or '').upper() != 'ACTIVA':
            conn.close()
            return jsonify({'error': 'La fundación debe estar ACTIVA para crear usuarios.'}), 409
        duplicate = conn.execute(
            """
            SELECT id FROM usuarios_app
            WHERE lower(trim(username))=lower(trim(?)) OR lower(trim(email))=lower(trim(?))
            """,
            (username, email),
        ).fetchone()
        if duplicate:
            conn.close()
            return jsonify({'error': 'Usuario o correo ya existe.'}), 409

        password_hash = generate_password_hash(password)
        if not check_password_hash(password_hash, password):
            conn.close()
            return jsonify({'error': 'No fue posible validar la contraseña del nuevo usuario.'}), 500
        timestamp = now_iso()
        force_change = 1 if bool(data.get('debe_cambiar_password', False)) else 0
        try:
            cursor = conn.execute(
                """
                INSERT INTO usuarios_app
                (username, email, password_hash, rol, fundacion_id, activo, estado, nombre_completo,
                 telefono, debe_cambiar_password, fecha_creacion, fecha_actualizacion)
                VALUES (?, ?, ?, ?, ?, 1, 'ACTIVO', ?, ?, ?, ?, ?)
                """,
                (
                    username, email, password_hash, role, foundation_id,
                    str(data.get('nombre_completo') or username).strip(),
                    str(data.get('telefono') or '').strip() or None,
                    force_change, timestamp, timestamp,
                ),
            )
            conn.commit()
            user_id = int(cursor.lastrowid)
            created = conn.execute(
                """
                SELECT id, username, email, rol, fundacion_id, activo, estado, nombre_completo,
                       telefono, debe_cambiar_password
                FROM usuarios_app WHERE id=?
                """,
                (user_id,),
            ).fetchone()
            conn.close()
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'error': 'Usuario o correo ya existe.'}), 409

        _clear_login_limits(database_path, username, email)
        audit(database_path, 'CREAR_USUARIO', 'usuarios_app', user_id, despues=dict(created))
        return jsonify({
            'message': 'Usuario creado correctamente y habilitado para iniciar sesión.',
            'usuario': dict(created),
            'login_identifier': username,
        }), 201

    @app.route('/api/usuarios/<int:usuario_id>/dependencias', methods=['GET'])
    def usuario_dependencias(usuario_id: int):
        current_user = getattr(g, 'current_user', {}) or {}
        conn = connect(database_path)
        target = conn.execute("SELECT * FROM usuarios_app WHERE id=?", (usuario_id,)).fetchone()
        if not target:
            conn.close()
            return jsonify({'error': 'Usuario no encontrado.'}), 404
        if current_user.get('rol') != 'SUPERADMIN' and int(target['fundacion_id'] or 0) != int(current_user.get('fundacion_id') or 0):
            conn.close()
            return jsonify({'error': 'No puedes consultar usuarios de otra fundación.'}), 403
        summary = _user_dependency_summary(conn, usuario_id)
        conn.close()
        return jsonify({
            'usuario': user_dict(target),
            'dependencias': summary,
            'eliminacion': 'LOGICA',
            'nota': 'La eliminación segura conserva trazabilidad y datos históricos.',
        })

    @app.route('/api/usuarios/<int:usuario_id>/restablecer-password', methods=['POST'])
    def usuario_restablecer_password(usuario_id: int):
        current_user = getattr(g, 'current_user', {}) or {}
        data = payload()
        conn = connect(database_path)
        target = conn.execute("SELECT * FROM usuarios_app WHERE id=?", (usuario_id,)).fetchone()
        if not target:
            conn.close()
            return jsonify({'error': 'Usuario no encontrado.'}), 404
        if current_user.get('rol') != 'SUPERADMIN' and int(target['fundacion_id'] or 0) != int(current_user.get('fundacion_id') or 0):
            conn.close()
            return jsonify({'error': 'No puedes restablecer usuarios de otra fundación.'}), 403
        if current_user.get('rol') != 'SUPERADMIN' and str(target['rol'] or '').upper() == 'SUPERADMIN':
            conn.close()
            return jsonify({'error': 'No puedes restablecer una cuenta SUPERADMIN.'}), 403
        if int(current_user.get('id') or 0) == usuario_id:
            conn.close()
            return jsonify({'error': 'Usa la opción Cambiar contraseña para tu propia cuenta.'}), 409
        if str(target['estado'] or 'ACTIVO').upper() == 'ELIMINADO':
            conn.close()
            return jsonify({'error': 'Restaura el usuario antes de restablecer su contraseña.'}), 409

        supplied = str(data.get('password') or '')
        temporary_password = supplied or _temporary_password()
        weak = _password_error(temporary_password)
        if weak:
            conn.close()
            return weak
        password_hash = generate_password_hash(temporary_password)
        if not check_password_hash(password_hash, temporary_password):
            conn.close()
            return jsonify({'error': 'No fue posible validar la contraseña temporal.'}), 500

        reactivate = bool(data.get('reactivar', False))
        if reactivate:
            foundation = conn.execute("SELECT estado FROM fundaciones WHERE id=?", (target['fundacion_id'],)).fetchone()
            if not foundation or str(foundation['estado'] or '').upper() != 'ACTIVA':
                conn.close()
                return jsonify({'error': 'La fundación debe estar ACTIVA para reactivar el usuario.'}), 409
        timestamp = now_iso()
        conn.execute(
            """
            UPDATE usuarios_app
            SET password_hash=?, debe_cambiar_password=1,
                activo=CASE WHEN ? THEN 1 ELSE activo END,
                estado=CASE WHEN ? THEN 'ACTIVO' ELSE estado END,
                fecha_actualizacion=?
            WHERE id=?
            """,
            (password_hash, reactivate, reactivate, timestamp, usuario_id),
        )
        conn.execute("UPDATE recuperacion_password SET usado=1 WHERE usuario_id=?", (usuario_id,))
        conn.execute(
            "UPDATE sesiones_usuario SET activa=0, fecha_cierre=? WHERE usuario_id=? AND activa=1",
            (timestamp, usuario_id),
        )
        conn.commit()
        conn.close()
        _clear_login_limits(database_path, target['username'], target['email'])
        audit(
            database_path,
            'ADMIN_RESTABLECER_PASSWORD',
            'usuarios_app',
            usuario_id,
            antes={'activo': target['activo'], 'estado': target['estado']},
            despues={'debe_cambiar_password': True, 'reactivado': reactivate},
        )
        response = {
            'message': 'Contraseña temporal creada. El usuario deberá cambiarla al iniciar sesión.',
            'debe_cambiar_password': True,
            'reactivado': reactivate,
        }
        if not supplied:
            response['temporary_password'] = temporary_password
            response['mostrar_una_sola_vez'] = True
        return jsonify(response)

    @app.route('/api/usuarios/<int:usuario_id>', methods=['PUT', 'DELETE'])
    def usuario_detalle(usuario_id: int):
        current_user = getattr(g, 'current_user', {}) or {}
        conn = connect(database_path)
        actual = conn.execute("SELECT * FROM usuarios_app WHERE id=?", (usuario_id,)).fetchone()
        if not actual:
            conn.close()
            return jsonify({'error': 'Usuario no encontrado.'}), 404
        if current_user.get('rol') != 'SUPERADMIN' and int(actual['fundacion_id'] or 0) != int(current_user.get('fundacion_id') or 0):
            conn.close()
            return jsonify({'error': 'No puedes modificar usuarios de otra fundación.'}), 403

        if request.method == 'DELETE':
            if int(current_user.get('id') or 0) == usuario_id:
                conn.close()
                return jsonify({'error': 'No puedes desactivar o eliminar tu propia cuenta.'}), 400
            if str(actual['rol'] or '').upper() == 'SUPERADMIN' and int(actual['activo'] or 0) == 1:
                remaining = conn.execute(
                    """
                    SELECT COUNT(*) AS total FROM usuarios_app
                    WHERE id<>? AND rol='SUPERADMIN' AND activo=1 AND upper(COALESCE(estado,'ACTIVO'))='ACTIVO'
                    """,
                    (usuario_id,),
                ).fetchone()
                if not remaining or int(remaining['total'] or 0) < 1:
                    conn.close()
                    return jsonify({
                        'error': 'Debe permanecer al menos un SUPERADMIN activo.',
                        'code': 'LAST_SUPERADMIN_PROTECTED',
                    }), 409

            action = str(request.args.get('accion') or 'desactivar').lower()
            timestamp = now_iso()
            dependencies = _user_dependency_summary(conn, usuario_id)
            if action == 'eliminar':
                reason = str(request.args.get('motivo') or 'Eliminación solicitada desde administración')[:500]
                conn.execute(
                    """
                    UPDATE usuarios_app
                    SET activo=0, estado='ELIMINADO', eliminado_en=?, eliminado_por=?, motivo_eliminacion=?, fecha_actualizacion=?
                    WHERE id=?
                    """,
                    (timestamp, current_user.get('id'), reason, timestamp, usuario_id),
                )
                audit_action = 'ELIMINAR_USUARIO_LOGICO'
                message = 'Usuario eliminado de forma segura. Se conservó la trazabilidad.'
            else:
                state = str(request.args.get('estado') or 'INACTIVO').upper()
                if state not in {'INACTIVO', 'SUSPENDIDO'}:
                    conn.close()
                    return jsonify({'error': 'Estado de usuario inválido.'}), 400
                conn.execute(
                    "UPDATE usuarios_app SET activo=0, estado=?, fecha_actualizacion=? WHERE id=?",
                    (state, timestamp, usuario_id),
                )
                audit_action = 'DESACTIVAR_USUARIO'
                message = 'Usuario desactivado correctamente.'
            conn.execute(
                "UPDATE sesiones_usuario SET activa=0, fecha_cierre=? WHERE usuario_id=? AND activa=1",
                (timestamp, usuario_id),
            )
            conn.commit()
            conn.close()
            audit(
                database_path,
                audit_action,
                'usuarios_app',
                usuario_id,
                antes=dict(actual),
                despues={'estado': 'ELIMINADO' if action == 'eliminar' else state, 'dependencias': dependencies['total']},
            )
            return jsonify({'message': message, 'eliminacion': 'LOGICA' if action == 'eliminar' else None, 'dependencias': dependencies})

        data = payload()
        role = str(data.get('rol', actual['rol']) or '').upper()
        if role not in ROLES_SISTEMA:
            conn.close()
            return jsonify({'error': 'Rol inválido.'}), 400
        if current_user.get('rol') != 'SUPERADMIN' and role == 'SUPERADMIN':
            conn.close()
            return jsonify({'error': 'No puedes asignar el rol SUPERADMIN.'}), 403

        foundation_id = (
            1 if single_tenant_mode()
            else (data.get('fundacion_id', actual['fundacion_id']) if current_user.get('rol') == 'SUPERADMIN' else actual['fundacion_id'])
        )
        try:
            foundation_id = int(foundation_id)
        except (TypeError, ValueError):
            conn.close()
            return jsonify({'error': 'Fundación inválida.'}), 400
        foundation = conn.execute("SELECT id, estado FROM fundaciones WHERE id=?", (foundation_id,)).fetchone()
        if not foundation:
            conn.close()
            return jsonify({'error': 'Fundación no encontrada.'}), 404

        active = int(data.get('activo', actual['activo']))
        state = str(data.get('estado', actual['estado'] or 'ACTIVO') or 'ACTIVO').upper()
        if active == 1:
            state = 'ACTIVO'
        if active == 1 and str(foundation['estado'] or '').upper() != 'ACTIVA':
            conn.close()
            return jsonify({'error': 'La fundación debe estar ACTIVA para mantener un usuario activo.'}), 409
        if int(current_user.get('id') or 0) == usuario_id and (active != 1 or state != 'ACTIVO'):
            conn.close()
            return jsonify({'error': 'No puedes desactivar tu propia cuenta.'}), 400

        demotes_active_superadmin = (
            str(actual['rol'] or '').upper() == 'SUPERADMIN'
            and (role != 'SUPERADMIN' or active != 1 or state != 'ACTIVO')
        )
        if demotes_active_superadmin:
            remaining = conn.execute(
                """
                SELECT COUNT(*) AS total FROM usuarios_app
                WHERE id<>? AND rol='SUPERADMIN' AND activo=1 AND upper(COALESCE(estado,'ACTIVO'))='ACTIVO'
                """,
                (usuario_id,),
            ).fetchone()
            if not remaining or int(remaining['total'] or 0) < 1:
                conn.close()
                return jsonify({
                    'error': 'Debe permanecer al menos un SUPERADMIN activo.',
                    'code': 'LAST_SUPERADMIN_PROTECTED',
                }), 409

        username = _normalize_username(data.get('username', actual['username']))
        email = _normalize_email(data.get('email', actual['email']))
        identity_error = _identity_error(username, email)
        if identity_error:
            conn.close()
            return jsonify({'error': identity_error}), 400
        duplicate = conn.execute(
            """
            SELECT id FROM usuarios_app
            WHERE id<>? AND (lower(trim(username))=lower(trim(?)) OR lower(trim(email))=lower(trim(?)))
            """,
            (usuario_id, username, email),
        ).fetchone()
        if duplicate:
            conn.close()
            return jsonify({'error': 'Usuario o correo ya existe.'}), 409

        password_sql = ''
        extra_params = []
        password_changed = bool(data.get('password'))
        force_change = 1 if bool(data.get('debe_cambiar_password', actual['debe_cambiar_password'])) else 0
        if password_changed:
            password = str(data.get('password') or '')
            weak = _password_error(password)
            if weak:
                conn.close()
                return weak
            password_hash = generate_password_hash(password)
            if not check_password_hash(password_hash, password):
                conn.close()
                return jsonify({'error': 'No fue posible validar la nueva contraseña.'}), 500
            password_sql = ', password_hash=?'
            extra_params.append(password_hash)

        params = [
            username, email, role, foundation_id, active, state,
            str(data.get('nombre_completo', actual['nombre_completo']) or '').strip(),
            str(data.get('telefono', actual['telefono']) or '').strip() or None,
        ] + extra_params + [force_change, state, state, state, now_iso(), usuario_id]
        try:
            conn.execute(
                f"""
                UPDATE usuarios_app
                SET username=?, email=?, rol=?, fundacion_id=?, activo=?, estado=?, nombre_completo=?, telefono=?
                    {password_sql}, debe_cambiar_password=?,
                    eliminado_en=CASE WHEN ?='ACTIVO' THEN NULL ELSE eliminado_en END,
                    eliminado_por=CASE WHEN ?='ACTIVO' THEN NULL ELSE eliminado_por END,
                    motivo_eliminacion=CASE WHEN ?='ACTIVO' THEN NULL ELSE motivo_eliminacion END,
                    fecha_actualizacion=?
                WHERE id=?
                """,
                tuple(params),
            )
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'error': 'Usuario o correo ya existe.'}), 409

        security_changed = any([
            int(actual['fundacion_id'] or 0) != foundation_id,
            str(actual['rol'] or '').upper() != role,
            int(actual['activo'] or 0) != active,
            str(actual['estado'] or 'ACTIVO').upper() != state,
            str(actual['username'] or '') != username,
            str(actual['email'] or '').lower() != email,
            int(actual['debe_cambiar_password'] or 0) != force_change,
            password_changed,
        ])
        if security_changed:
            conn.execute(
                "UPDATE sesiones_usuario SET activa=0, fecha_cierre=? WHERE usuario_id=? AND activa=1",
                (now_iso(), usuario_id),
            )
        conn.commit()
        updated = conn.execute(
            """
            SELECT id, username, email, rol, fundacion_id, activo, estado, nombre_completo,
                   telefono, debe_cambiar_password, eliminado_en
            FROM usuarios_app WHERE id=?
            """,
            (usuario_id,),
        ).fetchone()
        conn.close()
        if password_changed or str(actual['username'] or '') != username or str(actual['email'] or '').lower() != email:
            _clear_login_limits(database_path, actual['username'], actual['email'], username, email)
        audit(database_path, 'EDITAR_USUARIO', 'usuarios_app', usuario_id, antes=dict(actual), despues=dict(updated))
        return jsonify({
            'message': 'Usuario actualizado.',
            'usuario': dict(updated),
            'sesiones_invalidadas': security_changed,
        })

    @app.route('/api/roles', methods=['GET'])
    def roles():
        return jsonify({'roles': ROLES_SISTEMA})

    @app.route('/api/seguridad/auditoria', methods=['GET'])
    @require_roles('SUPERADMIN', 'GERENTE')
    def auditoria_seguridad():
        user = getattr(g, 'current_user', {})
        conn = connect(database_path)
        if user.get('rol') == 'SUPERADMIN':
            filas = conn.execute("SELECT * FROM auditoria_seguridad ORDER BY fecha DESC LIMIT 300").fetchall()
        else:
            filas = conn.execute("SELECT * FROM auditoria_seguridad WHERE fundacion_id=? ORDER BY fecha DESC LIMIT 300", (user.get('fundacion_id'),)).fetchall()
        conn.close()
        return jsonify({'auditoria': [dict(f) for f in filas]})
