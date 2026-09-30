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

    def __init__(self, database_path: str, output_folder: str):
        self.database_path = str(database_path)
        self.output_folder = Path(output_folder)
        seed = Path(__file__).resolve().parents[2] / "seed_data" / "caracterizacion_f23"
        self.template = seed / "F23_MO12_PP_v2.xlsm"
        self.mapping_path = seed / "mapeo_campos_v2.json"
        self.mapping = _parse(self.mapping_path.read_text(encoding="utf-8"), {})
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
        rules = (
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
                pending = []
                for field in self.fields:
                    value = self._prefill(field, source, reference_date)
                    field_id = str(field.get("id"))
                    if value not in (None, ""):
                        answers[field_id] = value
                        states[field_id] = "EXISTENTE_POR_VALIDAR"
                        if field.get("mode") not in {"AUXILIAR", "NO_ESCRIBIR"}:
                            pending.append(field_id)
                    elif field.get("mode") not in {"AUXILIAR", "NO_ESCRIBIR"}:
                        pending.append(field_id)
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
            data["participantes"].append(value)
        return data

    def field_catalog(self) -> list[dict[str, Any]]:
        return [{key: field.get(key) for key in ("id", "sheet", "field", "mode", "rule", "missing_action")} for field in self.fields]

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
                if state not in {"CONFIRMADO", "PENDIENTE", "NO_APLICA", "NO_RESPONDE", "CONFLICTO", "EXISTENTE_POR_VALIDAR"}:
                    raise ValueError(f"Estado no permitido para {field_id}.")
                if value in (None, "") and state == "CONFIRMADO":
                    state = "PENDIENTE"
                answers[field_id] = value
                states[field_id] = state
            applicable = [str(field.get("id")) for field in self.fields if field.get("mode") not in {"AUXILIAR", "NO_ESCRIBIR"}]
            pending = [field_id for field_id in applicable if states.get(field_id) not in {"CONFIRMADO", "NO_APLICA", "NO_RESPONDE"}]
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
