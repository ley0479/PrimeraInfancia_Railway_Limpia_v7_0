from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from modules.dbapi_compat import sqlite3
from modules.importaciones_universales.schema import SCHEMA_SQL as IMPORT_SCHEMA
from modules.programas_icbf.repository import ProgramasIcbfRepository
from modules.calendario_inteligente.repository import CalendarioInteligenteRepository


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def prepare(db: str, tenant: int = 1):
    now = "2026-09-30T00:00:00+00:00"
    canonical = {
        "participante.tipo_documento": "RC",
        "participante.numero_documento": "SINTETICO-1",
        "participante.primer_nombre": "ANA",
        "participante.primer_apellido": "PRUEBA",
    }
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        conn.executescript(IMPORT_SCHEMA)
        cur = conn.execute("""INSERT INTO importaciones_universales
          (tenant_id,nombre_archivo,nombre_guardado,tipo_archivo,hash_sha256,estado,porcentaje,etapa_actual,resultado_json,creado_en,actualizado_en)
          VALUES(?,?,?,?,?,'LISTO_PARA_IMPORTAR',90,'Validación completada','{}',?,?)""", (tenant, "sintetica.xlsx", "sintetica.xlsx", ".xlsx", hashlib.sha256(str(tenant).encode()).hexdigest(), now, now))
        import_id = int(cur.lastrowid)
        normalized = json.dumps({"canonical": canonical, "provenance": {}}, ensure_ascii=False)
        conn.execute("INSERT INTO importaciones_filas_staging(importacion_id,tenant_id,numero_fila,hash_fila,original_json,normalizado_json) VALUES(?,?,?,?,?,?)", (import_id, tenant, 2, hashlib.sha256(normalized.encode()).hexdigest(), "{}", normalized))
        conn.execute("CREATE TABLE IF NOT EXISTS sn_actividades_integrales(id INTEGER PRIMARY KEY AUTOINCREMENT,fundacion_id INTEGER NOT NULL,titulo TEXT,fecha_programada TEXT,responsable_id INTEGER,responsable_nombre TEXT,unidad_nombre TEXT)")
        cur = conn.execute("INSERT INTO sn_actividades_integrales(fundacion_id,titulo,fecha_programada,responsable_id,responsable_nombre,unidad_nombre) VALUES(?,?,?,?,?,?)", (tenant, "Actividad sintética", "2026-09-30", 11, "RESPONSABLE", "UDS SINTÉTICA"))
        activity_id = int(cur.lastrowid)
        conn.commit()
    repo = ProgramasIcbfRepository(db)
    repo.init_schema()
    profile = repo.ensure_profile(tenant, tenant)
    load = repo.create_snapshot(tenant, profile["id"], import_id, tenant)
    community = repo.create_community(tenant, profile["id"], "Comunidad sintética", "CS", tenant)
    participant = repo.list_participants(tenant, load["id"], True)[0]
    repo.assign_community(tenant, load["id"], participant["id"], community["id"], tenant, "Prueba")
    return repo, profile, load, community, participant, activity_id


def main():
    with tempfile.TemporaryDirectory() as temporary:
        db = str(Path(temporary) / "programas.sqlite3")
        repo, profile, load, community, participant, activity_id = prepare(db)
        point = repo.save_delivery_point(1, profile["id"], {"codigo": "P-1", "nombre": "Punto uno", "tipo": "UDS", "direccion": "Dirección sintética"}, 11)
        same_point = repo.save_delivery_point(1, profile["id"], {"codigo": "P-1", "nombre": "Punto uno", "tipo": "UDS", "direccion": "Dirección sintética"}, 11)
        require(point["id"] == same_point["id"], "Duplicó una versión de punto sin cambios")
        point_v2 = repo.save_delivery_point(1, profile["id"], {"codigo": "P-1", "nombre": "Punto uno", "tipo": "UDS", "direccion": "Dirección actualizada"}, 11)
        require(point_v2["version"] == 2 and point_v2["id"] != point["id"], "No versionó el punto de entrega")
        link = repo.link_health_activity(1, profile["id"], load["id"], community["id"], activity_id, "2026-09", point_v2["id"], 11)
        same_link = repo.link_health_activity(1, profile["id"], load["id"], community["id"], activity_id, "2026-09", point_v2["id"], 11)
        require(link["id"] == same_link["id"], "Duplicó la vinculación operativa")
        calendar_payload = repo.calendar_payload(1, link["id"])
        calendar = CalendarioInteligenteRepository(db); calendar.init_schema()
        event = calendar.create_entregable(calendar_payload, origen="programas_icbf")
        require(event["clave_unica"] == calendar_payload["clave_unica"] and calendar.find_by_clave(calendar_payload["clave_unica"])["id"] == event["id"], "No reutilizó el calendario existente de forma idempotente")
        incomplete = repo.create_delivery_draft(1, link["id"], participant["id"], {"request_key": "request-incomplete", "modalidad": "COMUNITARIA", "items": []}, 11)
        blocked = False
        try:
            repo.confirm_delivery(1, incomplete["id"], 11)
        except ValueError:
            blocked = True
        require(blocked and repo.delivery_detail(1, incomplete["id"])["estado"] == "BORRADOR", "Confirmó una entrega sin hechos reales")
        payload = {"request_key": "request-real-1", "modalidad": "COMUNITARIA", "fecha_entrega": "2026-09-30", "receptor_nombre": "RECEPTOR SINTÉTICO", "receptor_documento": "DOC-R", "receptor_parentesco": "MADRE", "items": [{"producto": "BIENESTARINA MAS", "lote": "LOTE-1", "unidades": 2, "unidad_medida": "UNIDAD"}]}
        draft = repo.create_delivery_draft(1, link["id"], participant["id"], payload, 11)
        repeated = repo.create_delivery_draft(1, link["id"], participant["id"], payload, 11)
        require(draft["id"] == repeated["id"], "El reintento duplicó la entrega")
        confirmed = repo.confirm_delivery(1, draft["id"], 11)
        require(confirmed["estado"] == "CONFIRMADA", "No confirmó la entrega explícita")
        require(repo.confirm_delivery(1, draft["id"], 11)["id"] == draft["id"], "Confirmación repetida no fue idempotente")
        replacement_payload = {**payload, "request_key": "request-real-2", "modalidad": "HOGAR", "replaces_delivery_id": draft["id"]}
        replacement = repo.create_delivery_draft(1, link["id"], participant["id"], replacement_payload, 11)
        replacement = repo.confirm_delivery(1, replacement["id"], 11)
        require(replacement["estado"] == "CONFIRMADA" and repo.delivery_detail(1, draft["id"])["estado"] == "REEMPLAZADA", "El cambio comunitaria/hogar produjo doble conteo")
        facts = repo.confirmed_delivery_facts(1, link["id"], load["id"], community["id"])
        require(list(facts) == [participant["id"]] and facts[participant["id"]]["id"] == replacement["id"], "La salida no resolvió exclusivamente el hecho confirmado vigente")
        blocked = False
        try:
            repo.delivery_detail(2, replacement["id"])
        except ValueError:
            blocked = True
        require(blocked, "Expuso una entrega a otra fundación")
        print("PASS test_programas_icbf_phase3")


if __name__ == "__main__":
    main()
