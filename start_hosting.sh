#!/usr/bin/env bash
set -Eeuo pipefail
umask 027

export APP_ENV="${APP_ENV:-production}"
export DATA_DIR="${DATA_DIR:-${RAILWAY_VOLUME_MOUNT_PATH:-/data}}"
export PORT="${PORT:-5000}"

# Railway monta el volumen en tiempo de ejecución. El proceso de entrada puede
# preparar sus permisos como root, pero Flask/Gunicorn nunca queda ejecutándose
# con privilegios de root.
if [[ "$(id -u)" -eq 0 ]]; then
  mkdir -p "$DATA_DIR"
  chown -R appuser:appuser "$DATA_DIR"
  exec gosu appuser "$0" "$@"
fi

mkdir -p "$DATA_DIR" "$DATA_DIR/integrity" "$DATA_DIR/migration_reports"

if [[ "${APP_ENV}" == "production" ]]; then
  # Railway recomienda DATABASE_URL como referencia al servicio PostgreSQL.
  # También admitimos las variables PG* inyectadas por el plugin y codificamos
  # usuario/contraseña correctamente cuando contienen caracteres especiales.
  if ! RESOLVED_DATABASE_URL="$(python backend/tools/resolve_postgresql_env.py)"; then
    echo "[ERROR] No se recibió una conexión PostgreSQL de Railway." >&2
    echo "[ERROR] Agregue DATABASE_URL como referencia al servicio PostgreSQL o referencie PGHOST, PGPORT, PGUSER, PGPASSWORD y PGDATABASE." >&2
    exit 20
  fi
  export DATABASE_URL="$RESOLVED_DATABASE_URL"
  unset RESOLVED_DATABASE_URL
fi

# Pre-deploy ya validó y migró PostgreSQL. El contenedor web prepara solo el
# volumen y arranca Gunicorn; nunca ejecuta DDL durante imports o requests.
export APP_SCHEMA_MIGRATION_MODE=0
export SKIP_RUNTIME_SCHEMA_DDL=1
# La primera descarga puede tardar varios minutos. Se ejecuta en segundo plano
# para que el healthcheck web no dependa de la velocidad del servidor de modelos.
python backend/tools/ensure_vosk_model.py &
python backend/runtime_prepare.py
echo "[STARTUP] Iniciando Gunicorn en 0.0.0.0:${PORT}"

# PostgreSQL elimina la contención del archivo SQLite. Se conserva un worker por
# omisión porque algunos jobs operativos aún son memoria local; puede aumentarse
# GUNICORN_WORKERS después de externalizar esos jobs.
exec gunicorn \
  --chdir backend \
  --bind "0.0.0.0:${PORT}" \
  --workers "${GUNICORN_WORKERS:-1}" \
  --worker-class gthread \
  --threads "${GUNICORN_THREADS:-4}" \
  --timeout "${GUNICORN_TIMEOUT:-300}" \
  --graceful-timeout 60 \
  --keep-alive 5 \
  --access-logfile - \
  --error-logfile - \
  --capture-output \
  wsgi:application
