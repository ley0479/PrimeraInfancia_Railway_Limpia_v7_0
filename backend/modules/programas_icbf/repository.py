from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from modules.dbapi_compat import sqlite3

from .adapters import adapter_definition
from .schema import SCHEMA_SQL

PROFILE_CODE = "SERVICIO_INTEGRADO_DESNUTRICION_EXTRAMURAL"
PROFILE_NAME = "Servicio Integrado de Atención y Prevención de la Desnutrición"
DEFAULT_SORT_CRITERION = "PRIMER_NOMBRE"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_name(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).upper()
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 ]+", " ", text)).strip()


def json_hash(value) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class ProgramasIcbfRepository:
    def __init__(self, database_path: str):
        self.database_path = str(database_path)

    def connect(self):
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self) -> None:
        if os.getenv("SKIP_RUNTIME_SCHEMA_DDL", "").strip().lower() in {"1", "true", "yes", "si", "sí", "on"} and os.getenv("APP_SCHEMA_MIGRATION_MODE", "").strip().lower() not in {"1", "true", "yes", "si", "sí", "on"}:
            return
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()

    def ensure_profile(self, fundacion_id: int, user_id: int | None = None) -> dict:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM icbf_program_profiles WHERE fundacion_id=? AND codigo=? ORDER BY version DESC LIMIT 1",
                (fundacion_id, PROFILE_CODE),
            ).fetchone()
            if not row:
                now = now_iso()
                cur = conn.execute(
                    """INSERT INTO icbf_program_profiles
                    (fundacion_id,codigo,nombre,modalidad,version,estado,criterio_orden,configuracion_json,creado_por,creado_en,actualizado_en)
                    VALUES(?,?,?,?,1,'INACTIVO',?,?,?,?,?)""",
                    (fundacion_id, PROFILE_CODE, PROFILE_NAME, "EXTRAMURAL", DEFAULT_SORT_CRITERION, json.dumps({"adapter_code": "SERVICIO_INTEGRADO_EXTRAMURAL_V1", "rfpp_rows": 20, "f2_rows": 30}), user_id, now, now),
                )
                profile_id = int(cur.lastrowid)
                self._audit(conn, fundacion_id, profile_id, None, user_id, "PERFIL_CREADO", {"estado": "INACTIVO"})
                conn.commit()
                row = conn.execute("SELECT * FROM icbf_program_profiles WHERE id=? AND fundacion_id=?", (profile_id, fundacion_id)).fetchone()
            elif not row["criterio_orden"]:
                now = now_iso()
                conn.execute("UPDATE icbf_program_profiles SET criterio_orden=?,actualizado_en=? WHERE id=? AND fundacion_id=?", (DEFAULT_SORT_CRITERION, now, row["id"], fundacion_id))
                self._audit(conn, fundacion_id, row["id"], None, user_id, "CRITERIO_ORDEN_CONFIRMADO", {"criterio": DEFAULT_SORT_CRITERION, "opcion": "B"})
                conn.commit()
                row = conn.execute("SELECT * FROM icbf_program_profiles WHERE id=? AND fundacion_id=?", (row["id"], fundacion_id)).fetchone()
            config = json.loads(row["configuracion_json"] or "{}")
            if not config.get("adapter_code"):
                config["adapter_code"] = "SERVICIO_INTEGRADO_EXTRAMURAL_V1"
                conn.execute("UPDATE icbf_program_profiles SET configuracion_json=?,actualizado_en=? WHERE id=? AND fundacion_id=?", (json.dumps(config, ensure_ascii=False), now_iso(), row["id"], fundacion_id))
                conn.commit()
                row = conn.execute("SELECT * FROM icbf_program_profiles WHERE id=? AND fundacion_id=?", (row["id"], fundacion_id)).fetchone()
            return self._profile(row)

    def register_profile(self, fundacion_id: int, data: dict, user_id: int | None = None) -> dict:
        code = str(data.get("codigo") or "").strip().upper()
        name = str(data.get("nombre") or "").strip()
        mode = str(data.get("modalidad") or "").strip().upper()
        adapter = adapter_definition(data.get("adapter_code"))
        if not re.fullmatch(r"[A-Z0-9_]{3,80}", code) or not name or not mode:
            raise ValueError("Código, nombre y modalidad válidos son obligatorios.")
        with self.connect() as conn:
            latest = conn.execute("SELECT * FROM icbf_program_profiles WHERE fundacion_id=? AND codigo=? ORDER BY version DESC LIMIT 1", (fundacion_id, code)).fetchone()
            config = dict(data.get("configuracion") or {})
            config["adapter_code"] = adapter["codigo"]
            normalized = json.dumps(config, ensure_ascii=False, sort_keys=True)
            if latest and latest["nombre"] == name and latest["modalidad"] == mode and json.dumps(json.loads(latest["configuracion_json"] or "{}"), ensure_ascii=False, sort_keys=True) == normalized:
                return self._profile(latest)
            version = int(latest["version"] or 0) + 1 if latest else 1
            now = now_iso()
            cur = conn.execute("""INSERT INTO icbf_program_profiles
                (fundacion_id,codigo,nombre,modalidad,version,estado,criterio_orden,configuracion_json,creado_por,creado_en,actualizado_en)
                VALUES(?,?,?,?,?,'INACTIVO',?,?,?, ?,?)""", (fundacion_id, code, name, mode, version, data.get("criterio_orden"), normalized, user_id, now, now))
            profile_id = int(cur.lastrowid)
            self._audit(conn, fundacion_id, profile_id, None, user_id, "PERFIL_REGISTRADO", {"codigo": code, "version": version, "adapter_code": adapter["codigo"]})
            conn.commit()
            return self._profile(conn.execute("SELECT * FROM icbf_program_profiles WHERE id=? AND fundacion_id=?", (profile_id, fundacion_id)).fetchone())

    def set_profile_state(self, fundacion_id: int, profile_id: int, state: str, user_id: int | None = None, allow_active: bool = False) -> dict:
        state = str(state or "").strip().upper()
        if state not in {"INACTIVO", "PILOTO", "ACTIVO"}:
            raise ValueError("Estado de perfil no permitido.")
        if state == "ACTIVO" and not allow_active:
            raise ValueError("La activación productiva requiere autorización y bandera independientes.")
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM icbf_program_profiles WHERE id=? AND fundacion_id=?", (profile_id, fundacion_id)).fetchone()
            if not row:
                raise ValueError("Perfil no encontrado.")
            conn.execute("UPDATE icbf_program_profiles SET estado=?,actualizado_en=? WHERE id=? AND fundacion_id=?", (state, now_iso(), profile_id, fundacion_id))
            self._audit(conn, fundacion_id, profile_id, None, user_id, "ESTADO_PERFIL_ACTUALIZADO", {"anterior": row["estado"], "nuevo": state})
            conn.commit()
            return self._profile(conn.execute("SELECT * FROM icbf_program_profiles WHERE id=? AND fundacion_id=?", (profile_id, fundacion_id)).fetchone())

    def list_profiles(self, fundacion_id: int) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM icbf_program_profiles WHERE fundacion_id=? ORDER BY codigo,version DESC", (fundacion_id,)).fetchall()
            return [self._profile(row) for row in rows]

    def list_loads(self, fundacion_id: int, profile_id: int) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM icbf_program_loads WHERE fundacion_id=? AND profile_id=? ORDER BY creado_en DESC,id DESC", (fundacion_id, profile_id)).fetchall()
            return [self.get_load(fundacion_id, int(row["id"]), conn=conn) for row in rows]

    def list_communities(self, fundacion_id: int, profile_id: int) -> list[dict]:
        with self.connect() as conn:
            return [dict(row) for row in conn.execute("SELECT * FROM icbf_program_communities WHERE fundacion_id=? AND profile_id=? AND vigente=1 ORDER BY nombre_normalizado,id", (fundacion_id, profile_id)).fetchall()]

    def set_sort_criterion(self, fundacion_id: int, profile_id: int, criterion: str | None, user_id: int | None = None) -> dict:
        allowed = {None, "PRIMER_APELLIDO", "PRIMER_NOMBRE"}
        criterion = str(criterion or "").strip().upper() or None
        if criterion not in allowed:
            raise ValueError("Criterio inválido. Usa PRIMER_APELLIDO, PRIMER_NOMBRE o vacío.")
        with self.connect() as conn:
            cur = conn.execute("UPDATE icbf_program_profiles SET criterio_orden=?,actualizado_en=? WHERE id=? AND fundacion_id=?", (criterion, now_iso(), profile_id, fundacion_id))
            if not cur.rowcount:
                raise ValueError("Perfil no encontrado.")
            self._audit(conn, fundacion_id, profile_id, None, user_id, "CRITERIO_ORDEN_ACTUALIZADO", {"criterio": criterion})
            conn.commit()
            row = conn.execute("SELECT * FROM icbf_program_profiles WHERE id=? AND fundacion_id=?", (profile_id, fundacion_id)).fetchone()
            return self._profile(row)

    def create_snapshot(self, fundacion_id: int, profile_id: int, import_id: int, user_id: int | None = None) -> dict:
        with self.connect() as conn:
            profile = conn.execute("SELECT * FROM icbf_program_profiles WHERE id=? AND fundacion_id=?", (profile_id, fundacion_id)).fetchone()
            if not profile:
                raise ValueError("Perfil no encontrado.")
            source = conn.execute("SELECT id,hash_sha256,estado FROM importaciones_universales WHERE id=? AND tenant_id=?", (import_id, fundacion_id)).fetchone()
            if not source:
                raise ValueError("Importación universal no encontrada para esta fundación.")
            existing = conn.execute("SELECT id FROM icbf_program_loads WHERE fundacion_id=? AND profile_id=? AND source_import_id=?", (fundacion_id, profile_id, import_id)).fetchone()
            if existing:
                return self.get_load(fundacion_id, int(existing["id"]), conn=conn)
            staged = conn.execute("SELECT id,numero_fila,normalizado_json FROM importaciones_filas_staging WHERE importacion_id=? AND tenant_id=? ORDER BY numero_fila", (import_id, fundacion_id)).fetchall()
            if not staged:
                raise ValueError("La importación no contiene filas normalizadas.")
            prepared = []
            for row in staged:
                bundle = json.loads(row["normalizado_json"] or "{}")
                canonical = bundle.get("canonical") or {}
                key = "|".join(str(canonical.get(name) or "").strip().upper() for name in ("participante.tipo_documento", "participante.numero_documento"))
                prepared.append({"source_row_id": int(row["id"]), "row": int(row["numero_fila"]), "key_hash": hashlib.sha256(key.encode("utf-8")).hexdigest(), "canonical": canonical, "key_present": bool(canonical.get("participante.numero_documento"))})
            quality = self._quality(prepared)
            snapshot_sha = json_hash([{"row": p["row"], "key": p["key_hash"], "canonical": p["canonical"]} for p in prepared])
            now = now_iso()
            cur = conn.execute("""INSERT INTO icbf_program_loads
                (fundacion_id,profile_id,source_import_id,source_sha256,snapshot_sha256,estado,total_registros,quality_json,creado_por,creado_en,actualizado_en)
                VALUES(?,?,?,?,?,'BORRADOR',?,?,?,?,?)""",
                (fundacion_id, profile_id, import_id, source["hash_sha256"], snapshot_sha, len(prepared), json.dumps(quality, ensure_ascii=False), user_id, now, now))
            load_id = int(cur.lastrowid)
            for item in prepared:
                conn.execute("""INSERT INTO icbf_program_participants
                    (fundacion_id,load_id,source_row_id,source_row_number,participant_key_hash,canonical_json,creado_en,actualizado_en)
                    VALUES(?,?,?,?,?,?,?,?)""", (fundacion_id, load_id, item["source_row_id"], item["row"], item["key_hash"], json.dumps(item["canonical"], ensure_ascii=False, default=str), now, now))
            self._audit(conn, fundacion_id, profile_id, load_id, user_id, "SNAPSHOT_CREADO", {"total": len(prepared), "quality": quality, "source_import_id": import_id})
            conn.commit()
            return self.get_load(fundacion_id, load_id, conn=conn)

    def create_community(self, fundacion_id: int, profile_id: int, name: str, code: str | None = None, user_id: int | None = None) -> dict:
        normalized = normalize_name(name)
        if not normalized:
            raise ValueError("El nombre de la comunidad es obligatorio.")
        with self.connect() as conn:
            if not conn.execute("SELECT 1 FROM icbf_program_profiles WHERE id=? AND fundacion_id=?", (profile_id, fundacion_id)).fetchone():
                raise ValueError("Perfil no encontrado.")
            latest = conn.execute("SELECT * FROM icbf_program_communities WHERE fundacion_id=? AND profile_id=? AND nombre_normalizado=? ORDER BY version DESC LIMIT 1", (fundacion_id, profile_id, normalized)).fetchone()
            if latest and int(latest["vigente"] or 0) == 1 and str(latest["codigo"] or "") == str(code or ""):
                return dict(latest)
            version = int(latest["version"] or 0) + 1 if latest else 1
            if latest:
                conn.execute("UPDATE icbf_program_communities SET vigente=0 WHERE id=? AND fundacion_id=?", (latest["id"], fundacion_id))
            cur = conn.execute("""INSERT INTO icbf_program_communities
                (fundacion_id,profile_id,codigo,nombre,nombre_normalizado,version,vigente,creado_por,creado_en)
                VALUES(?,?,?,?,?,?,1,?,?)""", (fundacion_id, profile_id, code, str(name).strip(), normalized, version, user_id, now_iso()))
            community_id = int(cur.lastrowid)
            self._audit(conn, fundacion_id, profile_id, None, user_id, "COMUNIDAD_CREADA", {"community_id": community_id, "version": version})
            conn.commit()
            return dict(conn.execute("SELECT * FROM icbf_program_communities WHERE id=? AND fundacion_id=?", (community_id, fundacion_id)).fetchone())

    def assign_community(self, fundacion_id: int, load_id: int, participant_id: int, community_id: int, user_id: int | None = None, reason: str | None = None) -> dict:
        with self.connect() as conn:
            participant = conn.execute("SELECT p.*,l.profile_id FROM icbf_program_participants p JOIN icbf_program_loads l ON l.id=p.load_id AND l.fundacion_id=p.fundacion_id WHERE p.id=? AND p.load_id=? AND p.fundacion_id=?", (participant_id, load_id, fundacion_id)).fetchone()
            if not participant:
                raise ValueError("Participante no encontrado en esta carga.")
            community = conn.execute("SELECT * FROM icbf_program_communities WHERE id=? AND fundacion_id=? AND profile_id=? AND vigente=1", (community_id, fundacion_id, participant["profile_id"])).fetchone()
            if not community:
                raise ValueError("Comunidad vigente no encontrada para este perfil.")
            version_row = conn.execute("SELECT COALESCE(MAX(version),0)+1 v FROM icbf_program_community_assignments WHERE fundacion_id=? AND load_id=? AND participant_id=?", (fundacion_id, load_id, participant_id)).fetchone()
            version = int(version_row["v"])
            now = now_iso()
            conn.execute("INSERT INTO icbf_program_community_assignments(fundacion_id,load_id,participant_id,community_id,version,motivo,asignado_por,creado_en) VALUES(?,?,?,?,?,?,?,?)", (fundacion_id, load_id, participant_id, community_id, version, reason, user_id, now))
            conn.execute("UPDATE icbf_program_participants SET community_id=?,actualizado_en=? WHERE id=? AND load_id=? AND fundacion_id=?", (community_id, now, participant_id, load_id, fundacion_id))
            self._audit(conn, fundacion_id, participant["profile_id"], load_id, user_id, "COMUNIDAD_ASIGNADA", {"participant_id": participant_id, "community_id": community_id, "version": version})
            conn.commit()
            return {"participant_id": participant_id, "community_id": community_id, "version": version}

    def get_load(self, fundacion_id: int, load_id: int, conn=None) -> dict:
        own = conn is None
        conn = conn or self.connect()
        try:
            row = conn.execute("SELECT * FROM icbf_program_loads WHERE id=? AND fundacion_id=?", (load_id, fundacion_id)).fetchone()
            if not row:
                raise ValueError("Carga no encontrada.")
            data = dict(row)
            data["quality"] = json.loads(data.pop("quality_json") or "{}")
            counts = conn.execute("SELECT COUNT(*) total,SUM(CASE WHEN community_id IS NULL THEN 1 ELSE 0 END) pendientes FROM icbf_program_participants WHERE load_id=? AND fundacion_id=?", (load_id, fundacion_id)).fetchone()
            data["communities"] = {"assigned": int(counts["total"] or 0) - int(counts["pendientes"] or 0), "pending": int(counts["pendientes"] or 0)}
            return data
        finally:
            if own:
                conn.close()

    def list_participants(self, fundacion_id: int, load_id: int, only_unassigned: bool = False) -> list[dict]:
        clause = " AND p.community_id IS NULL" if only_unassigned else ""
        with self.connect() as conn:
            rows = conn.execute(f"SELECT p.id,p.source_row_number,p.community_id,p.canonical_json,c.nombre community_name FROM icbf_program_participants p LEFT JOIN icbf_program_communities c ON c.id=p.community_id AND c.fundacion_id=p.fundacion_id WHERE p.load_id=? AND p.fundacion_id=?{clause} ORDER BY p.source_row_number", (load_id, fundacion_id)).fetchall()
            return [{**dict(row), "canonical": json.loads(row["canonical_json"] or "{}")} for row in rows]

    def generation_context(self, fundacion_id: int, load_id: int, community_id: int) -> dict:
        with self.connect() as conn:
            load = conn.execute("""SELECT l.*,p.criterio_orden,p.estado profile_state
                FROM icbf_program_loads l JOIN icbf_program_profiles p
                ON p.id=l.profile_id AND p.fundacion_id=l.fundacion_id
                WHERE l.id=? AND l.fundacion_id=?""", (load_id, fundacion_id)).fetchone()
            if not load:
                raise ValueError("Carga no encontrada.")
            if load["criterio_orden"] not in {"PRIMER_APELLIDO", "PRIMER_NOMBRE"}:
                raise ValueError("El criterio alfabético del perfil está pendiente de confirmación.")
            community = conn.execute("SELECT * FROM icbf_program_communities WHERE id=? AND profile_id=? AND fundacion_id=? AND vigente=1", (community_id, load["profile_id"], fundacion_id)).fetchone()
            if not community:
                raise ValueError("Comunidad vigente no encontrada para esta carga.")
            rows = conn.execute("SELECT id,source_row_number,canonical_json FROM icbf_program_participants WHERE load_id=? AND community_id=? AND fundacion_id=? ORDER BY source_row_number", (load_id, community_id, fundacion_id)).fetchall()
            if not rows:
                raise ValueError("La comunidad seleccionada no contiene participantes asignados.")
            participants = [{"id": int(row["id"]), "source_row_number": int(row["source_row_number"]), "canonical": json.loads(row["canonical_json"] or "{}")} for row in rows]
            return {"load": dict(load), "community": dict(community), "participants": participants}

    def find_generation(self, fundacion_id: int, request_sha256: str) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM icbf_program_generations WHERE fundacion_id=? AND request_sha256=?", (fundacion_id, request_sha256)).fetchone()
            return self._generation(row) if row else None

    def save_generation(self, fundacion_id: int, context: dict, format_code: str, period: str, template_sha: str, request_sha: str, files: list[dict], pending: list[str], user_id: int | None = None) -> dict:
        with self.connect() as conn:
            existing = conn.execute("SELECT * FROM icbf_program_generations WHERE fundacion_id=? AND request_sha256=?", (fundacion_id, request_sha)).fetchone()
            if existing:
                return self._generation(existing)
            load = context["load"]
            community = context["community"]
            public_files = [{key: value for key, value in item.items() if key != "participant_ids"} for item in files]
            cur = conn.execute("""INSERT INTO icbf_program_generations
                (fundacion_id,profile_id,load_id,community_id,formato,periodo,criterio_orden,template_sha256,request_sha256,estado,archivos_json,pendientes_json,creado_por,creado_en)
                VALUES(?,?,?,?,?,?,?,?,?,'PREDILIGENCIADO',?,?,?,?)""",
                (fundacion_id, load["profile_id"], load["id"], community["id"], format_code, period, load["criterio_orden"], template_sha, request_sha, json.dumps(public_files, ensure_ascii=False), json.dumps(pending, ensure_ascii=False), user_id, now_iso()))
            generation_id = int(cur.lastrowid)
            self._audit(conn, fundacion_id, load["profile_id"], load["id"], user_id, "PREDILIGENCIADO_GENERADO", {"generation_id": generation_id, "formato": format_code, "community_id": community["id"], "archivos": len(files), "pendientes": pending})
            conn.commit()
            return self._generation(conn.execute("SELECT * FROM icbf_program_generations WHERE id=? AND fundacion_id=?", (generation_id, fundacion_id)).fetchone())

    def get_generation(self, fundacion_id: int, generation_id: int) -> dict:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM icbf_program_generations WHERE id=? AND fundacion_id=?", (generation_id, fundacion_id)).fetchone()
            if not row:
                raise ValueError("Generación no encontrada.")
            return self._generation(row)

    def save_delivery_point(self, fundacion_id: int, profile_id: int, data: dict, user_id: int | None = None) -> dict:
        code = str(data.get("codigo") or "").strip()
        name = str(data.get("nombre") or "").strip()
        point_type = str(data.get("tipo") or "").strip().upper()
        if not code or not name or point_type not in {"UDS", "PUNTO_PRIMARIO"}:
            raise ValueError("Código, nombre y tipo UDS/PUNTO_PRIMARIO son obligatorios.")
        with self.connect() as conn:
            if not conn.execute("SELECT 1 FROM icbf_program_profiles WHERE id=? AND fundacion_id=?", (profile_id, fundacion_id)).fetchone():
                raise ValueError("Perfil no encontrado.")
            current = conn.execute("SELECT * FROM icbf_program_delivery_points WHERE fundacion_id=? AND profile_id=? AND codigo=? AND vigente=1 ORDER BY version DESC LIMIT 1", (fundacion_id, profile_id, code)).fetchone()
            comparable = {field: str(data.get(field) or "").strip() for field in ("nombre", "direccion", "barrio", "telefono", "responsable", "suplente", "origen_codigo", "origen_nombre")}
            comparable["tipo"] = point_type
            if current and all(str(current[field] or "").strip() == value for field, value in comparable.items()):
                return dict(current)
            version = int(current["version"] or 0) + 1 if current else 1
            if current:
                conn.execute("UPDATE icbf_program_delivery_points SET vigente=0 WHERE id=? AND fundacion_id=?", (current["id"], fundacion_id))
            now = now_iso()
            cur = conn.execute("""INSERT INTO icbf_program_delivery_points
                (fundacion_id,profile_id,codigo,nombre,tipo,direccion,barrio,telefono,responsable,suplente,origen_codigo,origen_nombre,version,vigente,creado_por,creado_en)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?)""", (fundacion_id, profile_id, code, name, point_type, comparable["direccion"], comparable["barrio"], comparable["telefono"], comparable["responsable"], comparable["suplente"], comparable["origen_codigo"], comparable["origen_nombre"], version, user_id, now))
            point_id = int(cur.lastrowid)
            self._audit(conn, fundacion_id, profile_id, None, user_id, "PUNTO_ENTREGA_VERSIONADO", {"point_id": point_id, "codigo": code, "version": version})
            conn.commit()
            return dict(conn.execute("SELECT * FROM icbf_program_delivery_points WHERE id=? AND fundacion_id=?", (point_id, fundacion_id)).fetchone())

    def link_health_activity(self, fundacion_id: int, profile_id: int, load_id: int, community_id: int, activity_id: int, period: str, point_id: int | None, user_id: int | None = None) -> dict:
        period = str(period or "").strip()
        if not re.fullmatch(r"\d{4}-\d{2}", period):
            raise ValueError("El periodo debe usar YYYY-MM.")
        with self.connect() as conn:
            load = conn.execute("SELECT 1 FROM icbf_program_loads WHERE id=? AND profile_id=? AND fundacion_id=?", (load_id, profile_id, fundacion_id)).fetchone()
            community = conn.execute("SELECT 1 FROM icbf_program_communities WHERE id=? AND profile_id=? AND fundacion_id=? AND vigente=1", (community_id, profile_id, fundacion_id)).fetchone()
            activity = conn.execute("SELECT id FROM sn_actividades_integrales WHERE id=? AND fundacion_id=?", (activity_id, fundacion_id)).fetchone()
            if not load or not community or not activity:
                raise ValueError("Carga, comunidad o actividad de Salud y Nutrición no pertenecen al contexto autorizado.")
            if point_id and not conn.execute("SELECT 1 FROM icbf_program_delivery_points WHERE id=? AND profile_id=? AND fundacion_id=? AND vigente=1", (point_id, profile_id, fundacion_id)).fetchone():
                raise ValueError("Punto de entrega vigente no encontrado.")
            existing = conn.execute("SELECT * FROM icbf_program_activity_links WHERE fundacion_id=? AND profile_id=? AND health_activity_id=? AND community_id=? AND periodo=?", (fundacion_id, profile_id, activity_id, community_id, period)).fetchone()
            if existing:
                return dict(existing)
            now = now_iso()
            cur = conn.execute("""INSERT INTO icbf_program_activity_links
                (fundacion_id,profile_id,load_id,community_id,health_activity_id,delivery_point_id,periodo,estado,creado_por,creado_en)
                VALUES(?,?,?,?,?,?,?,'VINCULADA',?,?)""", (fundacion_id, profile_id, load_id, community_id, activity_id, point_id, period, user_id, now))
            link_id = int(cur.lastrowid)
            self._audit(conn, fundacion_id, profile_id, load_id, user_id, "ACTIVIDAD_SALUD_VINCULADA", {"link_id": link_id, "health_activity_id": activity_id, "community_id": community_id})
            conn.commit()
            return dict(conn.execute("SELECT * FROM icbf_program_activity_links WHERE id=? AND fundacion_id=?", (link_id, fundacion_id)).fetchone())

    def calendar_payload(self, fundacion_id: int, link_id: int) -> dict:
        with self.connect() as conn:
            row = conn.execute("""SELECT l.id,l.periodo,c.nombre comunidad,a.titulo,a.fecha_programada,a.responsable_id,a.responsable_nombre,a.unidad_nombre
                FROM icbf_program_activity_links l
                JOIN icbf_program_communities c ON c.id=l.community_id AND c.fundacion_id=l.fundacion_id
                JOIN sn_actividades_integrales a ON a.id=l.health_activity_id AND a.fundacion_id=l.fundacion_id
                WHERE l.id=? AND l.fundacion_id=?""", (link_id, fundacion_id)).fetchone()
            if not row:
                raise ValueError("Vinculación operativa no encontrada.")
            if not row["fecha_programada"]:
                return {"estado": "PENDIENTE_FECHA", "motivo": "La actividad no tiene fecha programada."}
            return {
                "titulo": row["titulo"] or "Actividad Servicio Integrado",
                "descripcion": f"Programa Servicio Integrado · comunidad {row['comunidad']} · vínculo {row['id']}",
                "fecha_inicio": row["fecha_programada"], "fecha_limite": row["fecha_programada"],
                "modulo": "salud-nutricion", "tipo_formato": "SERVICIO_INTEGRADO",
                "responsable_id": row["responsable_id"], "responsable_nombre": row["responsable_nombre"],
                "unidad": row["unidad_nombre"] or row["comunidad"], "estado": "pendiente",
                "prioridad": "media", "requiere_evidencia": 1,
                "observaciones": f"Origen multiprograma ICBF; periodo {row['periodo']}; no acredita ejecución.",
                "clave_unica": f"ICBF-PROGRAMA-LINK-{row['id']}",
            }

    def create_delivery_draft(self, fundacion_id: int, activity_link_id: int, participant_id: int, data: dict, user_id: int | None = None) -> dict:
        request_key = str(data.get("request_key") or "").strip()
        mode = str(data.get("modalidad") or "").strip().upper()
        if not request_key or mode not in {"COMUNITARIA", "HOGAR"}:
            raise ValueError("request_key y modalidad COMUNITARIA/HOGAR son obligatorios.")
        items = data.get("items") or []
        if not isinstance(items, list):
            raise ValueError("items debe ser una lista.")
        with self.connect() as conn:
            existing = conn.execute("SELECT id FROM icbf_program_deliveries WHERE fundacion_id=? AND request_key=?", (fundacion_id, request_key)).fetchone()
            if existing:
                return self.delivery_detail(fundacion_id, int(existing["id"]), conn=conn)
            context = conn.execute("""SELECT l.*,p.load_id,p.community_id FROM icbf_program_activity_links l
                JOIN icbf_program_participants p ON p.id=? AND p.fundacion_id=l.fundacion_id
                WHERE l.id=? AND l.fundacion_id=? AND p.load_id=l.load_id AND p.community_id=l.community_id""", (participant_id, activity_link_id, fundacion_id)).fetchone()
            if not context:
                raise ValueError("Participante y actividad no pertenecen a la misma carga y comunidad.")
            replaces = int(data.get("replaces_delivery_id") or 0) or None
            now = now_iso()
            cur = conn.execute("""INSERT INTO icbf_program_deliveries
                (fundacion_id,activity_link_id,participant_id,modalidad,fecha_entrega,receptor_nombre,receptor_documento,receptor_parentesco,estado,request_key,replaces_delivery_id,creado_por,creado_en,actualizado_en)
                VALUES(?,?,?,?,?,?,?,?,'BORRADOR',?,?,?,?,?)""", (fundacion_id, activity_link_id, participant_id, mode, data.get("fecha_entrega"), data.get("receptor_nombre"), data.get("receptor_documento"), data.get("receptor_parentesco"), request_key, replaces, user_id, now, now))
            delivery_id = int(cur.lastrowid)
            for item in items:
                conn.execute("INSERT INTO icbf_program_delivery_items(fundacion_id,delivery_id,producto,lote,unidades,unidad_medida,creado_en) VALUES(?,?,?,?,?,?,?)", (fundacion_id, delivery_id, str(item.get("producto") or "").strip(), str(item.get("lote") or "").strip() or None, item.get("unidades"), str(item.get("unidad_medida") or "").strip() or None, now))
            self._audit(conn, fundacion_id, context["profile_id"], context["load_id"], user_id, "ENTREGA_BORRADOR_CREADA", {"delivery_id": delivery_id, "participant_id": participant_id, "modalidad": mode})
            conn.commit()
            return self.delivery_detail(fundacion_id, delivery_id, conn=conn)

    def confirm_delivery(self, fundacion_id: int, delivery_id: int, user_id: int | None = None) -> dict:
        with self.connect() as conn:
            delivery = conn.execute("SELECT * FROM icbf_program_deliveries WHERE id=? AND fundacion_id=?", (delivery_id, fundacion_id)).fetchone()
            if not delivery:
                raise ValueError("Entrega no encontrada.")
            if delivery["estado"] == "CONFIRMADA":
                return self.delivery_detail(fundacion_id, delivery_id, conn=conn)
            if delivery["estado"] != "BORRADOR":
                raise ValueError("Solo una entrega en borrador puede confirmarse.")
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(delivery["fecha_entrega"] or "")):
                raise ValueError("La fecha real de entrega es obligatoria.")
            if not str(delivery["receptor_nombre"] or "").strip() or not str(delivery["receptor_documento"] or "").strip() or not str(delivery["receptor_parentesco"] or "").strip():
                raise ValueError("Identidad y parentesco confirmado del receptor son obligatorios.")
            items = conn.execute("SELECT * FROM icbf_program_delivery_items WHERE delivery_id=? AND fundacion_id=?", (delivery_id, fundacion_id)).fetchall()
            if not items or any(not str(item["producto"] or "").strip() or not str(item["lote"] or "").strip() or float(item["unidades"] or 0) <= 0 for item in items):
                raise ValueError("Cada ítem confirmado requiere producto, lote y unidades mayores que cero.")
            active = conn.execute("SELECT id FROM icbf_program_deliveries WHERE fundacion_id=? AND activity_link_id=? AND participant_id=? AND estado='CONFIRMADA'", (fundacion_id, delivery["activity_link_id"], delivery["participant_id"])).fetchone()
            replaces = int(delivery["replaces_delivery_id"] or 0) or None
            if active and int(active["id"]) != replaces:
                raise ValueError("Ya existe una entrega confirmada; indica explícitamente cuál reemplaza.")
            now = now_iso()
            if replaces:
                cur = conn.execute("UPDATE icbf_program_deliveries SET estado='REEMPLAZADA',actualizado_en=? WHERE id=? AND fundacion_id=? AND estado='CONFIRMADA'", (now, replaces, fundacion_id))
                if not cur.rowcount:
                    raise ValueError("La entrega reemplazada no existe o no está confirmada.")
            conn.execute("UPDATE icbf_program_deliveries SET estado='CONFIRMADA',confirmado_por=?,confirmado_en=?,actualizado_en=? WHERE id=? AND fundacion_id=?", (user_id, now, now, delivery_id, fundacion_id))
            link = conn.execute("SELECT profile_id,load_id FROM icbf_program_activity_links WHERE id=? AND fundacion_id=?", (delivery["activity_link_id"], fundacion_id)).fetchone()
            self._audit(conn, fundacion_id, link["profile_id"], link["load_id"], user_id, "ENTREGA_CONFIRMADA", {"delivery_id": delivery_id, "replaces_delivery_id": replaces})
            conn.commit()
            return self.delivery_detail(fundacion_id, delivery_id, conn=conn)

    def delivery_detail(self, fundacion_id: int, delivery_id: int, conn=None) -> dict:
        own = conn is None
        conn = conn or self.connect()
        try:
            row = conn.execute("SELECT * FROM icbf_program_deliveries WHERE id=? AND fundacion_id=?", (delivery_id, fundacion_id)).fetchone()
            if not row:
                raise ValueError("Entrega no encontrada.")
            data = dict(row)
            data["items"] = [dict(item) for item in conn.execute("SELECT * FROM icbf_program_delivery_items WHERE delivery_id=? AND fundacion_id=? ORDER BY id", (delivery_id, fundacion_id)).fetchall()]
            return data
        finally:
            if own:
                conn.close()

    def confirmed_delivery_facts(self, fundacion_id: int, activity_link_id: int, load_id: int, community_id: int) -> dict[int, dict]:
        with self.connect() as conn:
            link = conn.execute("SELECT id FROM icbf_program_activity_links WHERE id=? AND fundacion_id=? AND load_id=? AND community_id=?", (activity_link_id, fundacion_id, load_id, community_id)).fetchone()
            if not link:
                raise ValueError("La actividad vinculada no pertenece a la carga y comunidad seleccionadas.")
            rows = conn.execute("""SELECT d.* FROM icbf_program_deliveries d
                JOIN icbf_program_participants p ON p.id=d.participant_id AND p.fundacion_id=d.fundacion_id
                WHERE d.fundacion_id=? AND d.activity_link_id=? AND d.estado='CONFIRMADA'
                AND p.load_id=? AND p.community_id=?""", (fundacion_id, activity_link_id, load_id, community_id)).fetchall()
            facts = {}
            for row in rows:
                item = dict(row)
                item["items"] = [dict(product) for product in conn.execute("SELECT producto,lote,unidades,unidad_medida FROM icbf_program_delivery_items WHERE fundacion_id=? AND delivery_id=? ORDER BY id", (fundacion_id, row["id"])).fetchall()]
                facts[int(row["participant_id"])] = item
            return facts

    @staticmethod
    def _quality(prepared: list[dict]) -> dict:
        seen = {}
        missing_document = 0
        missing_responsible_type = 0
        for item in prepared:
            data = item["canonical"]
            if not item["key_present"]:
                missing_document += 1
            else:
                seen[item["key_hash"]] = seen.get(item["key_hash"], 0) + 1
            if not data.get("acudiente.tipo_responsable"):
                missing_responsible_type += 1
        return {
            "total": len(prepared),
            "missing_document": missing_document,
            "missing_responsible_type": missing_responsible_type,
            "duplicate_key_groups": sum(1 for count in seen.values() if count > 1),
            "community_pending": len(prepared),
        }

    @staticmethod
    def _profile(row) -> dict:
        data = dict(row)
        data["configuracion"] = json.loads(data.pop("configuracion_json") or "{}")
        return data

    @staticmethod
    def _generation(row) -> dict:
        data = dict(row)
        data["archivos"] = json.loads(data.pop("archivos_json") or "[]")
        data["pendientes"] = json.loads(data.pop("pendientes_json") or "[]")
        return data

    @staticmethod
    def _audit(conn, fundacion_id, profile_id, load_id, user_id, event, detail) -> None:
        conn.execute("INSERT INTO icbf_program_audit(fundacion_id,profile_id,load_id,usuario_id,evento,detalle_json,creado_en) VALUES(?,?,?,?,?,?,?)", (fundacion_id, profile_id, load_id, user_id, event, json.dumps(detail, ensure_ascii=False, default=str), now_iso()))
