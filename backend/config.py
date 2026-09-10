"""Configuración central segura para ejecución local y Railway."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent

if load_dotenv:
    # Solo para desarrollo local. Los archivos .env están excluidos del paquete.
    load_dotenv(PROJECT_DIR / ".env", override=False)
    load_dotenv(BACKEND_DIR / ".env", override=False)


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "si", "sí", "on"}


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _absolute_path(raw: str | None, default: Path, *, relative_to: Path = BACKEND_DIR) -> Path:
    path = Path(raw).expanduser() if raw and raw.strip() else default
    if not path.is_absolute():
        path = relative_to / path
    return path.resolve()


def resolve_path(name: str, default: Path, *, relative_to: Path = BACKEND_DIR) -> str:
    return str(_absolute_path(os.getenv(name), default, relative_to=relative_to))


def _default_data_dir() -> Path:
    # Railway expone automáticamente RAILWAY_VOLUME_MOUNT_PATH cuando hay volumen.
    mount = (os.getenv("DATA_DIR") or os.getenv("RAILWAY_VOLUME_MOUNT_PATH") or "").strip()
    return _absolute_path(mount, BACKEND_DIR, relative_to=PROJECT_DIR)


def _sqlite_url(path: str) -> str:
    return f"sqlite:///{Path(path).as_posix()}"


def normalize_database_url(raw: str) -> str:
    """Normaliza URLs suministradas por Railway y herramientas locales.

    Se usa psycopg 3 explícitamente para evitar diferencias entre imágenes y
    conservar un único driver en producción.
    """
    value = str(raw or "").strip()
    if value.startswith("postgres://"):
        value = "postgresql://" + value[len("postgres://"):]
    if value.startswith("postgresql://"):
        value = "postgresql+psycopg://" + value[len("postgresql://"):]
    return value


def resolve_postgresql_url_from_environment() -> str:
    """Resuelve PostgreSQL sin exponer credenciales ni aceptar localhost.

    Railway normalmente inyecta ``DATABASE_URL`` mediante una referencia. Como
    respaldo admite nombres de URL equivalentes y las variables PG* del plugin.
    """
    for name in ("DATABASE_URL", "DATABASE_PRIVATE_URL", "POSTGRES_URL", "POSTGRESQL_URL"):
        value = str(os.getenv(name, "") or "").strip()
        if value:
            return normalize_database_url(value)

    parts = {
        "host": str(os.getenv("PGHOST", "") or "").strip(),
        "port": str(os.getenv("PGPORT", "") or "").strip(),
        "user": str(os.getenv("PGUSER", "") or "").strip(),
        "password": str(os.getenv("PGPASSWORD", "") or ""),
        "database": str(os.getenv("PGDATABASE", "") or "").strip(),
    }
    if all(parts.values()):
        return (
            "postgresql+psycopg://"
            f"{quote(parts['user'], safe='')}:{quote(parts['password'], safe='')}@"
            f"{parts['host']}:{parts['port']}/{quote(parts['database'], safe='')}"
        )
    return ""


def password_policy_errors(password: str, minimum: int = 12) -> list[str]:
    errors: list[str] = []
    if len(password or "") < minimum:
        errors.append(f"mínimo {minimum} caracteres")
    if not re.search(r"[A-ZÁÉÍÓÚÑ]", password or ""):
        errors.append("una mayúscula")
    if not re.search(r"[a-záéíóúñ]", password or ""):
        errors.append("una minúscula")
    if not re.search(r"\d", password or ""):
        errors.append("un número")
    if not re.search(r"[^A-Za-z0-9ÁÉÍÓÚÑáéíóúñ]", password or ""):
        errors.append("un símbolo")
    return errors


class BaseConfig:
    APP_ENV = os.getenv("APP_ENV", os.getenv("FLASK_ENV", "development")).lower()
    APP_VERSION = os.getenv("APP_VERSION", "2.7.2-document-center")
    BIBLIOTECA_REMOTE_CHECKS_ENABLED = os.getenv("BIBLIOTECA_REMOTE_CHECKS_ENABLED", "false").lower() in {"1", "true", "si", "sí"}
    BIBLIOTECA_ALLOWED_DOMAINS = os.getenv("BIBLIOTECA_ALLOWED_DOMAINS", "icbf.gov.co,www.icbf.gov.co")
    MOTOR_GESTION_ENABLED = os.getenv("MOTOR_GESTION_ENABLED", "true").lower() in {"1", "true", "si", "sí"}
    MOTOR_GESTION_MAX_EXPORT_ROWS = int(os.getenv("MOTOR_GESTION_MAX_EXPORT_ROWS", "5000"))
    BUILD_COMMIT = os.getenv("BUILD_COMMIT", os.getenv("RAILWAY_GIT_COMMIT_SHA", "unknown"))
    BUILD_DATE = os.getenv("BUILD_DATE", "unknown")
    PROJECT_INSTANCE_ID = os.getenv("PROJECT_INSTANCE_ID", "").strip()

    BASE_DIR = str(BACKEND_DIR)
    PROJECT_DIR = str(PROJECT_DIR)
    DATA_DIR = str(_default_data_dir())
    SEED_TEMPLATES_FOLDER = str(BACKEND_DIR / "seed_data" / "templates_originales")

    DATABASE_PATH = resolve_path("DATABASE_PATH", Path(DATA_DIR) / "database.sqlite3")
    DATABASE_URL = resolve_postgresql_url_from_environment() or _sqlite_url(DATABASE_PATH)
    ENABLE_POSTGRESQL_RUNTIME = env_bool("ENABLE_POSTGRESQL_RUNTIME", True)
    REQUIRE_POSTGRESQL_IN_PRODUCTION = env_bool("REQUIRE_POSTGRESQL_IN_PRODUCTION", True)
    INTEGRITY_ENGINE_ENABLED = env_bool("INTEGRITY_ENGINE_ENABLED", True)
    METRICS_ENABLED = env_bool("METRICS_ENABLED", True)
    ENABLE_CREDIT_ENFORCEMENT = env_bool("ENABLE_CREDIT_ENFORCEMENT", False)
    ENFORCE_LOGIN_BILLING = env_bool("ENFORCE_LOGIN_BILLING", False)
    ENABLE_CREDIT_ALERTS = env_bool("ENABLE_CREDIT_ALERTS", True)
    ENABLE_UNIVERSAL_DATA_MAPPER = env_bool("ENABLE_UNIVERSAL_DATA_MAPPER", False)
    UNIVERSAL_IMPORT_MAX_BYTES = env_int("UNIVERSAL_IMPORT_MAX_BYTES", 52_428_800)
    METRICS_TOKEN = os.getenv("METRICS_TOKEN", "").strip()
    READINESS_MAX_DB_LATENCY_MS = env_int("READINESS_MAX_DB_LATENCY_MS", 2000)
    OBSERVABILITY_SLOW_REQUEST_MS = env_int("OBSERVABILITY_SLOW_REQUEST_MS", 2000)
    SQLITE_TIMEOUT_SECONDS = env_int("SQLITE_TIMEOUT_SECONDS", 30)
    DB_POOL_SIZE = env_int("DB_POOL_SIZE", 8)
    DB_MAX_OVERFLOW = env_int("DB_MAX_OVERFLOW", 12)
    DB_POOL_TIMEOUT_SECONDS = env_int("DB_POOL_TIMEOUT_SECONDS", 10)
    DB_POOL_RECYCLE_SECONDS = env_int("DB_POOL_RECYCLE_SECONDS", 900)
    DB_CONNECT_TIMEOUT_SECONDS = env_int("DB_CONNECT_TIMEOUT_SECONDS", 10)
    DB_STATEMENT_TIMEOUT_MS = env_int("DB_STATEMENT_TIMEOUT_MS", 30000)
    DB_APPLICATION_NAME = os.getenv("DB_APPLICATION_NAME", "primera-infancia").strip() or "primera-infancia"

    UPLOAD_FOLDER = resolve_path("UPLOAD_FOLDER", Path(DATA_DIR) / "uploads")
    TEMPLATES_FOLDER = resolve_path("TEMPLATES_FOLDER", Path(DATA_DIR) / "templates_originales")
    OUTPUT_FOLDER = resolve_path("OUTPUT_FOLDER", Path(DATA_DIR) / "archivos_actualizados")
    BACKUPS_FOLDER = resolve_path("BACKUPS_FOLDER", Path(DATA_DIR) / "backups")
    DOCUMENTOS_FOLDER = resolve_path("DOCUMENTOS_FOLDER", Path(DATA_DIR) / "documentos_institucionales")
    CUENTAS_COBRO_FOLDER = resolve_path("CUENTAS_COBRO_FOLDER", Path(DATA_DIR) / "cuentas_cobro_plantillas")
    LOCAL_STORAGE_PATH = resolve_path("LOCAL_STORAGE_PATH", Path(DATA_DIR) / "storage")
    LOG_FOLDER = resolve_path("LOG_FOLDER", Path(DATA_DIR) / "logs")

    SECRET_KEY = os.getenv("SECRET_KEY", "development-only-change-me")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "development-jwt-only-change-me")

    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "").strip()
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").strip()
    RAILWAY_PUBLIC_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip()
    PUBLIC_APP_URL = os.getenv("PUBLIC_APP_URL", FRONTEND_ORIGIN).rstrip("/")
    SYNC_MANAGED_TEMPLATES = env_bool("SYNC_MANAGED_TEMPLATES", True)

    STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local").lower().strip()
    S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "")
    S3_REGION = os.getenv("S3_REGION", "")
    S3_BUCKET = os.getenv("S3_BUCKET", "")
    S3_ACCESS_KEY_ID = os.getenv("S3_ACCESS_KEY_ID", "")
    S3_SECRET_ACCESS_KEY = os.getenv("S3_SECRET_ACCESS_KEY", "")
    S3_USE_SSL = env_bool("S3_USE_SSL", True)

    SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "primera_infancia_session")
    SESSION_LIFETIME_MINUTES = env_int("SESSION_LIFETIME_MINUTES", 720)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", False)

    MIN_PASSWORD_LENGTH = env_int("MIN_PASSWORD_LENGTH", 12)
    INITIAL_ADMIN_USERNAME = os.getenv("INITIAL_ADMIN_USERNAME", "").strip()
    INITIAL_ADMIN_EMAIL = os.getenv("INITIAL_ADMIN_EMAIL", "").strip()
    INITIAL_ADMIN_PASSWORD = os.getenv("INITIAL_ADMIN_PASSWORD", "")
    INITIAL_ADMIN_NAME = os.getenv("INITIAL_ADMIN_NAME", "Administrador inicial").strip()
    INITIAL_ADMIN_FORCE_PASSWORD_CHANGE = env_bool("INITIAL_ADMIN_FORCE_PASSWORD_CHANGE", True)
    INITIAL_FOUNDATION_NAME = os.getenv("INITIAL_FOUNDATION_NAME", "Entorno de pruebas").strip()

    LOGIN_MAX_ATTEMPTS = env_int("LOGIN_MAX_ATTEMPTS", 5)
    LOGIN_WINDOW_SECONDS = env_int("LOGIN_WINDOW_SECONDS", 900)
    LOGIN_LOCK_SECONDS = env_int("LOGIN_LOCK_SECONDS", 900)
    # Presupuesto exclusivo del login. Los módulos operativos conservan SQLITE_TIMEOUT_SECONDS.
    LOGIN_DB_RETRY_ATTEMPTS = env_int("LOGIN_DB_RETRY_ATTEMPTS", 4)
    LOGIN_DB_BUSY_TIMEOUT_MS = env_int("LOGIN_DB_BUSY_TIMEOUT_MS", 150)
    LOGIN_DB_RETRY_BASE_MS = env_int("LOGIN_DB_RETRY_BASE_MS", 50)
    LOGIN_DB_RETRY_BUDGET_MS = env_int("LOGIN_DB_RETRY_BUDGET_MS", 1200)
    LOGIN_SLOW_THRESHOLD_MS = env_int("LOGIN_SLOW_THRESHOLD_MS", 1500)
    # Diagnostico temporal y seguro del flujo de autenticacion. Nunca registra
    # contrasenas, hashes, tokens ni la DATABASE_URL completa.
    AUTH_LOGIN_DEBUG = env_bool("AUTH_LOGIN_DEBUG", False)
    RECOVERY_MAX_ATTEMPTS = env_int("RECOVERY_MAX_ATTEMPTS", 5)
    RECOVERY_WINDOW_SECONDS = env_int("RECOVERY_WINDOW_SECONDS", 3600)
    RECOVERY_LOCK_SECONDS = env_int("RECOVERY_LOCK_SECONDS", 3600)

    PASSWORD_RESET_EXPIRES_MINUTES = env_int("PASSWORD_RESET_EXPIRES_MINUTES", 30)
    ALLOW_PASSWORD_RESET_TOKEN_RESPONSE = env_bool("ALLOW_PASSWORD_RESET_TOKEN_RESPONSE", False)
    # Alternativa estrictamente local cuando no existe proveedor de correo.
    # Se desactiva en producción y mientras PUBLIC_TUNNEL_MODE está activo.
    ALLOW_LOCAL_RECOVERY_CODE = env_bool("ALLOW_LOCAL_RECOVERY_CODE", False)
    LOCAL_RECOVERY_CODE_LENGTH = env_int("LOCAL_RECOVERY_CODE_LENGTH", 10)
    RESET_MAX_ATTEMPTS = env_int("RESET_MAX_ATTEMPTS", 8)
    RESET_WINDOW_SECONDS = env_int("RESET_WINDOW_SECONDS", 900)
    RESET_LOCK_SECONDS = env_int("RESET_LOCK_SECONDS", 900)
    PASSWORD_RESET_PUBLIC_URL = os.getenv("PASSWORD_RESET_PUBLIC_URL", PUBLIC_APP_URL).rstrip("/")
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    SMTP_PORT = env_int("SMTP_PORT", 587)
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "").strip()
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
    SMTP_USE_TLS = env_bool("SMTP_USE_TLS", True)
    SMTP_USE_SSL = env_bool("SMTP_USE_SSL", False)
    SMTP_TIMEOUT_SECONDS = env_int("SMTP_TIMEOUT_SECONDS", 15)
    PASSWORD_RESET_FROM_EMAIL = os.getenv("PASSWORD_RESET_FROM_EMAIL", "").strip() or SMTP_USERNAME

    ALLOW_LEGACY_QUERY_TOKENS = env_bool("ALLOW_LEGACY_QUERY_TOKENS", False)
    ENABLE_LEGACY_TENANT_BACKFILL = env_bool("ENABLE_LEGACY_TENANT_BACKFILL", False)

    MAX_CONTENT_LENGTH = env_int("MAX_CONTENT_LENGTH", 50 * 1024 * 1024)
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    FORCE_HTTPS = env_bool("FORCE_HTTPS", False)
    TRUSTED_PROXY_COUNT = env_int("TRUSTED_PROXY_COUNT", 0)
    BACKUP_RETENTION_DAYS = env_int("BACKUP_RETENTION_DAYS", 90)
    DEMO_MODE = env_bool("DEMO_MODE", False)

    # El valor seguro por omisión continúa siendo una sola fundación. La
    # entrega 2.4.1 mantiene el piloto únicamente mediante variables explícitas,
    # junto con el guard SQL, el esquema v3 y almacenamiento físico aislado.
    SINGLE_TENANT_MODE = env_bool("SINGLE_TENANT_MODE", True)
    # Confirmación explícita requerida para un despliegue multi-fundación.
    ALLOW_EXPERIMENTAL_MULTI_TENANT = env_bool("ALLOW_EXPERIMENTAL_MULTI_TENANT", False)
    MULTI_TENANT_STRICT = env_bool("MULTI_TENANT_STRICT", True)
    TENANT_STORAGE_ISOLATION = env_bool("TENANT_STORAGE_ISOLATION", True)
    MULTI_TENANT_SCHEMA_VERSION = env_int("MULTI_TENANT_SCHEMA_VERSION", 3)

    FLASK_HOST = os.getenv("FLASK_HOST", os.getenv("HOST", "127.0.0.1"))
    FLASK_PORT = env_int("FLASK_PORT", env_int("PORT", 5000))
    FRONTEND_PORT = env_int("FRONTEND_PORT", 8080)
    SERVER_MODE = os.getenv("SERVER_MODE", "LOCAL")
    PUBLIC_TUNNEL_MODE = env_bool("PUBLIC_TUNNEL_MODE", False)

    SQLALCHEMY_ENGINE_OPTIONS: dict[str, Any] = {
        "pool_pre_ping": True,
        "future": True,
    }


class DevelopmentConfig(BaseConfig):
    APP_ENV = "development"
    DEBUG = env_bool("FLASK_DEBUG", False)
    TESTING = False
    SESSION_COOKIE_SECURE = False


class TestingConfig(BaseConfig):
    APP_ENV = "testing"
    DEBUG = False
    TESTING = True
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False


class ProductionConfig(BaseConfig):
    APP_ENV = "production"
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    FORCE_HTTPS = env_bool("FORCE_HTTPS", True)  # ProxyFix conserva el esquema externo; healthcheck está exento.
    TRUSTED_PROXY_COUNT = env_int("TRUSTED_PROXY_COUNT", 1)


CONFIGS = {
    "development": DevelopmentConfig,
    "dev": DevelopmentConfig,
    "testing": TestingConfig,
    "test": TestingConfig,
    "production": ProductionConfig,
    "prod": ProductionConfig,
}


def get_config(name: str | None = None):
    selected = (name or os.getenv("APP_ENV") or os.getenv("FLASK_ENV") or "development").lower()
    return CONFIGS.get(selected, DevelopmentConfig)


def validate_runtime_config(config: dict[str, Any]) -> None:
    """Rechaza configuraciones productivas inseguras antes de abrir el servicio."""
    if str(config.get("APP_ENV", "")).lower() != "production":
        return

    errors: list[str] = []
    secret = str(config.get("SECRET_KEY", "")).strip()
    jwt_secret = str(config.get("JWT_SECRET_KEY", "")).strip()
    invalid = {
        "", "development-only-change-me", "development-jwt-only-change-me",
        "your-secret-key-change-in-production", "your-jwt-secret-change-in-production",
    }
    if secret in invalid or len(secret) < 32:
        errors.append("SECRET_KEY debe ser aleatoria y tener al menos 32 caracteres.")
    if jwt_secret in invalid or len(jwt_secret) < 32:
        errors.append("JWT_SECRET_KEY debe ser distinta y tener al menos 32 caracteres.")
    if secret and jwt_secret and secret == jwt_secret:
        errors.append("SECRET_KEY y JWT_SECRET_KEY no pueden ser iguales.")

    username = str(config.get("INITIAL_ADMIN_USERNAME", "")).strip()
    email = str(config.get("INITIAL_ADMIN_EMAIL", "")).strip()
    password = str(config.get("INITIAL_ADMIN_PASSWORD", ""))
    # La existencia de cuentas se valida contra la base durante init_hosting.
    # Aquí solo se valida un conjunto INITIAL_ADMIN cuando fue suministrado,
    # evitando exigirlo en cada reinicio de una base PostgreSQL ya inicializada.
    any_admin_value = bool(username or email or password)
    if any_admin_value:
        if not username:
            errors.append("INITIAL_ADMIN_USERNAME debe acompañar las demás variables iniciales.")
        if not email or "@" not in email:
            errors.append("INITIAL_ADMIN_EMAIL debe ser un correo válido.")
        policy_errors = password_policy_errors(password, int(config.get("MIN_PASSWORD_LENGTH", 12)))
        if policy_errors:
            errors.append("INITIAL_ADMIN_PASSWORD requiere " + ", ".join(policy_errors) + ".")
        if username.lower() == "admin" and password.lower() in {"admin", "admin123", "password"}:
            errors.append("No se permiten credenciales administrativas predeterminadas.")

    if config.get("STORAGE_BACKEND") not in {"local", "s3"}:
        errors.append("STORAGE_BACKEND debe ser local o s3.")
    if str(config.get("ALLOWED_ORIGINS", "")).strip() == "*":
        errors.append("ALLOWED_ORIGINS=* no está permitido en producción.")
    if config.get("ALLOW_LEGACY_QUERY_TOKENS"):
        errors.append("ALLOW_LEGACY_QUERY_TOKENS debe permanecer desactivado en producción.")
    if config.get("ALLOW_PASSWORD_RESET_TOKEN_RESPONSE"):
        errors.append("ALLOW_PASSWORD_RESET_TOKEN_RESPONSE debe permanecer desactivado en producción.")
    if config.get("ALLOW_LOCAL_RECOVERY_CODE"):
        errors.append("ALLOW_LOCAL_RECOVERY_CODE debe permanecer desactivado en producción.")
    if not config.get("FORCE_HTTPS", True):
        errors.append("FORCE_HTTPS debe permanecer activado en esta entrega Railway.")
    if not Path(str(config.get("DATA_DIR", ""))).is_absolute():
        errors.append("DATA_DIR debe ser una ruta absoluta.")
    database_url = str(config.get("DATABASE_URL", "")).strip()
    if database_url.startswith("postgresql"):
        if not database_url.startswith("postgresql+psycopg://"):
            errors.append("DATABASE_URL de PostgreSQL debe usar el driver psycopg normalizado.")
    elif database_url.startswith("sqlite"):
        if config.get("REQUIRE_POSTGRESQL_IN_PRODUCTION", True):
            errors.append("PostgreSQL es obligatorio en producción; SQLite queda reservado para recuperación local y pruebas.")
    else:
        errors.append("DATABASE_URL debe usar PostgreSQL o SQLite.")
    if not config.get("SINGLE_TENANT_MODE", True):
        if not config.get("ALLOW_EXPERIMENTAL_MULTI_TENANT", False):
            errors.append(
                "La operación multi-fundación requiere "
                "ALLOW_EXPERIMENTAL_MULTI_TENANT=true como confirmación explícita."
            )
        if not config.get("MULTI_TENANT_STRICT", True):
            errors.append("MULTI_TENANT_STRICT debe permanecer activado en modo multi-fundación.")
        if not config.get("TENANT_STORAGE_ISOLATION", True):
            errors.append("TENANT_STORAGE_ISOLATION debe permanecer activado en modo multi-fundación.")
        if int(config.get("MULTI_TENANT_SCHEMA_VERSION", 0) or 0) < 3:
            errors.append("MULTI_TENANT_SCHEMA_VERSION debe ser 3 o superior.")

    if errors:
        raise RuntimeError("Configuración de producción inválida: " + " ".join(errors))
