from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from modules.dbapi_compat import sqlite3
from modules.importaciones_universales.schema import SCHEMA_SQL as IMPORT_SCHEMA
from modules.programas_icbf.repository import ProgramasIcbfRepository


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def add_import(db: str, tenant: int, rows: list[dict]) -> int:
    now = "2026-09-30T00:00:00+00:00"
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        conn.executescript(IMPORT_SCHEMA)
        digest = hashlib.sha256(f"tenant-{tenant}".encode()).hexdigest()
        cur = conn.execute("""INSERT INTO importaciones_universales
          (tenant_id,nombre_archivo,nombre_guardado,tipo_archivo,hash_sha256,estado,porcentaje,etapa_actual,resultado_json,creado_en,actualizado_en)
          VALUES(?,?,?,?,?,'LISTO_PARA_IMPORTAR',90,'Validación completada','{}',?,?)""",
          (tenant, "sintetica.xlsx", f"sintetica-{tenant}.xlsx", ".xlsx", digest, now, now))
        import_id = int(cur.lastrowid)
        for number, canonical in enumerate(rows, 2):
            raw = json.dumps({"canonical": canonical, "provenance": {}}, ensure_ascii=False)
            cur = conn.execute("INSERT INTO importaciones_filas_staging(importacion_id,tenant_id,numero_fila,hash_fila,original_json,normalizado_json) VALUES(?,?,?,?,?,?)", (import_id, tenant, number, hashlib.sha256(raw.encode()).hexdigest(), "{}", raw))
        conn.commit()
        return import_id


def main():
    with tempfile.TemporaryDirectory() as temporary:
        db = str(Path(temporary) / "programas.sqlite3")
        rows = [
            {"participante.tipo_documento": "RC", "participante.numero_documento": "1001", "participante.primer_nombre": "ANA", "acudiente.tipo_responsable": "MADRE"},
            {"participante.tipo_documento": "RC", "participante.numero_documento": "1001", "participante.primer_nombre": "ANA"},
            {"participante.tipo_documento": "RC", "participante.numero_documento": "1002", "participante.primer_nombre": "LUIS"},
        ]
        import_one = add_import(db, 1, rows)
        import_two = add_import(db, 2, [{"participante.tipo_documento": "RC", "participante.numero_documento": "2001"}])
        repo = ProgramasIcbfRepository(db)
        repo.init_schema()
        profile_one = repo.ensure_profile(1, 11)
        profile_two = repo.ensure_profile(2, 22)
        require(profile_one["estado"] == "INACTIVO", "El perfil piloto debe iniciar inactivo")
        require(profile_one["criterio_orden"] == "PRIMER_NOMBRE", "No conservó la opción B confirmada")
        load = repo.create_snapshot(1, profile_one["id"], import_one, 11)
        require(load["quality"]["total"] == 3, "Conteo incorrecto")
        require(load["quality"]["duplicate_key_groups"] == 1, "No detectó duplicados")
        require(load["quality"]["missing_responsible_type"] == 2, "No detectó responsables pendientes")
        same = repo.create_snapshot(1, profile_one["id"], import_one, 11)
        require(same["id"] == load["id"], "La carga no es idempotente")
        community = repo.create_community(1, profile_one["id"], "Comunidad Norte", "CN", 11)
        participant = repo.list_participants(1, load["id"], True)[0]
        first = repo.assign_community(1, load["id"], participant["id"], community["id"], 11, "Asignación confirmada")
        second = repo.assign_community(1, load["id"], participant["id"], community["id"], 11, "Reconfirmación")
        require(first["version"] == 1 and second["version"] == 2, "No versionó la asignación")
        require(repo.get_load(1, load["id"])["communities"] == {"assigned": 1, "pending": 2}, "Resumen comunitario incorrecto")
        context = repo.generation_context(1, load["id"], community["id"])
        require([item["id"] for item in context["participants"]] == [participant["id"]], "El contexto incluyó participantes de otra comunidad")
        blocked = False
        try:
            repo.create_snapshot(1, profile_one["id"], import_two, 11)
        except ValueError:
            blocked = True
        require(blocked, "Expuso una importación de otra fundación")
        blocked = False
        try:
            repo.assign_community(2, load["id"], participant["id"], community["id"], 22)
        except ValueError:
            blocked = True
        require(blocked, "Permitió asignación cruzada entre fundaciones")
        require(repo.list_profiles(1)[0]["id"] != profile_two["id"], "Mezcló perfiles entre fundaciones")
        print("PASS test_programas_icbf_phase1")


if __name__ == "__main__":
    main()
