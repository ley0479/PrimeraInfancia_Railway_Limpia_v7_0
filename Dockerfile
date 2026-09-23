FROM postgres:18-bookworm AS postgres_client

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=production \
    PORT=5000

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       gosu \
       libcairo2 \
       libpango-1.0-0 \
       libpangocairo-1.0-0 \
       libgdk-pixbuf-2.0-0 \
       shared-mime-info \
       fonts-dejavu-core \
       fonts-liberation \
       libreoffice-writer \
       poppler-utils \
       libpq5 \
       tesseract-ocr \
       tesseract-ocr-spa \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 appuser \
    && useradd --system --uid 10001 --gid appuser --home-dir /app --shell /usr/sbin/nologin appuser

# Railway PostgreSQL opera en 18.x. Copiar el cliente oficial de la misma
# versión evita que pg_dump 17 rechace backups del servidor 18.
COPY --from=postgres_client /usr/lib/postgresql/18 /usr/lib/postgresql/18
ENV PATH="/usr/lib/postgresql/18/bin:${PATH}"

COPY backend/requirements-production.txt /tmp/requirements-production.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r /tmp/requirements-production.txt

COPY --chown=appuser:appuser . /app
RUN mkdir -p /data/tenants \
    && chown -R appuser:appuser /data \
    && chmod 0750 /data /data/tenants \
    && chmod 0755 /app/predeploy_hosting.sh /app/start_hosting.sh \
    /app/backend/start_gunicorn.sh /app/backend/init_hosting.py \
    /app/backend/runtime_prepare.py /app/backend/start_idp_worker.sh

EXPOSE 5000
CMD ["./start_hosting.sh"]
