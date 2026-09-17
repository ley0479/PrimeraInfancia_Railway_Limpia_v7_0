#!/usr/bin/env python3
"""Caracterización de vistas Fase 1 y bandeja personal multi-tenant."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from modules.calendario_inteligente.repository import CalendarioInteligenteRepository  # noqa: E402
from modules.seguridad.tenant_context import tenant_context  # noqa: E402


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


def run() -> None:
    frontend = (ROOT / "frontend" / "js" / "modules" / "calendario-inteligente.js").read_text(encoding="utf-8")
    liam = (ROOT / "frontend" / "js" / "liam" / "liam-controller.js").read_text(encoding="utf-8")
    require("ci-vista-semana" in frontend and "renderSemana" in frontend, "Falta la vista semanal")
    require("ci-vista-agenda" in frontend and "renderAgenda" in frontend, "Falta la agenda")
    require("/mis-pendientes" in frontend and "renderMisPendientes" in frontend, "Falta Mis pendientes")
    require("document.getElementById('dashboard')?.parentElement" in frontend, "El calendario no usa un anclaje estable de la SPA")
    index = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    require("onclick=\"mostrarSeccion('calendario-inteligente')\"" in index, "El menú no abre el calendario mejorado")
    require("2.7.6-ocr-auto-calendar-2" in index, "Falta invalidar la caché del calendario")
    require("waitForElement('#ci-periodo')" in liam, "LIAM no espera la carga real del calendario")
    require("window.ciSetPeriodo(action.period)" in liam, "LIAM no aplica el periodo consultado")
    require("d.name==='get_pending_activities_summary'" in liam, "La voz Realtime no navega al resultado de pendientes")

    with tempfile.TemporaryDirectory(prefix="pi-calendar-phase1-") as temp:
        root = Path(temp)
        repo = CalendarioInteligenteRepository(str(root / "db.sqlite3"), str(root / "uploads"))
        repo.init_schema(force=True)
        ana = {"id": 10, "username": "ana", "nombre_completo": "Ana Docente"}
        bob = {"id": 20, "username": "bob", "nombre_completo": "Bob Docente"}

        with tenant_context(1, role="DOCENTE", username="ana"):
            own = repo.create_entregable({
                "titulo": "Planeación propia", "fecha_limite": "2026-08-18",
                "responsable_id": 10, "responsable_nombre": "Ana Docente", "estado": "pendiente",
            })
            repo.create_entregable({
                "titulo": "Asignación de Bob", "fecha_limite": "2026-08-19",
                "responsable_id": 20, "responsable_nombre": "Bob Docente", "estado": "pendiente",
            })
            require([row["id"] for row in repo.list_mis_pendientes(ana)] == [own["id"]], "Ana recibió pendientes ajenos")
            require(len(repo.list_mis_pendientes(bob)) == 1, "Bob no recibió su pendiente")
            repo.update_entregable(own["id"], {"estado": "entregado"})
            require(not repo.list_mis_pendientes(ana), "Un entregado apareció como pendiente")
            repo.create_entregable({
                "titulo": "Actividad no aplicable", "fecha_limite": "2026-08-20",
                "responsable_id": 10, "responsable_nombre": "Ana Docente", "estado": "no_aplica",
            })
            repo.create_entregable({
                "titulo": "Actividad cerrada", "fecha_limite": "2026-08-21",
                "responsable_id": 10, "responsable_nombre": "Ana Docente", "estado": "cerrado",
            })
            require(not repo.list_mis_pendientes(ana), "NO_APLICA o cerrado apareció como pendiente")

        with tenant_context(2, role="DOCENTE", username="ana"):
            require(not repo.list_mis_pendientes(ana), "Mis pendientes cruzó el aislamiento tenant")

    print("PASS test_calendar_phase1_views_v2_7_0")


if __name__ == "__main__":
    run()
