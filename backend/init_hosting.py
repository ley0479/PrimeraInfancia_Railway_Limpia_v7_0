#!/usr/bin/env python3
"""Inicializa almacenamiento, esquema y administrador en SQLite o PostgreSQL."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from contextlib import contextmanager
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'si', 'sí', 'on'}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def verify_seed_manifest(seed_dir: Path) -> None:
    manifest_path = seed_dir / 'seed_manifest.json'
    if not manifest_path.is_file():
        raise RuntimeError(f'No existe el manifiesto de plantillas limpias: {manifest_path}')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if not manifest.get('sanitizada') or manifest.get('contiene_datos_reales') is not False:
        raise RuntimeError('El manifiesto de plantillas no confirma sanitización completa.')
    records = manifest.get('plantillas') or manifest.get('files') or []
    if not isinstance(records, list) or not records:
        raise RuntimeError('El manifiesto de plantillas está vacío o es inválido.')
    for record in records:
        name = record.get('archivo') or record.get('name') or record.get('filename')
        expected = (record.get('sha256') or '').lower().strip()
        if not name or not expected:
            raise RuntimeError('Registro incompleto en el manifiesto de plantillas.')
        candidate = (seed_dir / name).resolve()
        if seed_dir.resolve() not in candidate.parents:
            raise RuntimeError(f'Ruta insegura en manifiesto de plantillas: {name}')
        if not candidate.is_file():
            raise RuntimeError(f'Plantilla declarada y ausente: {name}')
        if sha256_file(candidate) != expected:
            raise RuntimeError(f'Hash inválido para plantilla {name}.')


def bootstrap_core_schema(config_class) -> None:
    """Crea el esquema núcleo antes de importar módulos que dependen de él.

    ``app.py`` registra módulos durante su importación y algunos crean tablas
    con claves foráneas hacia ``fundaciones`` y ``usuarios_app``. En una base
    PostgreSQL vacía esas tablas deben existir antes de registrar las rutas.
    """
    from flask import Flask
    from database import configure_database, database, get_db_connection
    from models import Schema
    from modules.dbapi_compat import (
        _split_script,
        _translate_ddl,
        order_schema_statements_by_foreign_keys,
    )

    bootstrap_app = Flask('primera_infancia_schema_bootstrap')
    bootstrap_app.config.from_object(config_class)
    configure_database(bootstrap_app)
    schema = Schema.get_schema_sql()
    if database.is_postgresql:
        statements = order_schema_statements_by_foreign_keys(_split_script(schema))
        schema = ';\n'.join(_translate_ddl(statement) for statement in statements) + ';\n'
    with get_db_connection() as connection:
        connection.cursor().executescript(schema)
        connection.commit()

    # Los módulos comerciales y operativos referencian estas tablas durante
    # su propio registro. Prepararlas aquí evita depender de efectos laterales
    # del orden de imports de ``app.py``.
    from modules.seguridad.services import ensure_security_schema
    ensure_security_schema(str(config_class.DATABASE_PATH))
    from modules.base_maestra.repository import BaseMaestraRepository
    BaseMaestraRepository(config_class.DATABASE_PATH).init_schema()
    from migrations.migrate_universal_mapper_v7 import migrate as migrate_universal_mapper
    universal_mapper_migration = migrate_universal_mapper(str(config_class.DATABASE_PATH))
    print('[MIGRATION] universal mapper: ' + json.dumps(universal_mapper_migration, ensure_ascii=False), flush=True)

    # Los modulos comerciales se migran explicitamente en predeploy. Registrar
    # sus Blueprints durante el import de app.py queda como operacion sin DDL.
    from modules.facturacion_suscripcion.repository import BillingRepository
    from modules.facturacion_suscripcion.services import BillingService
    BillingService(BillingRepository(config_class.DATABASE_PATH)).init(force=True)
    from migrations.migrate_credit_ledger_v7 import migrate as migrate_credit_ledger
    credit_migration = migrate_credit_ledger(str(config_class.DATABASE_PATH))
    print('[MIGRATION] credit ledger: ' + json.dumps(credit_migration, ensure_ascii=False), flush=True)
    from modules.panel_comercial.services import PanelComercialService
    PanelComercialService(config_class.DATABASE_PATH).init_schema()

    from modules.motor_plantillas.services import init_schema as init_motor_plantillas_schema
    from services.rpp_minutas_service import init_schema as init_rpp_minutas_schema
    init_motor_plantillas_schema(config_class.DATABASE_PATH)
    init_rpp_minutas_schema(config_class.DATABASE_PATH)

    # Centro Documental: DDL exclusivamente durante init/predeploy.
    from migrations.migrate_centro_documental_v7 import migrate as migrate_centro_documental
    documents_migration = migrate_centro_documental(str(config_class.DATABASE_PATH))
    print('[MIGRATION] centro documental: ' + json.dumps(documents_migration, ensure_ascii=False), flush=True)

    # Motor IDP: sus repositorios no pueden depender de DDL durante el primer
    # request. El esquema se crea explícitamente en pre-deploy, igual que el
    # Centro Documental, antes de bloquear las escrituras de esquema runtime.
    from modules.idp_documental.services import init_schema as init_idp_schema
    init_idp_schema(str(config_class.DATABASE_PATH))
    print('[MIGRATION] idp documental: PASS', flush=True)

    # LÍA: preferencias, progreso, feedback y auditoría son tablas aditivas.
    # Deben crearse en pre-deploy porque el runtime productivo bloquea DDL.
    from modules.asistente_capacitacion.schema import SCHEMA_SQL as lia_schema_sql
    with get_db_connection() as connection:
        connection.cursor().executescript(lia_schema_sql)
        connection.commit()
    print('[MIGRATION] LIA assistant: PASS', flush=True)

    # Las bases anteriores a multi-tenant conservaban UNIQUE(nombre), lo que
    # impedia repetir legítimamente una UDS en otra fundacion.
    from migrations.migrate_unidades_tenant_unique_v7 import migrate as migrate_unidades_tenant_unique
    unidades_migration = migrate_unidades_tenant_unique(config_class.DATABASE_PATH)
    print('[MIGRATION] unidades tenant unique: ' + json.dumps(unidades_migration, ensure_ascii=False), flush=True)

    # La identidad global se migra exclusivamente durante init/pre-deploy.
    # El Blueprint institucional no ejecuta DDL al importarse ni por request.
    from migrations.migrate_identidad_global_v7 import migrate as migrate_identidad_global
    migrate_identidad_global(str(config_class.DATABASE_PATH))


def _safe_database_label(url: str, path: str) -> str:
    if str(url).startswith('postgresql'):
        return 'postgresql://***'
    return str(path)


@contextmanager
def _postgres_startup_lock():
    """Serializa migraciones entre despliegues Railway solapados.

    El advisory lock vive únicamente durante la inicialización y se libera aun
    si una migración falla. No bloquea el tráfico ordinario ni modifica datos.
    """
    url = str(os.getenv('DATABASE_URL') or '').strip()
    if not url:
        # En local, config carga .env; Railway ya entrega DATABASE_URL en el
        # entorno. Resolver ambos antes del lock mantiene la misma secuencia.
        from config import get_config
        url = str(get_config(os.getenv('APP_ENV')).DATABASE_URL or '').strip()
    if not url.startswith(('postgresql://', 'postgres://', 'postgresql+psycopg://')):
        yield
        return
    import psycopg

    dsn = url.replace('postgresql+psycopg://', 'postgresql://', 1)
    conn = psycopg.connect(dsn, autocommit=True)
    lock_key = 807_202_601  # constante exclusiva del inicializador del proyecto
    lock_timeout_seconds = max(5, min(120, int(os.getenv('MIGRATION_LOCK_TIMEOUT_SECONDS', '30'))))
    try:
        conn.execute(f"SET lock_timeout = '{lock_timeout_seconds}s'")
        print('[MIGRATION] waiting for PostgreSQL startup advisory lock', flush=True)
        conn.execute('SELECT pg_advisory_lock(%s)', (lock_key,))
        print('[MIGRATION] PostgreSQL startup advisory lock acquired', flush=True)
        # Un despliegue cancelado puede dejar temporalmente una conexión del
        # worker anterior ``idle in transaction`` conservando locks DDL. Ya
        # siendo el único migrador autorizado, cerrar solo esas sesiones
        # huérfanas de esta aplicación evita bloquear el nuevo esquema. No se
        # afectan peticiones activas, otros servicios ni transacciones nuevas.
        stale_rows = conn.execute(
            """
            SELECT pid
              FROM pg_stat_activity
             WHERE datname = current_database()
               AND usename = current_user
               AND pid <> pg_backend_pid()
               AND application_name = %s
               AND state = 'idle in transaction'
               AND xact_start < clock_timestamp() - interval '30 seconds'
            """,
            (str(os.getenv('DB_APPLICATION_NAME') or 'primera-infancia'),),
        ).fetchall()
        terminated = 0
        for row in stale_rows:
            result = conn.execute('SELECT pg_terminate_backend(%s)', (int(row[0]),)).fetchone()
            terminated += int(bool(result and result[0]))
        if terminated:
            print(f'[MIGRATION] terminated stale application transactions: {terminated}', flush=True)
        yield
    finally:
        try:
            conn.execute('SELECT pg_advisory_unlock(%s)', (lock_key,))
            print('[MIGRATION] PostgreSQL startup advisory lock released', flush=True)
        finally:
            conn.close()


def _main() -> int:
    os.environ.setdefault('APP_ENV', 'production')
    # El inicializador es la única fase autorizada para modificar el esquema.
    # Se asignan (no setdefault) para neutralizar valores heredados de Railway.
    os.environ['APP_SCHEMA_MIGRATION_MODE'] = '1'
    os.environ['SKIP_RUNTIME_SCHEMA_DDL'] = '0'
    git_sha = str(
        os.getenv('RAILWAY_GIT_COMMIT_SHA')
        or os.getenv('GIT_COMMIT_SHA')
        or os.getenv('BUILD_COMMIT')
        or 'unknown'
    ).strip()
    build_time = str(os.getenv('RAILWAY_DEPLOYMENT_START_TIME') or os.getenv('BUILD_TIME') or '').strip()
    from config import get_config
    from services.seed_sync import sync_managed_seed_tree

    config_class = get_config(os.environ.get('APP_ENV'))
    bootstrap_core_schema(config_class)
    print(
        f"[BUILD] APP_VERSION={getattr(config_class, 'APP_VERSION', 'unknown')} "
        f"GIT_SHA={git_sha} BUILT_AT={build_time or 'unknown'}",
        flush=True,
    )
    data_dir = Path(config_class.DATA_DIR)
    marker = data_dir / '.primera_infancia_initialized.json'
    marker_preexisting = marker.is_file()
    runtime_dirs = [
        data_dir,
        Path(config_class.UPLOAD_FOLDER),
        Path(config_class.TEMPLATES_FOLDER),
        Path(config_class.OUTPUT_FOLDER),
        Path(config_class.BACKUPS_FOLDER),
        Path(config_class.DOCUMENTOS_FOLDER),
        Path(config_class.CUENTAS_COBRO_FOLDER),
        Path(config_class.LOCAL_STORAGE_PATH),
        Path(config_class.LOG_FOLDER),
    ]
    for directory in runtime_dirs:
        directory.mkdir(parents=True, exist_ok=True)

    seed_dir = Path(config_class.SEED_TEMPLATES_FOLDER)
    verify_seed_manifest(seed_dir)
    sync_report = sync_managed_seed_tree(
        seed_dir,
        Path(config_class.TEMPLATES_FOLDER),
        data_dir=data_dir,
        backups_dir=Path(config_class.BACKUPS_FOLDER),
        allow_updates=env_bool('SYNC_MANAGED_TEMPLATES', True),
    )

    # El esquema ya esta preparado. Desde este punto, importar/registrar Flask
    # no tiene permiso de ejecutar DDL ni semillas.
    os.environ['APP_SCHEMA_MIGRATION_MODE'] = '0'
    os.environ['SKIP_RUNTIME_SCHEMA_DDL'] = '1'

    # app configura el Engine central antes de registrar los módulos.
    import app as app_module

    # Gate funcional de arranque: el import de app.py no puede ocultar fallos de
    # módulos críticos con un simple print. Si alguno no registró su Blueprint,
    # se cancela el despliegue antes de publicar una instancia parcial.
    required_blueprints = {
        'facturacion_suscripcion',
        'panel_comercial',
        'gestion_pedagogica',
        'gestion_coordinador',
        'calendario_inteligente',
        'calendario_alias',
        'planeacion_pedagogica',
        'base_maestra',
        'motor_plantillas',
        'idp_documental',
        'centro_planeacion',
        'integrity_stability',
    }
    registered_blueprints = set(app_module.app.blueprints)
    missing_blueprints = sorted(required_blueprints - registered_blueprints)
    if missing_blueprints:
        raise RuntimeError(
            'Módulos críticos no registrados; se bloquea el despliegue parcial: '
            + ', '.join(missing_blueprints)
        )
    print(
        '[STARTUP] critical blueprints PASS: ' + ', '.join(sorted(required_blueprints)),
        flush=True,
    )
    from database import database, get_db_connection
    from modules.seguridad.services import bootstrap_initial_admin
    from modules.seguridad.tenant_context import ensure_tenant_directories
    from services.rpp_minutas_service import seed_minuta_sanitizada_desde_json
    from services.uds_catalog import catalog_summary, ensure_catalog_units_sqlite, migrate_demo_units_sqlite

    # Continuamos dentro del contenedor de predeploy. El import anterior quedó
    # protegido; las escrituras de esquema explícitas de init_db sí están
    # autorizadas en esta fase y nunca se ejecutan en el worker web.
    os.environ['APP_SCHEMA_MIGRATION_MODE'] = '1'
    os.environ['SKIP_RUNTIME_SCHEMA_DDL'] = '0'
    app_module.init_db()
    if database.is_sqlite:
        from migrations.migrate_multitenant_phase3 import migrate as migrate_multitenant_phase3
        tenant_migration = migrate_multitenant_phase3(config_class.DATABASE_PATH)
    else:
        tenant_migration = {'engine': 'postgresql', 'status': 'schema-current'}

    ensure_tenant_directories(config_class.DATA_DIR, 1)
    admin_result = bootstrap_initial_admin(config_class.DATABASE_PATH, app_module.app.config)

    uds_migration = migrate_demo_units_sqlite(config_class.DATABASE_PATH)
    uds_seed = ensure_catalog_units_sqlite(config_class.DATABASE_PATH, fundacion_id=1)
    rpp_seed = seed_minuta_sanitizada_desde_json(
        config_class.DATABASE_PATH,
        BACKEND_DIR / 'seed_data' / 'config' / 'rpp_minuta_base_2026_05.json',
        fundacion_id=1,
        corporacion_id=1,
    )

    db_status = database.healthcheck()
    if not db_status.get('ok'):
        raise RuntimeError(f"Falló healthcheck de base: {db_status.get('error')}")

    with get_db_connection() as conn:
        user_count = int(conn.execute('SELECT COUNT(*) AS total FROM usuarios_app').fetchone()[0])
        superadmin_count = int(conn.execute(
            "SELECT COUNT(*) AS total FROM usuarios_app WHERE rol='SUPERADMIN' AND activo=1"
        ).fetchone()[0])
        beneficiary_count = int(conn.execute('SELECT COUNT(*) AS total FROM beneficiarios').fetchone()[0])
        unit_count = int(conn.execute('SELECT COUNT(*) AS total FROM unidades').fetchone()[0])

    if user_count < 1 or superadmin_count < 1:
        raise RuntimeError('La base inicializada no contiene un SUPERADMIN activo.')
    if admin_result.get('created') and beneficiary_count != 0:
        raise RuntimeError('Una base nueva no puede contener beneficiarios precargados.')
    if beneficiary_count != 0 and not env_bool('ALLOW_EXISTING_RUNTIME_DATA', False):
        print('ADVERTENCIA: la base ya contenía beneficiarios; no se modificaron ni borraron.', flush=True)
    if admin_result.get('configuration_mismatch'):
        print(
            'ADVERTENCIA: INITIAL_ADMIN_* no coincide con el SUPERADMIN existente; '
            'no se creó ni modificó ninguna cuenta.',
            flush=True,
        )
    if sync_report.get('preserved_custom'):
        print(
            'AVISO: se preservaron plantillas personalizadas distintas de las semillas gestionadas: '
            + ', '.join(sync_report['preserved_custom']),
            flush=True,
        )

    marker.write_text(json.dumps({
        'version': app_module.app.config.get('APP_VERSION'),
        'git_sha': git_sha,
        'build_time': build_time or None,
        'schema_migration_mode': True,
        'database_backend': database.dialect_name,
        'database': _safe_database_label(config_class.DATABASE_URL, config_class.DATABASE_PATH),
        'template_sync': {
            key: value for key, value in sync_report.items()
            if key in {'copied', 'updated', 'preserved_custom', 'backups', 'state_file'}
        },
        'admin_created': bool(admin_result.get('created')),
        'marker_preexisting': marker_preexisting,
        'users': user_count,
        'active_superadmins': superadmin_count,
        'beneficiaries': beneficiary_count,
        'units': unit_count,
        'uds_catalog': catalog_summary(),
        'uds_migration': uds_migration,
        'uds_seed': uds_seed,
        'rpp_seed': rpp_seed,
        'tenant_migration': tenant_migration,
        'health': db_status,
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    try:
        marker.chmod(0o600)
    except OSError:
        pass

    print(
        f"Inicialización correcta: {database.dialect_name}, {user_count} usuario(s), "
        f"{beneficiary_count} beneficiario(s), {unit_count} UDS; "
        f"plantillas nuevas={len(sync_report.get('copied') or [])}, "
        f"actualizadas={len(sync_report.get('updated') or [])}, "
        f"personalizadas preservadas={len(sync_report.get('preserved_custom') or [])}.",
        flush=True,
    )
    return 0


def main() -> int:
    with _postgres_startup_lock():
        return _main()


if __name__ == '__main__':
    raise SystemExit(main())
