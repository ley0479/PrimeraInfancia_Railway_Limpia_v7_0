from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from openpyxl.utils.cell import get_column_letter, range_boundaries

from modules.dbapi_compat import sqlite3
from modules.seguridad.tenant_context import tenant_path

from .f23_schema import F23_SCHEMA_SQL


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _parse(value: Any, default):
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value or "")
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


def _norm(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class F23Service:
    CODE = "F23.MO12.PP"
    VERSION = "2"
    REGISTER_SHEETS = ("BD-M1", "BD-M2", "BD-M3", "BD-M3 Integrantes")
    YES_NO_FIELDS = {
        "NN-021", "NN-030", "NN-031", "NN-041", "NN-043", "NN-044", "NN-046",
        "MG-008", "MG-024",
    }
    DOCUMENT_TYPES_NN = [
        "1. REGISTRO CIVIL", "2. TARJETA DE IDENTIDAD", "3. PASAPORTE",
        "4. PERMISO ESPECIAL DE PERMANENCIA (PEP)", "5. NO TIENE",
    ]
    DISABILITY_CATEGORIES = [
        "1. Física", "2. Intelectual", "3. Psicosocial", "4. Auditiva", "5. Visual",
        "6. Sordoceguera", "7. Múltiple", "8. Sensorial (gusto, olfato, tacto)",
        "9. Sistémica", "10. Voz y habla", "11. Piel, pelo y uñas", "12. Ninguna",
    ]
    SLEEP_OPTIONS = ["1. Hamaca", "2. Cama", "3. Colchoneta", "4. Estera", "5. Cuna", "6. Plancha", "7. Otro"]
    COLOMBIA_DEPARTMENTS = [
        "AMAZONAS", "ANTIOQUIA", "ARAUCA", "ATLÁNTICO", "BOGOTÁ D.C.", "BOLÍVAR", "BOYACÁ",
        "CALDAS", "CAQUETÁ", "CASANARE", "CAUCA", "CESAR", "CHOCÓ", "CÓRDOBA", "CUNDINAMARCA",
        "GUAINÍA", "GUAVIARE", "HUILA", "LA GUAJIRA", "MAGDALENA", "META", "NARIÑO",
        "NORTE DE SANTANDER", "PUTUMAYO", "QUINDÍO", "RISARALDA", "SAN ANDRÉS",
        "SANTANDER", "SUCRE", "TOLIMA", "VALLE DEL CAUCA", "VAUPÉS", "VICHADA",
    ]

    def __init__(self, database_path: str, output_folder: str):
        self.database_path = str(database_path)
        self.output_folder = Path(output_folder)
        seed = Path(__file__).resolve().parents[2] / "seed_data" / "caracterizacion_f23"
        self.template = seed / "F23_MO12_PP_v2.xlsm"
        self.mapping_path = seed / "mapeo_campos_v2.json"
        self.catalogs_path = seed / "catalogos_ui_v2.json"
        self.mapping = _parse(self.mapping_path.read_text(encoding="utf-8"), {})
        self.catalogs = _parse(self.catalogs_path.read_text(encoding="utf-8"), {}) if self.catalogs_path.is_file() else {}
        self.fields = list(self.mapping.get("fields") or [])

    def connect(self):
        conn = sqlite3.connect(self.database_path, timeout=60)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def init_schema(self):
        with self.connect() as conn:
            conn.executescript(F23_SCHEMA_SQL)
            conn.commit()

    def configuration(self, fundacion_id: int) -> dict[str, Any]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT unidad_servicio unidad,MAX(codigo_unidad) codigo,COUNT(*) total FROM master_ninos WHERE fundacion_id=? AND activo=1 AND COALESCE(unidad_servicio,'')<>'' GROUP BY unidad_servicio ORDER BY unidad_servicio",
                (fundacion_id,),
            ).fetchall()
        return {
            "template": {"codigo": self.CODE, "version": self.VERSION, "disponible": self.template.is_file(), "sha256": _sha(self.template) if self.template.is_file() else None},
            "mapeo": {"disponible": self.mapping_path.is_file(), "campos": len(self.fields)},
            "unidades": [dict(row) for row in rows],
        }

    @staticmethod
    def _pick(source: dict[str, Any], *names):
        flat = {_norm(key): value for key, value in source.items() if value not in (None, "")}
        for name in names:
            value = flat.get(_norm(name))
            if value not in (None, ""):
                return value
        return None

    def _prefill(self, field: dict[str, Any], source: dict[str, Any], reference_date: str) -> Any:
        label = _norm(field.get("field"))
        if "fecha de diligenciamiento" in label:
            return reference_date
        if re.fullmatch(r"\d+ edad", label):
            birth = self._pick(source, "fecha_nacimiento", "fecha nacimiento")
            try:
                born, reference = date.fromisoformat(str(birth)[:10]), date.fromisoformat(reference_date)
                if born > reference:
                    return None
                months = (reference.year - born.year) * 12 + reference.month - born.month - (reference.day < born.day)
                return f"{months // 12} años, {months % 12} meses"
            except (TypeError, ValueError):
                return None
        rules = (
            (("regional",), ("regional", "nombre regional", "regional uds")),
            (("centro zonal",), ("centro_zonal", "centro zonal", "nombre centro zonal")),
            (("nombre agente educativo",), ("docente", "agente educativo", "nombre agente educativo")),
            (("usuario",), ("usuario", "tipo usuario", "tipo de usuario")),
            (("pais de nacimiento",), ("pais_nacimiento", "pais de nacimiento")),
            (("nacionalidad principal",), ("nacionalidad", "nacionalidad principal")),
            (("segunda nacionalidad",), ("segunda_nacionalidad", "segunda nacionalidad")),
            (("departamento de residencia",), ("departamento", "departamento residencia")),
            (("municipio de residencia",), ("municipio", "municipio residencia")),
            (("numero celular acudiente",), ("telefono_acudiente", "celular acudiente", "telefono")),
            (("codigo cuentame", "codigo de la uds", "codigo uds"), ("codigo_unidad", "codigo uds", "codigo cuentame uds")),
            (("fecha de nacimiento",), ("fecha_nacimiento", "fecha nacimiento")),
            (("tipo de documento",), ("tipo_documento", "tipo documento")),
            (("numero de documento", "documento del participante", "identificacion"), ("documento", "numero documento", "identificacion")),
            (("primer nombre",), ("primer_nombre", "primer nombre")),
            (("segundo nombre",), ("segundo_nombre", "segundo nombre")),
            (("primer apellido",), ("primer_apellido", "primer apellido")),
            (("segundo apellido",), ("segundo_apellido", "segundo apellido")),
            (("nombres", "nombre del usuario"), ("nombres", "nombre_completo", "nombre completo")),
            (("apellidos",), ("apellidos",)),
            (("sexo",), ("sexo",)),
            (("unidad de servicio", "nombre uds"), ("unidad_servicio", "unidad", "unidad nombre")),
            (("modalidad",), ("modalidad",)),
            (("vacun",), ("vacunas",)),
            (("crecimiento",), ("control_crecimiento", "carne_crecimiento")),
            (("peso",), ("peso",)),
            (("talla",), ("talla",)),
        )
        for fragments, aliases in rules:
            if any(fragment in label for fragment in fragments):
                return self._pick(source, *aliases)
        return None

    def _previous_confirmed_answers(self, conn, fundacion_id: int, participant_id: int) -> dict[str, Any]:
        rows = conn.execute(
            """SELECT p.respuestas_json,p.estados_json
               FROM f23_participantes p
               JOIN f23_sesiones s ON s.id=p.sesion_id AND s.fundacion_id=p.fundacion_id
               WHERE p.fundacion_id=? AND p.participante_id=?
               ORDER BY s.fecha_referencia DESC,p.id DESC""",
            (fundacion_id, participant_id),
        ).fetchall()
        recovered: dict[str, Any] = {}
        for row in rows:
            answers = _parse(row["respuestas_json"], {})
            states = _parse(row["estados_json"], {})
            for field_id, value in answers.items():
                if field_id not in recovered and value not in (None, "") and states.get(field_id) == "CONFIRMADO":
                    recovered[field_id] = value
        return recovered

    def _field_applies(self, field: dict[str, Any], answers: dict[str, Any]) -> bool:
        ui = self._field_ui(field)
        parent = ui.get("depends_on")
        expected = ui.get("show_when") or []
        if not parent or not expected:
            return True
        current = _norm(answers.get(str(parent)))
        return bool(current) and current in {_norm(value) for value in expected}

    def _pending_fields(self, answers: dict[str, Any], states: dict[str, Any]) -> list[str]:
        pending = []
        for field in self.fields:
            field_id = str(field.get("id"))
            if field.get("mode") in {"AUXILIAR", "NO_ESCRIBIR"} or not self._field_applies(field, answers):
                continue
            if states.get(field_id) not in {"CONFIRMADO", "NO_APLICA", "NO_RESPONDE"}:
                pending.append(field_id)
        return pending

    def create_session(self, fundacion_id: int, unit: str, reference_date: str, user_id: int | None) -> dict[str, Any]:
        unit = str(unit or "").strip()
        if not unit:
            raise ValueError("Selecciona una unidad de servicio.")
        try:
            date.fromisoformat(reference_date)
        except (TypeError, ValueError):
            raise ValueError("La fecha de referencia debe usar AAAA-MM-DD.")
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM master_ninos WHERE fundacion_id=? AND activo=1 AND UPPER(unidad_servicio)=UPPER(?) ORDER BY apellidos,nombres,documento", (fundacion_id, unit)).fetchall()
            if not rows:
                raise ValueError("La unidad seleccionada no tiene participantes activos en la Base Maestra publicada.")
            snapshots = []
            for row in rows:
                data = dict(row)
                data.update(_parse(data.get("datos_json"), {}))
                snapshots.append(data)
            snapshot_hash = hashlib.sha256(_json([{k: v for k, v in item.items() if k != "datos_json"} for item in snapshots]).encode()).hexdigest()
            now = _now()
            cursor = conn.execute("INSERT INTO f23_sesiones(fundacion_id,unidad,codigo_unidad,fecha_referencia,total_participantes,snapshot_hash,creado_por,fecha_creacion,fecha_actualizacion) VALUES(?,?,?,?,?,?,?,?,?)", (fundacion_id, unit, self._pick(snapshots[0], "codigo_unidad"), reference_date, len(snapshots), snapshot_hash, user_id, now, now))
            session_id = int(cursor.lastrowid)
            for source in snapshots:
                answers = {}
                states = {}
                previous = self._previous_confirmed_answers(conn, fundacion_id, int(source["id"]))
                for field in self.fields:
                    value = self._prefill(field, source, reference_date)
                    field_id = str(field.get("id"))
                    if value not in (None, ""):
                        answers[field_id] = value
                        states[field_id] = "EXISTENTE_POR_VALIDAR"
                    elif previous.get(field_id) not in (None, ""):
                        answers[field_id] = previous[field_id]
                        states[field_id] = "ANTERIOR_POR_CONFIRMAR"
                pending = self._pending_fields(answers, states)
                full_name = source.get("nombre_completo") or " ".join(filter(None, [source.get("nombres"), source.get("apellidos")])).strip()
                conn.execute("INSERT INTO f23_participantes(fundacion_id,sesion_id,participante_id,documento,nombre_completo,tipo_ficha,fuente_snapshot_json,respuestas_json,estados_json,pendientes_json,integrantes_json,fecha_actualizacion) VALUES(?,?,?,?,?,'NN',?,?,?,?, '[]',?)", (fundacion_id, session_id, int(source["id"]), str(source.get("documento") or ""), full_name, _json(source), _json(answers), _json(states), _json(pending), now))
            conn.execute("INSERT INTO f23_auditoria(fundacion_id,sesion_id,usuario_id,accion,detalle_json,fecha) VALUES(?,?,?,?,?,?)", (fundacion_id, session_id, user_id, "CREAR_SESION", _json({"unidad": unit, "participantes": len(snapshots)}), now))
            conn.commit()
        return self.session(fundacion_id, session_id)

    def list_sessions(self, fundacion_id: int) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM f23_sesiones WHERE fundacion_id=? ORDER BY id DESC", (fundacion_id,)).fetchall()
            result = []
            for row in rows:
                item = dict(row)
                pending_rows = conn.execute("SELECT pendientes_json FROM f23_participantes WHERE sesion_id=? AND fundacion_id=?", (item["id"], fundacion_id)).fetchall()
                item["completos"] = sum(1 for value in pending_rows if not _parse(value[0], []))
                result.append(item)
            return result

    def session(self, fundacion_id: int, session_id: int) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM f23_sesiones WHERE id=? AND fundacion_id=?", (session_id, fundacion_id)).fetchone()
            if not row:
                raise LookupError("Sesión de caracterización no encontrada.")
            participants = conn.execute("SELECT id,participante_id,documento,nombre_completo,tipo_ficha,respuestas_json,estados_json,pendientes_json,integrantes_json,estado,fecha_actualizacion FROM f23_participantes WHERE sesion_id=? AND fundacion_id=? ORDER BY nombre_completo", (session_id, fundacion_id)).fetchall()
        data = dict(row)
        data["participantes"] = []
        for item in participants:
            value = dict(item)
            for key, default in (("respuestas_json", {}), ("estados_json", {}), ("pendientes_json", []), ("integrantes_json", [])):
                value[key.replace("_json", "")] = _parse(value.pop(key), default)
            value["pendientes_total"] = len(value["pendientes"])
            value["precargados_total"] = sum(1 for state in value["estados"].values() if state == "EXISTENTE_POR_VALIDAR")
            value["recuperados_total"] = sum(1 for state in value["estados"].values() if state == "ANTERIOR_POR_CONFIRMAR")
            value["aplicables_total"] = sum(1 for field in self.fields if field.get("mode") not in {"AUXILIAR", "NO_ESCRIBIR"} and self._field_applies(field, value["respuestas"]))
            value["resueltos_total"] = value["aplicables_total"] - value["pendientes_total"]
            data["participantes"].append(value)
        return data

    def _field_ui(self, field: dict[str, Any]) -> dict[str, Any]:
        field_id = str(field.get("id"))
        label = _norm(field.get("field"))
        ui: dict[str, Any] = {"control": "textarea", "section": "Familia y vivienda" if field_id.startswith("FAM-") else "Identificación y atenciones"}
        if "fecha" in label:
            ui["control"] = "date"
        if field_id in self.YES_NO_FIELDS:
            ui.update(control="select", options=["SI", "NO"])
        if field_id in {"NN-002", "MG-002"}:
            ui.update(control="select", catalog_key="regionales")
        elif field_id in {"NN-003", "MG-003"}:
            ui.update(control="select", catalog_key="regional_centros", depends_on="NN-002" if field_id == "NN-003" else "MG-002")
        elif field_id in {"NN-013", "MG-021"}:
            ui.update(control="select", catalog_key="departamentos")
        elif field_id in {"NN-014", "MG-022"}:
            ui.update(control="select", catalog_key="departamento_municipios", depends_on="NN-013" if field_id == "NN-014" else "MG-021")
        elif field_id in {"NN-016", "MG-011"}:
            ui.update(control="select", options=self.DOCUMENT_TYPES_NN)
        elif field_id in {"NN-020", "MG-015"}:
            ui.update(control="select", options=["1. MUJER", "2. HOMBRE", "3. INTERSEXUAL"])
        elif field_id in {"NN-022", "MG-025"}:
            ui.update(control="select", options=self.DISABILITY_CATEGORIES, depends_on="NN-021" if field_id == "NN-022" else "MG-024", show_when=["SI"])
        elif field_id == "NN-028":
            ui.update(control="select", options=self.SLEEP_OPTIONS)
        elif field_id == "NN-029":
            ui.update(depends_on="NN-028", show_when=["7. Otro"])
        elif field_id in {"NN-024", "NN-025", "NN-026", "MG-027"}:
            ui.update(control="select", catalog_key="lenguas")
        official_choices = {
            "NN-032": ["AFILIADO", "NO_AFILIADO"],
            "NN-035": ["ESQUEMA_COMPLETO", "ESQUEMA_INCOMPLETO"],
            "NN-038": ["CON_ATENCIÓN_SALUD_BUCAL", "SIN_ATENCIÓN_SALUD_BUCAL"],
            "NN-050": ["RECIBE_LECHE_MATERNA", "NO_RECIBE_LECHE_MATERNA"],
            "NN-053": ["SI_EXCLUSIVAMENTE_LECHE_MATERNA", "NO_OTROS_ALIMENTOS"],
            "NN-056": ["SI_LECHE_MATERNA_EXCLUSIVA", "NO_LECHE_MATERNA_EXCLUSIVA"],
        }
        if field_id in official_choices:
            ui.update(control="select", options=official_choices[field_id])
        dependencies = {
            "NN-033": ("NN-032", ["NO_AFILIADO"]),
            "NN-034": ("NN-033", ["6. Otra"]),
            "NN-036": ("NN-035", ["ESQUEMA_INCOMPLETO"]),
            "NN-037": ("NN-036", ["7. Otra"]),
            "NN-039": ("NN-038", ["SIN_ATENCIÓN_SALUD_BUCAL"]),
            "NN-040": ("NN-039", ["6. Otro"]),
            "NN-045": ("NN-044", ["SI"]),
            "NN-047": ("NN-046", ["SI"]),
            "NN-048": ("NN-046", ["NO"]),
            "NN-051": ("NN-050", ["NO_RECIBE_LECHE_MATERNA"]),
            "NN-052": ("NN-051", ["8. Otro"]),
            "NN-054": ("NN-053", ["NO_OTROS_ALIMENTOS"]),
            "NN-055": ("NN-053", ["NO_OTROS_ALIMENTOS"]),
            "NN-057": ("NN-056", ["NO_LECHE_MATERNA_EXCLUSIVA"]),
            "NN-058": ("NN-057", ["8. Otro"]),
        }
        if field_id in dependencies:
            parent, values = dependencies[field_id]
            ui.update(depends_on=parent, show_when=values)
        if field_id in {"NN-002", "NN-003", "NN-004", "NN-005", "NN-006", "NN-007", "MG-002", "MG-003", "MG-004", "MG-005", "MG-006", "MG-007"}:
            ui["section"] = "Datos institucionales"
        elif field_id.startswith("NN-") and int(field_id.split("-")[1]) >= 21:
            ui["section"] = "Salud, cuidado y alimentación"
        return ui

    def field_catalog(self) -> list[dict[str, Any]]:
        result = []
        for field in self.fields:
            item = {key: field.get(key) for key in ("id", "sheet", "field", "mode", "rule", "missing_action")}
            item.update(self._field_ui(field))
            result.append(item)
        return result

    def ui_catalogs(self) -> dict[str, Any]:
        return self.catalogs

    def update_participant(self, fundacion_id: int, record_id: int, payload: dict[str, Any], user_id: int | None) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM f23_participantes WHERE id=? AND fundacion_id=?", (record_id, fundacion_id)).fetchone()
            if not row:
                raise LookupError("Participante de caracterización no encontrado.")
            answers = _parse(row["respuestas_json"], {})
            states = _parse(row["estados_json"], {})
            allowed = {str(field.get("id")) for field in self.fields}
            for field_id, value in (payload.get("respuestas") or {}).items():
                if field_id not in allowed:
                    continue
                state = str((payload.get("estados") or {}).get(field_id) or "CONFIRMADO").upper()
                if state not in {"CONFIRMADO", "PENDIENTE", "NO_APLICA", "NO_RESPONDE", "CONFLICTO", "EXISTENTE_POR_VALIDAR", "ANTERIOR_POR_CONFIRMAR"}:
                    raise ValueError(f"Estado no permitido para {field_id}.")
                if value in (None, "") and state == "CONFIRMADO":
                    state = "PENDIENTE"
                answers[field_id] = value
                states[field_id] = state
            pending = self._pending_fields(answers, states)
            members = payload.get("integrantes", _parse(row["integrantes_json"], []))
            if len(members) > 10:
                raise ValueError("El formato oficial admite máximo diez integrantes. No se truncaron datos; se requiere una salida institucional aprobada.")
            state = "COMPLETO" if not pending else "BORRADOR"
            now = _now()
            conn.execute("UPDATE f23_participantes SET tipo_ficha=?,respuestas_json=?,estados_json=?,pendientes_json=?,integrantes_json=?,estado=?,fecha_actualizacion=? WHERE id=? AND fundacion_id=?", (str(payload.get("tipo_ficha") or row["tipo_ficha"]).upper(), _json(answers), _json(states), _json(pending), _json(members), state, now, record_id, fundacion_id))
            conn.execute("UPDATE f23_sesiones SET fecha_actualizacion=? WHERE id=? AND fundacion_id=?", (now, row["sesion_id"], fundacion_id))
            conn.execute("INSERT INTO f23_auditoria(fundacion_id,sesion_id,participante_registro_id,usuario_id,accion,detalle_json,fecha) VALUES(?,?,?,?,?,?,?)", (fundacion_id, row["sesion_id"], record_id, user_id, "GUARDAR_RESPUESTAS", _json({"estado": state, "pendientes": len(pending)}), now))
            conn.commit()
        return next(item for item in self.session(fundacion_id, int(row["sesion_id"]))["participantes"] if int(item["id"]) == record_id)

    def participant_context(self, fundacion_id: int, record_id: int) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute("SELECT p.id,p.sesion_id,s.unidad FROM f23_participantes p JOIN f23_sesiones s ON s.id=p.sesion_id AND s.fundacion_id=p.fundacion_id WHERE p.id=? AND p.fundacion_id=?", (record_id, fundacion_id)).fetchone()
            if not row:
                raise LookupError("Participante de caracterización no encontrado.")
            return dict(row)

    def _register_values(self, participant: dict[str, Any], row_number: int = 2) -> tuple[str, dict[str, Any]]:
        answers = participant["respuestas"]
        target = "BD-M2" if participant.get("tipo_ficha") == "MG" else "BD-M1"
        values = {}
        for field in self.fields:
            if field.get("sheet") != target:
                continue
            coordinate = str(field.get("header_cell") or "")
            match = re.match(r"([A-Z]+)1$", coordinate)
            if match:
                values[f"{match.group(1)}{row_number}"] = answers.get(str(field.get("id")))
        return target, values

    def _capture_values(self, participant: dict[str, Any]) -> dict[str, dict[str, Any]]:
        answers = participant["respuestas"]
        result: dict[str, dict[str, Any]] = {}
        for field in self.fields:
            value = answers.get(str(field.get("id")))
            if value in (None, ""):
                continue
            for reference in str(field.get("capture") or "").split(";"):
                match = re.search(r"([^!;]+)!\$?([A-Z]+)\$?(\d+)(?::\$?([A-Z]+)\$?(\d+))?", reference.strip())
                if match:
                    result.setdefault(match.group(1), {})[f"{match.group(2)}{match.group(3)}"] = value
        return result

    def _blank_capture_values(self) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for field in self.fields:
            for reference in str(field.get("capture") or "").split(";"):
                match = re.search(r"([^!;]+)!\$?([A-Z]+)\$?(\d+)(?::\$?([A-Z]+)\$?(\d+))?", reference.strip())
                if not match:
                    continue
                sheet = match.group(1)
                start = f"{match.group(2)}{match.group(3)}"
                end = f"{match.group(4)}{match.group(5)}" if match.group(4) else start
                min_col, min_row, max_col, max_row = range_boundaries(f"{start}:{end}")
                for row in range(min_row, max_row + 1):
                    for column in range(min_col, max_col + 1):
                        result.setdefault(sheet, {})[f"{get_column_letter(column)}{row}"] = None
        return result

    @staticmethod
    def _sheet_paths(archive: zipfile.ZipFile) -> dict[str, str]:
        main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
        rel_doc = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        package = "http://schemas.openxmlformats.org/package/2006/relationships"
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {item.attrib["Id"]: item.attrib["Target"] for item in relationships.findall(f"{{{package}}}Relationship")}
        result = {}
        for sheet in workbook.findall(f".//{{{main}}}sheet"):
            target = targets.get(sheet.attrib.get(f"{{{rel_doc}}}id"), "")
            if target:
                result[sheet.attrib["name"]] = "xl/" + target.lstrip("/")
        return result

    @staticmethod
    def _patch_sheet(xml: bytes, values: dict[str, Any], clear_from_row: int | None = None) -> bytes:
        namespace = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
        ET.register_namespace("", namespace)
        root = ET.fromstring(xml)
        sheet_data = root.find(f"{{{namespace}}}sheetData")
        if sheet_data is None:
            return xml
        rows = {int(row.attrib.get("r", "0")): row for row in sheet_data.findall(f"{{{namespace}}}row")}
        if clear_from_row is not None:
            for number, row in rows.items():
                if number < clear_from_row:
                    continue
                for cell in row.findall(f"{{{namespace}}}c"):
                    for child in list(cell):
                        if child.tag in {f"{{{namespace}}}v", f"{{{namespace}}}f", f"{{{namespace}}}is"}:
                            cell.remove(child)
                    cell.attrib.pop("t", None)
        for coordinate, value in values.items():
            match = re.match(r"[A-Z]+(\d+)$", coordinate)
            if not match:
                continue
            row_number = int(match.group(1))
            row = rows.get(row_number)
            if row is None:
                row = ET.Element(f"{{{namespace}}}row", {"r": str(row_number)})
                sheet_data.append(row);rows[row_number] = row
            cell = next((item for item in row.findall(f"{{{namespace}}}c") if item.attrib.get("r") == coordinate), None)
            if cell is None:
                cell = ET.Element(f"{{{namespace}}}c", {"r": coordinate})
                row.append(cell)
            for child in list(cell):
                if child.tag in {f"{{{namespace}}}v", f"{{{namespace}}}f", f"{{{namespace}}}is"}:
                    cell.remove(child)
            if value in (None, ""):
                cell.attrib.pop("t", None)
                continue
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                cell.attrib.pop("t", None)
                ET.SubElement(cell, f"{{{namespace}}}v").text = str(value)
            else:
                cell.attrib["t"] = "inlineStr"
                inline = ET.SubElement(cell, f"{{{namespace}}}is")
                text = ET.SubElement(inline, f"{{{namespace}}}t")
                text.text = str(value)
                if str(value).startswith(" ") or str(value).endswith(" "):
                    text.attrib["{http://www.w3.org/XML/1998/namespace}space"] = "preserve"
        return ET.tostring(root, encoding="utf-8", xml_declaration=True)

    def _write_preserving_package(self, output: Path, writes: dict[str, dict[str, Any]]):
        temporary = output.with_suffix(".tmp.xlsm")
        with zipfile.ZipFile(self.template, "r") as source:
            paths = self._sheet_paths(source)
            with zipfile.ZipFile(temporary, "w") as target:
                for info in source.infolist():
                    content = source.read(info.filename)
                    sheet_name = next((name for name, path in paths.items() if path == info.filename), None)
                    if sheet_name in writes or sheet_name in self.REGISTER_SHEETS:
                        content = self._patch_sheet(content, writes.get(sheet_name, {}), 2 if sheet_name in self.REGISTER_SHEETS else None)
                    target.writestr(info, content)
        temporary.replace(output)

    def generate(self, fundacion_id: int, session_id: int, user_id: int | None, participant_record_id: int | None = None) -> dict[str, Any]:
        if not self.template.is_file():
            raise ValueError("La plantilla F23 no está instalada.")
        session = self.session(fundacion_id, session_id)
        participants = session["participantes"]
        if participant_record_id:
            participants = [item for item in participants if int(item["id"]) == int(participant_record_id)]
            if not participants:
                raise LookupError("El participante no pertenece a esta sesión.")
        root = Path(tenant_path(self.output_folder, "caracterizacion_f23", str(session_id)))
        root.mkdir(parents=True, exist_ok=True)
        writes: dict[str, dict[str, Any]] = self._blank_capture_values()
        if participant_record_id:
            participant = participants[0]
            target, values = self._register_values(participant)
            writes.setdefault(target, {}).update(values)
            for sheet, cells in self._capture_values(participant).items():
                writes.setdefault(sheet, {}).update(cells)
            filename = f"F23_{participant['tipo_ficha']}_{participant['documento'] or participant['id']}.xlsm"
            generation_type = "INDIVIDUAL"
        else:
            row_by_sheet = {"BD-M1": 2, "BD-M2": 2}
            for participant in participants:
                target = "BD-M2" if participant.get("tipo_ficha") == "MG" else "BD-M1"
                _, values = self._register_values(participant, row_by_sheet[target])
                writes.setdefault(target, {}).update(values)
                row_by_sheet[target] += 1
            filename = f"F23_{re.sub(r'[^A-Za-z0-9_-]+', '_', session['unidad'])}_{session['fecha_referencia']}.xlsm"
            generation_type = "CONSOLIDADO"
        output = root / filename
        self._write_preserving_package(output, writes)
        digest = _sha(output)
        now = _now()
        with self.connect() as conn:
            cursor = conn.execute("INSERT INTO f23_generaciones(fundacion_id,sesion_id,participante_registro_id,tipo,nombre_archivo,ruta_archivo,sha256,detalle_json,creado_por,fecha_creacion) VALUES(?,?,?,?,?,?,?,?,?,?)", (fundacion_id, session_id, participant_record_id, generation_type, filename, str(output.resolve()), digest, _json({"participantes": len(participants), "pendientes": sum(item["pendientes_total"] for item in participants), "borrador": any(item["pendientes_total"] for item in participants)}), user_id, now))
            generation_id = int(cursor.lastrowid)
            conn.execute("INSERT INTO f23_auditoria(fundacion_id,sesion_id,participante_registro_id,usuario_id,accion,detalle_json,fecha) VALUES(?,?,?,?,?,?,?)", (fundacion_id, session_id, participant_record_id, user_id, "GENERAR_XLSM", _json({"generacion_id": generation_id, "tipo": generation_type, "sha256": digest}), now))
            conn.commit()
        return {"id": generation_id, "tipo": generation_type, "nombre_archivo": filename, "sha256": digest, "participantes": len(participants), "borrador": any(item["pendientes_total"] for item in participants), "descarga": f"/api/psicosocial/f23/generaciones/{generation_id}/descargar"}

    def generation(self, fundacion_id: int, generation_id: int) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute("SELECT g.*,s.unidad FROM f23_generaciones g JOIN f23_sesiones s ON s.id=g.sesion_id AND s.fundacion_id=g.fundacion_id WHERE g.id=? AND g.fundacion_id=?", (generation_id, fundacion_id)).fetchone()
            if not row:
                raise LookupError("Archivo F23 no encontrado.")
            return dict(row)
