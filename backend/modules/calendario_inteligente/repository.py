"""Repositorio SQLite del Calendario Inteligente de Entregables."""
from __future__ import annotations

import os
import json
import uuid
import re
from modules.dbapi_compat import sqlite3
from modules.runtime_schema import runtime_schema_ddl_disabled
from modules.seguridad.tenant_context import current_tenant_id, tenant_storage_root
from modules.supervision_calidad.services import file_sha256
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from .services import (
    ESTADOS_PERMITIDOS,
    MODULOS_PERMITIDOS,
    calcular_estado_color,
    canonical_modulo,
    clave_unica_entregable,
    detectar_columnas,
    parse_fecha,
    row_to_payload,
    leer_cronograma_flexible,
    construir_preview_cronograma,
    fechas_recurrentes,
    normalizar_texto,
)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


class CalendarioInteligenteRepository:
    def __init__(self, database_path: str, upload_folder: str | None = None):
        self.database_path = database_path
        self.upload_folder = upload_folder

    def connect(self):
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _tenant_id(self) -> int:
        return int(current_tenant_id(default=1) or 1)

    def init_schema(self, *, force: bool = False) -> None:
        if runtime_schema_ddl_disabled() and not force:
            return
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS calendario_entregables (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    titulo TEXT NOT NULL,
                    descripcion TEXT,
                    fecha_inicio TEXT,
                    fecha_limite TEXT NOT NULL,
                    modulo TEXT,
                    tipo_formato TEXT,
                    responsable_id INTEGER,
                    responsable_nombre TEXT,
                    fecha_sugerida TEXT,
                    fecha_estado TEXT DEFAULT 'PENDIENTE_ASIGNACION',
                    importacion_id INTEGER,
                    coordinador TEXT,
                    unidad TEXT,
                    municipio TEXT,
                    estado TEXT DEFAULT 'pendiente',
                    prioridad TEXT DEFAULT 'Media',
                    color TEXT DEFAULT 'azul',
                    requiere_evidencia INTEGER DEFAULT 0,
                    archivo_evidencia TEXT,
                    fecha_entrega TEXT,
                    observaciones TEXT,
                    creado_por TEXT,
                    fecha_creacion TEXT,
                    actualizado_en TEXT,
                    fundacion_id INTEGER DEFAULT 1,
                    usuario_creador_id INTEGER,
                    clave_unica TEXT,
                    origen TEXT DEFAULT 'manual'
                    ,responsable_rol TEXT
                    ,recurrencia TEXT DEFAULT 'ninguna'
                    ,recurrencia_intervalo INTEGER DEFAULT 1
                    ,recurrencia_hasta TEXT
                    ,serie_id TEXT
                    ,instancia_numero INTEGER DEFAULT 1
                )
                """
            )
            # CREATE TABLE IF NOT EXISTS no agrega columnas a una tabla
            # histórica. Migrarlas antes de crear índices multi-tenant evita
            # UndefinedColumn en instalaciones provenientes de versiones
            # anteriores.
            conn.commit()
            entregable_columns = {
                str(row[1])
                for row in conn.execute('PRAGMA table_info("calendario_entregables")').fetchall()
            }
            for column, definition in {
                "fundacion_id": "INTEGER DEFAULT 1",
                "clave_unica": "TEXT",
                "responsable_rol": "TEXT",
                "recurrencia": "TEXT DEFAULT 'ninguna'",
                "recurrencia_intervalo": "INTEGER DEFAULT 1",
                "recurrencia_hasta": "TEXT",
                "serie_id": "TEXT",
                "instancia_numero": "INTEGER DEFAULT 1",
            }.items():
                if column not in entregable_columns:
                    conn.execute(f'ALTER TABLE "calendario_entregables" ADD COLUMN "{column}" {definition}')
                    entregable_columns.add(column)
            conn.commit()
            conn.execute("DROP INDEX IF EXISTS idx_calendario_entregables_clave")
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_calendario_entregables_clave ON calendario_entregables(fundacion_id, clave_unica)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_calendario_fecha ON calendario_entregables(fecha_limite)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_calendario_coordinador ON calendario_entregables(coordinador)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_calendario_unidad ON calendario_entregables(unidad)")
            # En PostgreSQL el adaptador resuelve PRAGMA mediante introspección
            # en otra conexión. Liberar primero los locks DDL evita que una
            # migración aditiva se bloquee a sí misma durante el startup.
            conn.commit()
            for column, definition in {
                "responsable_rol": "TEXT",
                "recurrencia": "TEXT DEFAULT 'ninguna'",
                "recurrencia_intervalo": "INTEGER DEFAULT 1",
                "recurrencia_hasta": "TEXT",
                "serie_id": "TEXT",
                "instancia_numero": "INTEGER DEFAULT 1",
            }.items():
                if column not in entregable_columns:
                    conn.execute(f'ALTER TABLE "calendario_entregables" ADD COLUMN "{column}" {definition}')
            conn.execute("CREATE INDEX IF NOT EXISTS idx_calendario_entregables_serie ON calendario_entregables(fundacion_id, serie_id)")
            conn.commit()

            # ALPHA33: tablas auxiliares para flujo de cronograma revisable antes de guardar.
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS calendario_cronogramas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre_archivo TEXT,
                    archivo_guardado TEXT,
                    periodo TEXT,
                    estado TEXT DEFAULT 'preview',
                    total_detectadas INTEGER DEFAULT 0,
                    total_validas INTEGER DEFAULT 0,
                    total_invalidas INTEGER DEFAULT 0,
                    requiere_revision INTEGER DEFAULT 1,
                    preview_json TEXT,
                    usuario_carga TEXT,
                    fecha_carga TEXT,
                    fecha_confirmacion TEXT,
                    confirmado_por TEXT,
                    fundacion_id INTEGER DEFAULT 1
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS calendario_actividades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cronograma_id INTEGER,
                    entregable_id INTEGER,
                    fecha TEXT,
                    titulo TEXT,
                    descripcion TEXT,
                    responsable TEXT,
                    coordinador TEXT,
                    unidad TEXT,
                    modulo TEXT,
                    estado TEXT DEFAULT 'programado',
                    prioridad TEXT DEFAULT 'Media',
                    observacion TEXT,
                    archivo_origen TEXT,
                    usuario_carga TEXT,
                    fecha_carga TEXT,
                    fecha_entrega TEXT,
                    entregado_por TEXT,
                    soporte_path TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    clave_unica TEXT,
                    fundacion_id INTEGER DEFAULT 1
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ci_actividades_fecha ON calendario_actividades(fecha)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ci_actividades_cronograma ON calendario_actividades(cronograma_id)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS calendario_entregas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actividad_id INTEGER,
                    entregable_id INTEGER,
                    fecha_entrega TEXT,
                    entregado_por TEXT,
                    soporte_path TEXT,
                    observaciones TEXT,
                    created_at TEXT,
                    fundacion_id INTEGER DEFAULT 1
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS calendario_alertas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entregable_id INTEGER,
                    fecha TEXT,
                    nivel TEXT,
                    mensaje TEXT,
                    estado TEXT DEFAULT 'activa',
                    created_at TEXT,
                    fundacion_id INTEGER DEFAULT 1
                )
                """
            )
            conn.commit()
            alert_columns = {
                str(row[1])
                for row in conn.execute('PRAGMA table_info("calendario_alertas")').fetchall()
            }
            for column, definition in {
                "fundacion_id": "INTEGER DEFAULT 1",
                "evento": "TEXT", "usuario_id": "INTEGER", "tipo": "TEXT",
                "fecha_programada": "TEXT", "fecha_enviada": "TEXT",
            }.items():
                if column not in alert_columns:
                    conn.execute(f'ALTER TABLE "calendario_alertas" ADD COLUMN "{column}" {definition}')
                    alert_columns.add(column)
            conn.commit()
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_cal_alerta_idempotente ON calendario_alertas(fundacion_id,entregable_id,usuario_id,tipo,fecha_programada)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS calendario_archivos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cronograma_id INTEGER,
                    nombre_original TEXT,
                    nombre_guardado TEXT,
                    ruta TEXT,
                    tipo TEXT,
                    usuario_carga TEXT,
                    fecha_carga TEXT,
                    fundacion_id INTEGER DEFAULT 1
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS calendario_auditoria (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    accion TEXT,
                    referencia_tipo TEXT,
                    referencia_id INTEGER,
                    detalle TEXT,
                    usuario TEXT,
                    created_at TEXT,
                    fundacion_id INTEGER DEFAULT 1
                )
                """
            )
            # Completar aislamiento en instalaciones creadas por versiones previas.
            for table in (
                "calendario_cronogramas", "calendario_actividades", "calendario_entregas", "calendario_alertas",
                "calendario_archivos", "calendario_auditoria",
            ):
                columns = {str(row[1]) for row in conn.execute(f'PRAGMA table_info("{table}")').fetchall()}
                if "fundacion_id" not in columns:
                    conn.execute(f'ALTER TABLE "{table}" ADD COLUMN fundacion_id INTEGER DEFAULT 1')
                conn.execute(f'CREATE INDEX IF NOT EXISTS "idx_{table}_fundacion" ON "{table}"(fundacion_id)')
            conn.execute("CREATE INDEX IF NOT EXISTS idx_calendario_entregables_fundacion_fecha ON calendario_entregables(fundacion_id, fecha_limite)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_calendario_cronogramas_fundacion ON calendario_cronogramas(fundacion_id)")
            conn.execute(
                """CREATE TABLE IF NOT EXISTS calendario_obligaciones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    componente TEXT NOT NULL,
                    numero TEXT,
                    titulo TEXT NOT NULL,
                    descripcion TEXT,
                    texto_original TEXT,
                    activa INTEGER DEFAULT 1,
                    creado_por TEXT,
                    fecha_creacion TEXT,
                    fecha_actualizacion TEXT,
                    fundacion_id INTEGER DEFAULT 1
                )"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS calendario_requisitos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    obligacion_id INTEGER NOT NULL,
                    tipo TEXT NOT NULL,
                    nombre TEXT NOT NULL,
                    obligatorio INTEGER DEFAULT 1,
                    orden INTEGER DEFAULT 1,
                    fundacion_id INTEGER DEFAULT 1,
                    FOREIGN KEY(obligacion_id) REFERENCES calendario_obligaciones(id)
                )"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS calendario_asignaciones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    obligacion_id INTEGER NOT NULL,
                    periodo TEXT NOT NULL,
                    unidad TEXT,
                    responsable_rol TEXT,
                    responsable_id INTEGER,
                    responsable_nombre TEXT,
                    estado TEXT DEFAULT 'PENDIENTE',
                    justificacion_no_aplica TEXT,
                    no_aplica_por INTEGER,
                    no_aplica_fecha TEXT,
                    creado_por INTEGER,
                    fecha_creacion TEXT,
                    fecha_actualizacion TEXT,
                    fundacion_id INTEGER DEFAULT 1,
                    FOREIGN KEY(obligacion_id) REFERENCES calendario_obligaciones(id)
                )"""
            )
            for table in (
                "calendario_obligaciones", "calendario_requisitos", "calendario_asignaciones",
            ):
                columns = {
                    str(row[1])
                    for row in conn.execute(f'PRAGMA table_info("{table}")').fetchall()
                }
                if "fundacion_id" not in columns:
                    conn.execute(f'ALTER TABLE "{table}" ADD COLUMN fundacion_id INTEGER DEFAULT 1')
            conn.commit()
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cal_obligaciones_fund_comp ON calendario_obligaciones(fundacion_id, componente, activa)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cal_requisitos_obligacion ON calendario_requisitos(fundacion_id, obligacion_id, orden)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cal_asignaciones_periodo ON calendario_asignaciones(fundacion_id, periodo, unidad, responsable_rol, estado)")
            conn.commit()
            for column, definition in {"fecha_sugerida": "TEXT", "fecha_estado": "TEXT DEFAULT 'PENDIENTE_ASIGNACION'", "importacion_id": "INTEGER"}.items():
                try:
                    conn.execute(f'ALTER TABLE "calendario_asignaciones" ADD COLUMN "{column}" {definition}')
                    conn.commit()
                except Exception:
                    conn.rollback()
            conn.execute(
                """CREATE TABLE IF NOT EXISTS calendario_evidencias (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entidad_tipo TEXT NOT NULL,
                    entidad_id INTEGER NOT NULL,
                    requisito_id INTEGER,
                    nombre_original TEXT NOT NULL,
                    nombre_guardado TEXT NOT NULL,
                    ruta_archivo TEXT NOT NULL,
                    mime_type TEXT,
                    tamano_bytes INTEGER NOT NULL,
                    sha256 TEXT NOT NULL,
                    version INTEGER DEFAULT 1,
                    estado TEXT DEFAULT 'CARGADA',
                    descripcion TEXT,
                    cargada_por INTEGER,
                    cargada_por_nombre TEXT,
                    fecha_carga TEXT,
                    revisada_por INTEGER,
                    fecha_revision TEXT,
                    observacion_revision TEXT,
                    fundacion_id INTEGER DEFAULT 1
                )"""
            )
            evidence_columns = {
                str(row[1])
                for row in conn.execute('PRAGMA table_info("calendario_evidencias")').fetchall()
            }
            if "fundacion_id" not in evidence_columns:
                conn.execute(
                    'ALTER TABLE "calendario_evidencias" ADD COLUMN fundacion_id INTEGER DEFAULT 1'
                )
                conn.commit()
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cal_evidencias_entidad ON calendario_evidencias(fundacion_id, entidad_tipo, entidad_id, requisito_id, fecha_carga)")
            conn.commit()

    def add_evidencia(self, entidad_tipo: str, entidad_id: int, requisito_id: int | None, file, descripcion: str, user: dict[str, Any]) -> dict[str, Any]:
        entity = str(entidad_tipo or "").upper()
        if entity not in {"ENTREGABLE", "CHECKLIST"}:
            raise ValueError("Tipo de entidad de evidencia no permitido.")
        if entity == "ENTREGABLE" and not self.get_entregable(entidad_id):
            raise LookupError("Entregable no encontrado.")
        if entity == "CHECKLIST" and not self.get_asignacion(entidad_id):
            raise LookupError("Asignación no encontrada.")
        original = os.path.basename(str(getattr(file, "filename", "") or "evidencia"))
        extension = Path(original).suffix.lower()
        allowed = {".pdf", ".doc", ".docx", ".xlsx", ".xls", ".csv", ".txt", ".png", ".jpg", ".jpeg", ".webp", ".zip"}
        if extension not in allowed:
            raise ValueError("Tipo de archivo no permitido.")
        fid = self._tenant_id()
        root = tenant_storage_root(self.upload_folder or "data/uploads", fid) / "calendario_inteligente" / "evidencias" / entity.lower() / str(entidad_id)
        root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_base = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in Path(original).name)
        safe_name = f"{stamp}_{safe_base}"
        path = root / safe_name
        file.save(path)
        size = path.stat().st_size
        if size <= 0 or size > 50 * 1024 * 1024:
            path.unlink(missing_ok=True)
            raise ValueError("La evidencia está vacía o supera 50 MB.")
        mime = str(getattr(file, "mimetype", None) or "application/octet-stream")
        if mime.startswith("text/html") or mime in {"application/x-msdownload", "application/x-sh"}:
            path.unlink(missing_ok=True)
            raise ValueError("Tipo MIME no permitido.")
        sha = file_sha256(path)
        now = now_iso()
        with self.connect() as conn:
            row = conn.execute("SELECT COALESCE(MAX(version),0)+1 n FROM calendario_evidencias WHERE fundacion_id=? AND entidad_tipo=? AND entidad_id=? AND COALESCE(requisito_id,0)=? AND nombre_original=?", (fid, entity, entidad_id, int(requisito_id or 0), original)).fetchone()
            cur = conn.execute(
                """INSERT INTO calendario_evidencias(entidad_tipo,entidad_id,requisito_id,nombre_original,nombre_guardado,ruta_archivo,mime_type,tamano_bytes,sha256,version,estado,descripcion,cargada_por,cargada_por_nombre,fecha_carga,fundacion_id)
                VALUES(?,?,?,?,?,?,?,?,?,?,'CARGADA',?,?,?,?,?)""",
                (entity, entidad_id, requisito_id, original, safe_name, str(path), mime, size, sha, int(row["n"] or 1), descripcion, user.get("id"), user.get("nombre_completo") or user.get("username"), now, fid),
            )
            evidence_id = int(cur.lastrowid)
            if entity == "CHECKLIST":
                conn.execute("UPDATE calendario_asignaciones SET estado=CASE WHEN estado='PENDIENTE' THEN 'EN_PROGRESO' ELSE estado END,fecha_actualizacion=? WHERE fundacion_id=? AND id=?", (now, fid, entidad_id))
            conn.commit()
        return self.get_evidencia(evidence_id) or {}

    def get_evidencia(self, evidence_id: int) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM calendario_evidencias WHERE fundacion_id=? AND id=?", (self._tenant_id(), evidence_id)).fetchone()
        return dict(row) if row else None

    def list_evidencias(self, entidad_tipo: str, entidad_id: int) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute("SELECT id,entidad_tipo,entidad_id,requisito_id,nombre_original,mime_type,tamano_bytes,sha256,version,estado,descripcion,cargada_por_nombre,fecha_carga,observacion_revision FROM calendario_evidencias WHERE fundacion_id=? AND entidad_tipo=? AND entidad_id=? ORDER BY fecha_carga DESC,id DESC", (self._tenant_id(), str(entidad_tipo).upper(), entidad_id)).fetchall()
        return [dict(row) for row in rows]

    def evidencia_path(self, evidence_id: int) -> tuple[Path, str, str] | None:
        row = self.get_evidencia(evidence_id)
        if not row:
            return None
        try:
            path = Path(row["ruta_archivo"]).resolve(strict=True)
            root = tenant_storage_root(self.upload_folder or "data/uploads", self._tenant_id()).resolve()
            path.relative_to(root)
        except (OSError, ValueError):
            return None
        if file_sha256(path) != row["sha256"]:
            return None
        return path, row["nombre_original"], row.get("mime_type") or "application/octet-stream"

    def revisar_evidencias(self, entidad_tipo: str, entidad_id: int, decision: str, observacion: str, user: dict[str, Any]) -> dict[str, Any]:
        state = str(decision or "").upper()
        if state not in {"APROBADA", "DEVUELTA"}:
            raise ValueError("Decisión de revisión no permitida.")
        if state == "DEVUELTA" and not str(observacion or "").strip():
            raise ValueError("La devolución requiere una observación.")
        entity = str(entidad_tipo or "").upper()
        now = now_iso()
        with self.connect() as conn:
            cur = conn.execute("UPDATE calendario_evidencias SET estado=?,revisada_por=?,fecha_revision=?,observacion_revision=? WHERE fundacion_id=? AND entidad_tipo=? AND entidad_id=? AND estado='CARGADA'", (state, user.get("id"), now, observacion or "", self._tenant_id(), entity, entidad_id))
            if entity == "CHECKLIST":
                conn.execute("UPDATE calendario_asignaciones SET estado=?,fecha_actualizacion=? WHERE fundacion_id=? AND id=?", ("APROBADO" if state == "APROBADA" else "DEVUELTO", now, self._tenant_id(), entidad_id))
            elif entity == "ENTREGABLE":
                conn.execute("UPDATE calendario_entregables SET estado=?,actualizado_en=? WHERE fundacion_id=? AND id=?", ("aprobado" if state == "APROBADA" else "rechazado", now, self._tenant_id(), entidad_id))
            conn.commit()
        return {"actualizadas": int(cur.rowcount or 0), "estado": state}

    def enviar_evidencias_revision(self, entidad_tipo: str, entidad_id: int) -> dict[str, Any]:
        entity = str(entidad_tipo or "").upper()
        if entity not in {"ENTREGABLE", "CHECKLIST"}:
            raise ValueError("Tipo de entidad de evidencia no permitido.")
        evidencias = self.list_evidencias(entity, entidad_id)
        if not any(item.get("estado") == "CARGADA" for item in evidencias):
            raise ValueError("Carga al menos una evidencia nueva antes de enviarla a revisión.")
        now = now_iso()
        fid = self._tenant_id()
        with self.connect() as conn:
            if entity == "CHECKLIST":
                cur = conn.execute("UPDATE calendario_asignaciones SET estado='ENTREGADO',fecha_actualizacion=? WHERE fundacion_id=? AND id=?", (now, fid, entidad_id))
            else:
                cur = conn.execute("UPDATE calendario_entregables SET estado='entregado',fecha_entrega=?,actualizado_en=? WHERE fundacion_id=? AND id=?", (now[:10], now, fid, entidad_id))
            conn.commit()
        if not cur.rowcount:
            raise LookupError("Actividad no encontrada.")
        return {"entidad_tipo": entity, "entidad_id": entidad_id, "estado": "ENTREGADO"}

    def create_obligacion(self, data: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        componente = str(data.get("componente") or "").strip()
        titulo = str(data.get("titulo") or data.get("actividad") or "").strip()
        periodo = str(data.get("periodo") or "").strip()[:7]
        if not componente or not titulo:
            raise ValueError("Componente y actividad son obligatorios.")
        if len(periodo) != 7 or periodo[4:5] != "-":
            raise ValueError("periodo debe usar el formato AAAA-MM.")
        requisitos = data.get("requisitos") or []
        if not isinstance(requisitos, list) or not requisitos:
            raise ValueError("La obligación debe tener al menos un requisito.")
        now = now_iso()
        fid = self._tenant_id()
        with self.connect() as conn:
            cur = conn.execute(
                """INSERT INTO calendario_obligaciones
                (componente,numero,titulo,descripcion,texto_original,activa,creado_por,fecha_creacion,fecha_actualizacion,fundacion_id)
                VALUES (?,?,?,?,?,1,?,?,?,?)""",
                (componente, data.get("numero") or "", titulo, data.get("descripcion") or "", data.get("texto_original") or "", user.get("username") or "sistema", now, now, fid),
            )
            obligation_id = int(cur.lastrowid)
            for index, requirement in enumerate(requisitos, start=1):
                item = requirement if isinstance(requirement, dict) else {"nombre": str(requirement)}
                name = str(item.get("nombre") or item.get("titulo") or "").strip()
                if not name:
                    continue
                conn.execute(
                    "INSERT INTO calendario_requisitos(obligacion_id,tipo,nombre,obligatorio,orden,fundacion_id) VALUES(?,?,?,?,?,?)",
                    (obligation_id, str(item.get("tipo") or "EVIDENCIA").upper(), name, 0 if item.get("obligatorio") is False else 1, index, fid),
                )
            cur = conn.execute(
                """INSERT INTO calendario_asignaciones
                (obligacion_id,periodo,unidad,responsable_rol,responsable_id,responsable_nombre,fecha_sugerida,fecha_estado,importacion_id,estado,creado_por,fecha_creacion,fecha_actualizacion,fundacion_id)
                VALUES(?,?,?,?,?,?,?,?,?,'PENDIENTE',?,?,?,?)""",
                (obligation_id, periodo, data.get("unidad") or "", str(data.get("responsable_rol") or "").upper(), data.get("responsable_id") or None, data.get("responsable_nombre") or "", parse_fecha(data.get("fecha_sugerida") or data.get("fecha")), "ASIGNADA" if parse_fecha(data.get("fecha_sugerida") or data.get("fecha")) else "PENDIENTE_ASIGNACION", data.get("importacion_id") or None, user.get("id"), now, now, fid),
            )
            assignment_id = int(cur.lastrowid)
            conn.commit()
        return self.get_asignacion(assignment_id)

    def confirmar_importacion_checklist(self, importacion_id: int, propuestas: list[dict[str, Any]], periodo: str, user: dict[str, Any]) -> dict[str, Any]:
        if not propuestas:
            raise ValueError("No hay propuestas seleccionadas para incorporar.")
        created, ignored, errors = [], 0, []
        for index, item in enumerate(propuestas, start=1):
            if item.get("ignorar") or item.get("descartar"):
                ignored += 1
                continue
            entregables = item.get("entregables") or item.get("requisitos") or ""
            if isinstance(entregables, str):
                requirements = [{"nombre": value.strip()} for value in re.split(r"[\n;,]+", entregables) if value.strip()]
            else:
                requirements = entregables
            if not requirements:
                requirements = [{"nombre": "Evidencia por definir", "obligatorio": False}]
            payload = {
                "componente": item.get("componente") or "SIN COMPONENTE",
                "numero": item.get("numero") or "",
                "titulo": item.get("titulo") or item.get("actividad"),
                "texto_original": item.get("texto_original") or item.get("titulo") or "",
                "periodo": periodo,
                "unidad": item.get("unidad") or "",
                "responsable_rol": item.get("responsable_rol") or "",
                "responsable_nombre": item.get("responsable_nombre") or "",
                "fecha_sugerida": item.get("fecha_sugerida") or item.get("fecha"),
                "importacion_id": importacion_id,
                "requisitos": requirements,
            }
            try:
                if not payload["titulo"]:
                    raise ValueError("Actividad vacía.")
                with self.connect() as conn:
                    duplicate = conn.execute("""SELECT a.id FROM calendario_asignaciones a JOIN calendario_obligaciones o ON o.id=a.obligacion_id AND o.fundacion_id=a.fundacion_id WHERE a.fundacion_id=? AND a.periodo=? AND LOWER(TRIM(o.componente))=LOWER(TRIM(?)) AND LOWER(TRIM(o.titulo))=LOWER(TRIM(?)) AND LOWER(TRIM(COALESCE(a.unidad,'')))=LOWER(TRIM(?)) LIMIT 1""", (self._tenant_id(), periodo, payload["componente"], payload["titulo"], payload["unidad"])).fetchone()
                if duplicate:
                    ignored += 1
                    continue
                created.append(self.create_obligacion(payload, user))
            except Exception as exc:
                errors.append({"fila": index, "error": str(exc)})
        with self.connect() as conn:
            conn.execute("UPDATE calendario_cronogramas SET estado='APROBADO',fecha_confirmacion=?,confirmado_por=? WHERE fundacion_id=? AND id=?", (now_iso(), user.get("username") or "sistema", self._tenant_id(), importacion_id))
            conn.commit()
        return {"creadas": len(created), "duplicadas_o_ignoradas": ignored, "errores": errors, "asignaciones": created}

    def get_asignacion(self, assignment_id: int) -> dict[str, Any] | None:
        fid = self._tenant_id()
        with self.connect() as conn:
            assignment = conn.execute("SELECT * FROM calendario_asignaciones WHERE fundacion_id=? AND id=?", (fid, assignment_id)).fetchone()
            if not assignment:
                return None
            obligation = conn.execute("SELECT * FROM calendario_obligaciones WHERE fundacion_id=? AND id=?", (fid, assignment["obligacion_id"])).fetchone()
            requirements = conn.execute("SELECT * FROM calendario_requisitos WHERE fundacion_id=? AND obligacion_id=? ORDER BY orden,id", (fid, assignment["obligacion_id"])).fetchall()
        payload = dict(assignment)
        payload["obligacion"] = dict(obligation) if obligation else None
        payload["requisitos"] = [dict(row) for row in requirements]
        return payload

    def list_checklist(self, periodo: str, user: dict[str, Any] | None = None) -> dict[str, Any]:
        fid = self._tenant_id()
        params: list[Any] = [fid, str(periodo or "")[:7]]
        where = "fundacion_id=? AND periodo=?"
        role = str((user or {}).get("rol") or "").upper()
        if role not in {"SUPERADMIN", "GERENTE", "COORDINADOR", "AUXILIAR_ADMINISTRATIVO"}:
            where += " AND (responsable_id=? OR LOWER(COALESCE(responsable_nombre,'')) IN (LOWER(?),LOWER(?)))"
            params.extend([(user or {}).get("id") or 0, (user or {}).get("username") or "", (user or {}).get("nombre_completo") or ""])
        with self.connect() as conn:
            rows = conn.execute(f"SELECT id FROM calendario_asignaciones WHERE {where} ORDER BY unidad,responsable_rol,id", params).fetchall()
        items = [self.get_asignacion(int(row["id"])) for row in rows]
        items = [item for item in items if item]
        exigibles = [item for item in items if item["estado"] != "NO_APLICA"]
        aprobadas = [item for item in exigibles if item["estado"] in {"APROBADO", "CUMPLIDO"}]
        return {
            "periodo": str(periodo or "")[:7],
            "asignaciones": items,
            "resumen": {
                "total": len(items), "no_aplica": len(items) - len(exigibles),
                "exigibles": len(exigibles), "aprobadas": len(aprobadas),
                "cumplimiento": round(len(aprobadas) * 100 / len(exigibles), 1) if exigibles else 0,
            },
        }

    def tablero_cumplimiento(self, periodo: str) -> dict[str, Any]:
        fid = self._tenant_id()
        with self.connect() as conn:
            rows = conn.execute("""SELECT a.*,o.componente,o.titulo FROM calendario_asignaciones a JOIN calendario_obligaciones o ON o.id=a.obligacion_id AND o.fundacion_id=a.fundacion_id WHERE a.fundacion_id=? AND a.periodo=?""", (fid, str(periodo or "")[:7])).fetchall()
        data = [dict(row) for row in rows]
        def aggregate(field: str) -> list[dict[str, Any]]:
            groups: dict[str, dict[str, int]] = {}
            for row in data:
                key = str(row.get(field) or "Sin asignar").strip() or "Sin asignar"
                item = groups.setdefault(key, {"total": 0, "no_aplica": 0, "exigibles": 0, "aprobadas": 0, "vencidas": 0})
                item["total"] += 1
                state = str(row.get("estado") or "PENDIENTE").upper()
                if state == "NO_APLICA": item["no_aplica"] += 1
                else:
                    item["exigibles"] += 1
                    if state in {"APROBADO", "CUMPLIDO"}: item["aprobadas"] += 1
                    if state == "VENCIDO": item["vencidas"] += 1
            return [{"nombre": key, **value, "cumplimiento": round(value["aprobadas"] * 100 / value["exigibles"], 1) if value["exigibles"] else 0} for key, value in sorted(groups.items())]
        exigibles = [row for row in data if str(row.get("estado") or "").upper() != "NO_APLICA"]
        approved = [row for row in exigibles if str(row.get("estado") or "").upper() in {"APROBADO", "CUMPLIDO"}]
        return {"periodo": str(periodo or "")[:7], "fundacion_id": fid, "formula": "obligaciones_aprobadas / obligaciones_exigibles * 100", "resumen": {"total": len(data), "exigibles": len(exigibles), "aprobadas": len(approved), "no_aplica": len(data)-len(exigibles), "cumplimiento": round(len(approved)*100/len(exigibles),1) if exigibles else 0}, "por_uds": aggregate("unidad"), "por_responsable": aggregate("responsable_nombre"), "por_rol": aggregate("responsable_rol"), "por_componente": aggregate("componente")}

    def update_asignacion_estado(self, assignment_id: int, estado: str, motivo: str, user: dict[str, Any]) -> dict[str, Any] | None:
        allowed = {"PENDIENTE", "EN_PROGRESO", "ENTREGADO", "APROBADO", "DEVUELTO", "NO_APLICA"}
        state = str(estado or "").upper()
        if state not in allowed:
            raise ValueError("Estado de checklist no permitido.")
        reason = str(motivo or "").strip()
        if state == "NO_APLICA" and not reason:
            raise ValueError("NO APLICA requiere una justificación.")
        now = now_iso()
        with self.connect() as conn:
            cur = conn.execute(
                """UPDATE calendario_asignaciones SET estado=?,justificacion_no_aplica=?,no_aplica_por=?,no_aplica_fecha=?,fecha_actualizacion=?
                WHERE fundacion_id=? AND id=?""",
                (state, reason if state == "NO_APLICA" else None, user.get("id") if state == "NO_APLICA" else None, now if state == "NO_APLICA" else None, now, self._tenant_id(), assignment_id),
            )
            conn.commit()
        return self.get_asignacion(assignment_id) if cur.rowcount else None

    def _row(self, row: sqlite3.Row | None) -> dict[str, Any] | None:
        if not row:
            return None
        data = dict(row)
        estado, color, dias = calcular_estado_color(data.get("fecha_limite"), data.get("estado"))
        # No sobrescribe entregado/aprobado/no_aplica/cerrado. Sí actualiza estado visual en salida.
        data["estado_calculado"] = estado
        data["color_calculado"] = color
        data["dias_restantes"] = dias
        data["color"] = data.get("color") or color
        if data.get("estado") not in {"entregado", "aprobado", "no_aplica", "cerrado", "rechazado"}:
            data["estado"] = estado
            data["color"] = color
        return data

    def _rows(self, rows) -> list[dict[str, Any]]:
        return [self._row(r) for r in rows]

    def _build_where(self, filters: dict[str, Any]) -> tuple[str, list[Any]]:
        where = ["fundacion_id=?"]
        params: list[Any] = [self._tenant_id()]
        periodo = filters.get("periodo")
        anio = filters.get("anio")
        if periodo:
            where.append("substr(fecha_limite, 1, 7) = ?")
            params.append(str(periodo)[:7])
        elif anio:
            where.append("substr(fecha_limite, 1, 4) = ?")
            params.append(str(anio)[:4])
        for field in ["coordinador", "unidad", "modulo", "estado", "responsable_nombre", "municipio"]:
            value = filters.get(field)
            if value:
                if field in {"coordinador", "unidad", "modulo", "responsable_nombre", "municipio"}:
                    where.append(f"LOWER(COALESCE({field}, '')) LIKE LOWER(?)")
                    params.append(f"%{value}%")
                else:
                    where.append(f"{field} = ?")
                    params.append(value)
        fecha = filters.get("fecha")
        if fecha:
            where.append("fecha_limite = ?")
            params.append(parse_fecha(fecha) or fecha)
        return " AND ".join(where), params

    def list_entregables(self, filters: dict[str, Any] | None = None, limit: int = 500) -> list[dict[str, Any]]:
        filters = filters or {}
        where, params = self._build_where(filters)
        with self.connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM calendario_entregables WHERE {where} ORDER BY fecha_limite ASC, prioridad DESC, modulo ASC, unidad ASC LIMIT ?",
                params + [limit],
            ).fetchall()
        return self._rows(rows)

    def get_entregable(self, entregable_id: int) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM calendario_entregables WHERE fundacion_id=? AND id=?", (self._tenant_id(), entregable_id)).fetchone()
        return self._row(row)

    def list_mis_pendientes(self, user: dict[str, Any], limit: int = 100) -> list[dict[str, Any]]:
        """Lista obligaciones activas asignadas o creadas por el usuario actual.

        La fundación siempre proviene del contexto tenant del backend. Los
        nombres se usan solo como compatibilidad para registros históricos;
        cuando existen IDs, estos son la referencia principal.
        """
        user_id = int(user.get("id") or 0)
        names = {
            str(user.get("username") or "").strip().casefold(),
            str(user.get("email") or "").strip().casefold(),
            str(user.get("nombre_completo") or user.get("nombre") or "").strip().casefold(),
        }
        names.discard("")
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM calendario_entregables
                WHERE fundacion_id=?
                  AND LOWER(COALESCE(estado, 'pendiente')) NOT IN ('entregado','aprobado','cancelado','no aplica')
                  AND (
                    (? > 0 AND (responsable_id=? OR usuario_creador_id=?))
                    OR LOWER(TRIM(COALESCE(responsable_nombre,''))) IN ({})
                    OR LOWER(TRIM(COALESCE(creado_por,''))) IN ({})
                  )
                ORDER BY fecha_limite ASC, prioridad DESC, id ASC
                LIMIT ?
                """.format(
                    ",".join("?" for _ in names) or "NULL",
                    ",".join("?" for _ in names) or "NULL",
                ),
                [self._tenant_id(), user_id, user_id, user_id, *sorted(names), *sorted(names), max(1, min(int(limit), 500))],
            ).fetchall()
        return self._rows(rows)

    def create_entregable(self, data: dict[str, Any], origen: str = "manual") -> dict[str, Any]:
        payload = self._prepare_payload(data, origen=origen)
        fields = [
            "titulo", "descripcion", "fecha_inicio", "fecha_limite", "modulo", "tipo_formato", "responsable_id",
            "responsable_nombre", "coordinador", "unidad", "municipio", "estado", "prioridad", "color",
            "requiere_evidencia", "archivo_evidencia", "fecha_entrega", "observaciones", "creado_por", "fecha_creacion",
            "actualizado_en", "fundacion_id", "usuario_creador_id", "clave_unica", "origen", "responsable_rol",
            "recurrencia", "recurrencia_intervalo", "recurrencia_hasta", "serie_id", "instancia_numero",
        ]
        values = [payload.get(f) for f in fields]
        placeholders = ",".join("?" for _ in fields)
        with self.connect() as conn:
            try:
                cur = conn.execute(f"INSERT INTO calendario_entregables ({','.join(fields)}) VALUES ({placeholders})", values)
                conn.commit()
                new_id = cur.lastrowid
            except sqlite3.IntegrityError:
                row = conn.execute("SELECT id FROM calendario_entregables WHERE fundacion_id=? AND clave_unica=?", (self._tenant_id(), payload["clave_unica"])).fetchone()
                new_id = int(row["id"])
        return self.get_entregable(new_id)

    def create_recurrentes(self, data: dict[str, Any], origen: str = "manual") -> list[dict[str, Any]]:
        fechas = fechas_recurrentes(
            data.get("fecha_limite"), data.get("recurrencia"),
            data.get("recurrencia_hasta"), data.get("recurrencia_intervalo", 1),
        )
        serie_id = str(data.get("serie_id") or uuid.uuid4().hex) if len(fechas) > 1 else None
        created = []
        for index, fecha in enumerate(fechas, start=1):
            item = {
                **data,
                "fecha_limite": fecha,
                "fecha_inicio": fecha,
                "serie_id": serie_id,
                "instancia_numero": index,
            }
            created.append(self.create_entregable(item, origen=origen))
        return created

    def update_entregable(self, entregable_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        current = self.get_entregable(entregable_id)
        if not current:
            return None
        payload = {**current, **(data or {})}
        payload = self._prepare_payload(payload, origen=current.get("origen") or "manual", keep_created=True)
        fields = [
            "titulo", "descripcion", "fecha_inicio", "fecha_limite", "modulo", "tipo_formato", "responsable_id",
            "responsable_nombre", "coordinador", "unidad", "municipio", "estado", "prioridad", "color",
            "requiere_evidencia", "archivo_evidencia", "fecha_entrega", "observaciones", "actualizado_en", "clave_unica",
            "responsable_rol", "recurrencia", "recurrencia_intervalo", "recurrencia_hasta", "serie_id", "instancia_numero",
        ]
        values = [payload.get(f) for f in fields] + [entregable_id]
        with self.connect() as conn:
            conn.execute(f"UPDATE calendario_entregables SET {','.join(f + '=?' for f in fields)} WHERE fundacion_id=? AND id=?", values[:-1] + [self._tenant_id(), entregable_id])
            conn.commit()
        return self.get_entregable(entregable_id)

    def delete_entregable(self, entregable_id: int) -> bool:
        with self.connect() as conn:
            cur = conn.execute("DELETE FROM calendario_entregables WHERE fundacion_id=? AND id=?", (self._tenant_id(), entregable_id))
            conn.commit()
            return cur.rowcount > 0

    def _prepare_payload(self, data: dict[str, Any], origen: str = "manual", keep_created: bool = False) -> dict[str, Any]:
        now = now_iso()
        fecha_limite = parse_fecha(data.get("fecha_limite") or data.get("fecha") or data.get("fecha_entrega"))
        if not fecha_limite:
            raise ValueError("fecha_limite es obligatoria y debe ser válida.")
        fecha_inicio = parse_fecha(data.get("fecha_inicio")) or fecha_limite
        estado_input = data.get("estado") or "pendiente"
        estado, color, _dias = calcular_estado_color(fecha_limite, estado_input)
        if estado_input in {"entregado", "aprobado", "rechazado", "no_aplica", "cerrado"}:
            estado = estado_input
            color = calcular_estado_color(fecha_limite, estado_input)[1]
        modulo = canonical_modulo(data.get("modulo"), data.get("tipo_formato"))
        payload = dict(data)
        payload.update({
            "titulo": str(data.get("titulo") or data.get("actividad") or "Entregable operativo").strip(),
            "descripcion": data.get("descripcion") or data.get("observaciones") or "",
            "fecha_inicio": fecha_inicio,
            "fecha_limite": fecha_limite,
            "modulo": modulo,
            "tipo_formato": data.get("tipo_formato") or data.get("formato") or modulo,
            "responsable_id": data.get("responsable_id") or None,
            "responsable_nombre": data.get("responsable_nombre") or data.get("responsable") or "",
            "responsable_rol": data.get("responsable_rol") or data.get("rol_responsable") or "",
            "coordinador": data.get("coordinador") or "",
            "unidad": data.get("unidad") or data.get("uds") or "",
            "municipio": data.get("municipio") or "",
            "estado": estado,
            "prioridad": data.get("prioridad") or "Media",
            "color": color,
            "requiere_evidencia": 1 if str(data.get("requiere_evidencia", "0")).lower() in {"1", "true", "si", "sí", "yes"} else 0,
            "archivo_evidencia": data.get("archivo_evidencia") or None,
            "fecha_entrega": parse_fecha(data.get("fecha_entrega")) or None,
            "observaciones": data.get("observaciones") or "",
            "creado_por": data.get("creado_por") or "sistema",
            "fecha_creacion": data.get("fecha_creacion") if keep_created else now,
            "actualizado_en": now,
            "fundacion_id": self._tenant_id(),
            "usuario_creador_id": data.get("usuario_creador_id") or None,
            "origen": origen,
            "recurrencia": normalizar_texto(data.get("recurrencia") or "ninguna").replace(" ", "_"),
            "recurrencia_intervalo": int(data.get("recurrencia_intervalo") or 1),
            "recurrencia_hasta": parse_fecha(data.get("recurrencia_hasta")) or None,
            "serie_id": data.get("serie_id") or None,
            "instancia_numero": int(data.get("instancia_numero") or 1),
        })
        payload["clave_unica"] = data.get("clave_unica") or clave_unica_entregable(payload)
        return payload

    def import_cronograma(self, path: str, filename: str = "") -> dict[str, Any]:
        df = leer_cronograma_flexible(path, filename)
        mapping = detectar_columnas(df.columns)
        if "fecha_limite" not in mapping or "titulo" not in mapping:
            return {
                "total_filas": int(len(df)),
                "creados": 0,
                "duplicados": 0,
                "errores": [{"fila": 0, "error": "El archivo debe contener columnas de fecha y actividad/entregable."}],
                "columnas_detectadas": mapping,
            }
        creados = 0
        duplicados = 0
        errores = []
        for idx, row in df.iterrows():
            try:
                payload = row_to_payload(row, mapping)
                if not payload.get("fecha_limite"):
                    errores.append({"fila": int(idx) + 2, "error": "Fecha inválida o vacía."})
                    continue
                before = self.find_by_clave(payload["clave_unica"])
                self.create_entregable(payload, origen="excel")
                if before:
                    duplicados += 1
                else:
                    creados += 1
            except Exception as exc:
                errores.append({"fila": int(idx) + 2, "error": str(exc)})
        return {
            "total_filas": int(len(df)),
            "creados": creados,
            "duplicados": duplicados,
            "errores": errores[:50],
            "columnas_detectadas": mapping,
        }

    def registrar_preview_cronograma(self, path: str, filename: str = "", usuario: str = "sistema") -> dict[str, Any]:
        """Procesa un cronograma y guarda una vista previa editable sin crear entregables."""
        preview = construir_preview_cronograma(path, filename)
        actividades = preview.get("actividades") or []
        fechas = [a.get("fecha_limite") for a in actividades if a.get("fecha_limite")]
        periodo = (min(fechas)[:7] if fechas else date.today().isoformat()[:7])
        now = now_iso()
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO calendario_cronogramas (
                    nombre_archivo, archivo_guardado, periodo, estado, total_detectadas,
                    total_validas, total_invalidas, requiere_revision, preview_json,
                    usuario_carga, fecha_carga, fundacion_id
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    filename,
                    os.path.basename(path),
                    periodo,
                    "LISTO_PARA_REVISION",
                    len(actividades),
                    int(preview.get("validas") or 0),
                    int(preview.get("invalidas") or 0),
                    1 if preview.get("requiere_revision") else 0,
                    json.dumps(preview, ensure_ascii=False),
                    usuario,
                    now,
                    self._tenant_id(),
                ),
            )
            cronograma_id = int(cur.lastrowid)
            conn.execute(
                """
                INSERT INTO calendario_archivos (cronograma_id, nombre_original, nombre_guardado, ruta, tipo, usuario_carga, fecha_carga, fundacion_id)
                VALUES (?,?,?,?,?,?,?,?)
                """,
                (cronograma_id, filename, os.path.basename(path), path, "cronograma", usuario, now, self._tenant_id()),
            )
            conn.execute(
                "INSERT INTO calendario_auditoria (accion, referencia_tipo, referencia_id, detalle, usuario, created_at, fundacion_id) VALUES (?,?,?,?,?,?,?)",
                ("preview_cronograma", "cronograma", cronograma_id, f"Detectadas {len(actividades)} actividades", usuario, now, self._tenant_id()),
            )
            conn.commit()
        preview["cronograma_id"] = cronograma_id
        preview["periodo"] = periodo
        preview["archivo"] = os.path.basename(path)
        return preview

    def registrar_preview_actividades(self, actividades_fuente: list[dict[str, Any]], filename: str = "", usuario: str = "sistema", referencia: str = "") -> dict[str, Any]:
        """Crea una vista previa desde actividades ya revisadas por otro motor.

        No crea entregables: conserva el mismo paso de confirmación humana del
        cargador de cronogramas y evita volver a ejecutar OCR sobre el original.
        """
        actividades=[]; errores=[]
        for index,item in enumerate(actividades_fuente or [],start=1):
            fecha=str(item.get("fecha_limite") or item.get("fecha") or "")[:10]
            titulo=str(item.get("actividad") or item.get("titulo") or "").strip()
            row_errors=[]
            if not fecha: row_errors.append("Fecha requerida")
            if not titulo: row_errors.append("Actividad requerida")
            if row_errors: errores.append({"fila":index,"error":"; ".join(row_errors)})
            actividades.append({
                "id_temp":index,"fecha":fecha,"fecha_limite":fecha,"titulo":titulo,
                "descripcion":str(item.get("descripcion") or item.get("entregable") or ""),
                "entregables":str(item.get("entregables") or item.get("entregable") or ""),
                "responsable_nombre":str(item.get("responsable_nombre") or item.get("responsable") or ""),
                "coordinador":str(item.get("coordinador") or ""),"unidad":str(item.get("unidad") or ""),
                "modulo":str(item.get("modulo") or item.get("componente") or "General"),
                "tipo_formato":str(item.get("tipo_formato") or "General"),"estado":"programado",
                "prioridad":str(item.get("prioridad") or "Media"),"observaciones":str(item.get("observaciones") or ""),
                "ok":not row_errors,"errores":row_errors,"advertencias":["Origen: Motor Universal; confirme la lectura antes de guardar."],
                "confianza":int(float(item.get("confianza") or 0.76)*100) if float(item.get("confianza") or 0.76)<=1 else int(item.get("confianza")),
                "origen":filename or referencia or "Motor Universal",
            })
        validas=sum(1 for item in actividades if item["ok"])
        preview={"total_filas":len(actividades),"actividades":actividades,"validas":validas,"invalidas":len(actividades)-validas,"duplicados_en_archivo":0,"errores":errores,"advertencias":["Revise las actividades extraídas por el Motor Universal."],"requiere_revision":True,"referencia_origen":referencia}
        fechas=[item["fecha_limite"] for item in actividades if item["fecha_limite"]]; periodo=min(fechas)[:7] if fechas else date.today().isoformat()[:7]; now=now_iso()
        with self.connect() as conn:
            cur=conn.execute("INSERT INTO calendario_cronogramas (nombre_archivo,archivo_guardado,periodo,estado,total_detectadas,total_validas,total_invalidas,requiere_revision,preview_json,usuario_carga,fecha_carga,fundacion_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",(filename,referencia,periodo,"LISTO_PARA_REVISION",len(actividades),validas,len(actividades)-validas,1,json.dumps(preview,ensure_ascii=False),usuario,now,self._tenant_id()))
            cronograma_id=int(cur.lastrowid)
            conn.execute("INSERT INTO calendario_auditoria (accion,referencia_tipo,referencia_id,detalle,usuario,created_at,fundacion_id) VALUES (?,?,?,?,?,?,?)",("preview_desde_idp","cronograma",cronograma_id,f"Documento {referencia}; {len(actividades)} actividades",usuario,now,self._tenant_id()))
            conn.commit()
        preview.update({"cronograma_id":cronograma_id,"periodo":periodo,"archivo":filename})
        return preview

    def confirmar_cronograma(self, cronograma_id: int, actividades: list[dict[str, Any]], usuario: str = "sistema") -> dict[str, Any]:
        """Guarda actividades revisadas en el calendario operativo."""
        creados = 0
        duplicados = 0
        errores: list[dict[str, Any]] = []
        now = now_iso()
        if not actividades:
            with self.connect() as conn:
                row = conn.execute("SELECT preview_json FROM calendario_cronogramas WHERE fundacion_id=? AND id=?", (self._tenant_id(), cronograma_id)).fetchone()
            if row and row["preview_json"]:
                try:
                    actividades = (json.loads(row["preview_json"]).get("actividades") or [])
                except Exception:
                    actividades = []
        for idx, item in enumerate(actividades or [], start=1):
            try:
                if not item or item.get("descartar") is True:
                    continue
                fecha = parse_fecha(item.get("fecha_limite") or item.get("fecha") or item.get("fecha_entrega"))
                titulo = str(item.get("titulo") or item.get("actividad") or "").strip()
                if not fecha or not titulo:
                    errores.append({"fila": idx, "error": "La actividad debe tener fecha y título para guardarse."})
                    continue
                entregables_text = str(item.get("entregables") or item.get("tipo_formato") or "").strip()
                descripcion_text = str(item.get("descripcion") or item.get("observaciones") or item.get("observacion") or "").strip()
                if entregables_text and entregables_text not in descripcion_text:
                    descripcion_text = (descripcion_text + "\nEntregables requeridos: " + entregables_text).strip()
                payload = {
                    "fecha_limite": fecha,
                    "fecha_inicio": parse_fecha(item.get("fecha_inicio")) or fecha,
                    "titulo": titulo,
                    "descripcion": descripcion_text,
                    "responsable_nombre": item.get("responsable_nombre") or item.get("responsable") or "",
                    "coordinador": item.get("coordinador") or "",
                    "unidad": item.get("unidad") or item.get("uds") or "",
                    "modulo": item.get("modulo") or item.get("componente") or "General",
                    "tipo_formato": item.get("tipo_formato") or item.get("entregables") or item.get("modulo") or "General",
                    "estado": item.get("estado") or "programado",
                    "prioridad": item.get("prioridad") or "Media",
                    "observaciones": item.get("observaciones") or item.get("observacion") or "",
                    "municipio": item.get("municipio") or "",
                    "creado_por": usuario,
                    "requiere_evidencia": item.get("requiere_evidencia", True),
                }
                prepared = self._prepare_payload(payload, origen="cronograma")
                before = self.find_by_clave(prepared["clave_unica"])
                entregable = self.create_entregable(payload, origen="cronograma")
                if before:
                    duplicados += 1
                else:
                    creados += 1
                with self.connect() as conn:
                    conn.execute(
                        """
                        INSERT INTO calendario_actividades (
                            cronograma_id, entregable_id, fecha, titulo, descripcion, responsable,
                            coordinador, unidad, modulo, estado, prioridad, observacion, archivo_origen,
                            usuario_carga, fecha_carga, created_at, updated_at, clave_unica, fundacion_id
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            cronograma_id,
                            entregable.get("id") if entregable else None,
                            fecha,
                            titulo,
                            payload.get("descripcion"),
                            payload.get("responsable_nombre"),
                            payload.get("coordinador"),
                            payload.get("unidad"),
                            canonical_modulo(payload.get("modulo"), payload.get("tipo_formato")),
                            entregable.get("estado") if entregable else prepared.get("estado"),
                            payload.get("prioridad"),
                            payload.get("observaciones"),
                            item.get("archivo_origen") or "cronograma",
                            usuario,
                            now,
                            now,
                            now,
                            prepared.get("clave_unica"),
                            self._tenant_id(),
                        ),
                    )
                    conn.commit()
            except Exception as exc:
                errores.append({"fila": idx, "error": str(exc)})
        with self.connect() as conn:
            conn.execute(
                "UPDATE calendario_cronogramas SET estado=?, fecha_confirmacion=?, confirmado_por=? WHERE fundacion_id=? AND id=?",
                ("APROBADO", now, usuario, self._tenant_id(), cronograma_id),
            )
            conn.execute(
                "INSERT INTO calendario_auditoria (accion, referencia_tipo, referencia_id, detalle, usuario, created_at, fundacion_id) VALUES (?,?,?,?,?,?,?)",
                ("confirmar_cronograma", "cronograma", cronograma_id, f"Creados {creados}, duplicados {duplicados}, errores {len(errores)}", usuario, now, self._tenant_id()),
            )
            conn.commit()
        return {
            "cronograma_id": cronograma_id,
            "creados": creados,
            "duplicados": duplicados,
            "errores": errores[:100],
            "total_recibidas": len(actividades or []),
        }

    def exportar_cronograma_excel(self, filters: dict[str, Any] | None = None) -> str:
        """Genera un Excel simple del cronograma filtrado."""
        if not self.upload_folder:
            raise ValueError("No hay carpeta de salida configurada para exportar.")
        eventos = self.list_entregables(filters or {}, limit=10000)
        out_dir = Path(self.upload_folder) / "calendario_inteligente" / "exports"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"cronograma_calendario_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
        rows = []
        for e in eventos:
            rows.append({
                "Fecha": e.get("fecha_limite"),
                "Actividad": e.get("titulo"),
                "Descripción": e.get("descripcion"),
                "Responsable": e.get("responsable_nombre"),
                "Coordinador": e.get("coordinador"),
                "Unidad": e.get("unidad"),
                "Módulo": e.get("modulo"),
                "Estado": e.get("estado"),
                "Prioridad": e.get("prioridad"),
                "Observaciones": e.get("observaciones"),
            })
        pd.DataFrame(rows).to_excel(out_path, index=False)
        return str(out_path)

    def exportar_cronograma_pdf(self, filters: dict[str, Any] | None = None) -> str:
        """Genera un PDF sencillo del calendario filtrado."""
        if not self.upload_folder:
            raise ValueError("No hay carpeta de salida configurada para exportar.")
        eventos = self.list_entregables(filters or {}, limit=10000)
        out_dir = Path(self.upload_folder) / "calendario_inteligente" / "exports"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"cronograma_calendario_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter, landscape
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        except Exception as exc:
            raise ValueError("Para exportar PDF se requiere reportlab instalado.") from exc
        styles = getSampleStyleSheet()
        doc = SimpleDocTemplate(str(out_path), pagesize=landscape(letter), rightMargin=28, leftMargin=28, topMargin=28, bottomMargin=28)
        story = [Paragraph("Calendario Inteligente de Entregables", styles["Title"]), Spacer(1, 10)]
        data = [["Fecha", "Actividad", "Módulo", "Unidad", "Coordinador", "Estado"]]
        for e in eventos[:250]:
            data.append([
                str(e.get("fecha_limite") or ""),
                str(e.get("titulo") or "")[:55],
                str(e.get("modulo") or "")[:28],
                str(e.get("unidad") or "")[:28],
                str(e.get("coordinador") or "")[:28],
                str(e.get("estado") or ""),
            ])
        if len(data) == 1:
            data.append(["Sin actividades", "", "", "", "", ""])
        table = Table(data, repeatRows=1, colWidths=[70, 240, 120, 130, 130, 80])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ]))
        story.append(table)
        doc.build(story)
        return str(out_path)

    def find_by_clave(self, clave: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM calendario_entregables WHERE fundacion_id=? AND clave_unica=?", (self._tenant_id(), clave)).fetchone()
        return self._row(row)

    def dashboard(self, periodo: str | None = None, anio: str | None = None, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        if not periodo:
            periodo = date.today().isoformat()[:7]
        filtros = {**(filters or {}), "periodo": periodo}
        eventos = self.list_entregables(filtros, limit=1000)
        annual = self.list_entregables({**(filters or {}), "anio": anio or periodo[:4]}, limit=5000)
        def count_color(*colors):
            return sum(1 for e in eventos if e.get("color") in colors or e.get("color_calculado") in colors)
        entregados = sum(1 for e in eventos if e.get("estado") in {"entregado", "aprobado"})
        resumen = {
            "entregables_mes": len(eventos),
            "proximos": count_color("amarillo", "naranja"),
            "vencidos": count_color("rojo"),
            "entregados": entregados,
            "programados": count_color("azul"),
        }
        resumen["cumplimiento_general"] = round((entregados / len(eventos)) * 100, 1) if eventos else 0
        return {
            "periodo": periodo,
            "anio": anio or periodo[:4],
            "resumen": resumen,
            "eventos": eventos,
            "annual": annual,
            "alertas": self.alertas(eventos),
            "cumplimiento_coordinador": self.cumplimiento(eventos, "coordinador"),
            "cumplimiento_modulo": self.cumplimiento(eventos, "modulo"),
            "catalogos": self.catalogos(),
        }

    def alertas(self, eventos: list[dict[str, Any]]) -> list[dict[str, Any]]:
        today = date.today()
        fid = self._tenant_id()
        with self.connect() as conn:
            for event in eventos:
                if str(event.get("estado") or "").lower() in {"entregado", "aprobado", "cerrado", "no_aplica", "cancelado"}:
                    continue
                try:
                    due = date.fromisoformat(str(event.get("fecha_limite") or "")[:10])
                except ValueError:
                    continue
                for offset, kind in ((5, "VENCE_5_DIAS"), (3, "VENCE_3_DIAS"), (1, "VENCE_1_DIA"), (0, "VENCE_HOY"), (-1, "VENCIDO")):
                    scheduled = (due - timedelta(days=offset)).isoformat()
                    level = "rojo" if offset <= 0 else ("naranja" if offset == 1 else "amarillo")
                    message = f"{event.get('titulo')} vence {due.isoformat()}." if offset >= 0 else f"{event.get('titulo')} está vencido."
                    conn.execute("""INSERT INTO calendario_alertas(entregable_id,fecha,nivel,mensaje,estado,created_at,fundacion_id,evento,usuario_id,tipo,fecha_programada,fecha_enviada) VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(fundacion_id,entregable_id,usuario_id,tipo,fecha_programada) DO NOTHING""", (event.get("id"), due.isoformat(), level, message, "PROGRAMADA", now_iso(), fid, "VENCIMIENTO", event.get("responsable_id") or 0, kind, scheduled, None))
            conn.execute("UPDATE calendario_alertas SET estado='ENVIADA',fecha_enviada=COALESCE(fecha_enviada,?) WHERE fundacion_id=? AND estado='PROGRAMADA' AND fecha_programada<=?", (now_iso(), fid, today.isoformat()))
            rows = conn.execute("""SELECT a.*,e.modulo,e.fecha_limite FROM calendario_alertas a LEFT JOIN calendario_entregables e ON e.id=a.entregable_id AND e.fundacion_id=a.fundacion_id WHERE a.fundacion_id=? AND a.estado='ENVIADA' AND COALESCE(LOWER(e.estado),'pendiente') NOT IN ('entregado','aprobado','cerrado','no_aplica','cancelado') ORDER BY a.fecha_programada DESC,a.id DESC LIMIT 50""", (fid,)).fetchall()
            conn.commit()
        return [{"id": row["entregable_id"], "alerta_id": row["id"], "nivel": row["nivel"], "mensaje": row["mensaje"], "fecha_limite": row["fecha_limite"], "modulo": row["modulo"], "tipo": row["tipo"]} for row in rows]

    def cumplimiento(self, eventos: list[dict[str, Any]], campo: str) -> list[dict[str, Any]]:
        buckets: dict[str, dict[str, int]] = {}
        for e in eventos:
            key = str(e.get(campo) or "Sin asignar").strip() or "Sin asignar"
            buckets.setdefault(key, {"total": 0, "entregado": 0, "vencido": 0})
            buckets[key]["total"] += 1
            if e.get("estado") in {"entregado", "aprobado"}:
                buckets[key]["entregado"] += 1
            if (e.get("color") or e.get("color_calculado")) == "rojo":
                buckets[key]["vencido"] += 1
        rows = []
        for key, values in buckets.items():
            total = values["total"]
            rows.append({
                "nombre": key,
                "total": total,
                "entregados": values["entregado"],
                "vencidos": values["vencido"],
                "porcentaje": round((values["entregado"] / total) * 100, 1) if total else 0,
            })
        return sorted(rows, key=lambda x: (-x["vencidos"], x["porcentaje"], x["nombre"]))

    def catalogos(self) -> dict[str, Any]:
        with self.connect() as conn:
            coordinadores = [r[0] for r in conn.execute("SELECT DISTINCT coordinador FROM calendario_entregables WHERE fundacion_id=? AND COALESCE(coordinador,'')<>'' ORDER BY coordinador", (self._tenant_id(),)).fetchall()]
            unidades = [r[0] for r in conn.execute("SELECT DISTINCT unidad FROM calendario_entregables WHERE fundacion_id=? AND COALESCE(unidad,'')<>'' ORDER BY unidad", (self._tenant_id(),)).fetchall()]
        return {"estados": ESTADOS_PERMITIDOS, "modulos": MODULOS_PERMITIDOS, "coordinadores": coordinadores, "unidades": unidades}

    def marcar_entregado(self, entregable_id: int, archivo: str | None = None, observaciones: str | None = None) -> dict[str, Any] | None:
        data = {"estado": "entregado", "fecha_entrega": date.today().isoformat()}
        if archivo:
            data["archivo_evidencia"] = archivo
        if observaciones:
            data["observaciones"] = observaciones
        return self.update_entregable(entregable_id, data)

    def sincronizar_entrega(self, data: dict[str, Any]) -> dict[str, Any] | None:
        # Busca un entregable abierto del mismo módulo/unidad/formato en el mes; si existe, lo marca entregado.
        fecha = parse_fecha(data.get("fecha_entrega")) or date.today().isoformat()
        periodo = fecha[:7]
        modulo = canonical_modulo(data.get("modulo"), data.get("tipo_formato"))
        unidad = data.get("unidad") or ""
        eventos = self.list_entregables({"periodo": periodo, "modulo": modulo, "unidad": unidad}, limit=20)
        candidatos = [e for e in eventos if e.get("estado") not in {"entregado", "aprobado", "no_aplica", "cerrado"}]
        if candidatos:
            return self.update_entregable(candidatos[0]["id"], {"estado": "entregado", "fecha_entrega": fecha, "archivo_evidencia": data.get("archivo_evidencia")})
        payload = {
            "titulo": data.get("titulo") or f"Entrega {modulo}",
            "fecha_limite": fecha,
            "fecha_entrega": fecha,
            "estado": "entregado",
            "modulo": modulo,
            "tipo_formato": data.get("tipo_formato") or modulo,
            "unidad": unidad,
            "coordinador": data.get("coordinador") or "",
            "responsable_nombre": data.get("responsable_nombre") or "",
            "observaciones": data.get("observaciones") or "Sincronizado desde módulo operativo.",
        }
        return self.create_entregable(payload, origen="sincronizacion")
