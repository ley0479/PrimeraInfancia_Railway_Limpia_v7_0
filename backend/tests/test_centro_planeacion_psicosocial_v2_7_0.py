#!/usr/bin/env python3
"""Regresión funcional del Centro de Planeación y Componente Psicosocial 2.7.0.

Usa datos completamente ficticios y valida no duplicación, aislamiento tenant,
versionado, cierres humanos, documentos, dependencias y vistas por rol.
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
import zipfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "tests"))

from modules.centro_planeacion.repository import CentroPlaneacionRepository
from modules.componente_psicosocial.repository import ComponentePsicosocialRepository
from modules.familias_redes.repository import FamiliasRedesRepository
from modules.gestion_integral_uca.integrations import UCAIntegrationEngine
from modules.gestion_integral_uca.repository import GestionIntegralRepository
from modules.motor_gestion_proyecto.repository import MotorGestionRepository
from test_expediente_uca_central_v2_5_2 import prepare_database


def require(value, message: str) -> None:
    if not value:
        raise AssertionError(message)


def expect_error(fn, contains: str) -> None:
    try:
        fn()
    except Exception as exc:  # noqa: BLE001
        require(contains.lower() in str(exc).lower(), f"Error inesperado: {exc}")
        return
    raise AssertionError(f"Se esperaba error con: {contains}")


def run() -> None:
    with tempfile.TemporaryDirectory(prefix="pi-v270-") as temp:
        root = Path(temp)
        db = root / "database.sqlite3"
        data_dir = root / "data"
        output = root / "output"
        output.mkdir(parents=True, exist_ok=True)
        prepare_database(db, data_dir)

        coordinator_a = {"id": 101, "username": "coord.a", "nombre_completo": "Coordinación A", "rol": "COORDINADOR", "fundacion_id": 1}
        coordinator_b = {"id": 202, "username": "coord.b", "nombre_completo": "Coordinación B", "rol": "COORDINADOR", "fundacion_id": 2}
        professional_a = {"id": 303, "username": "psico.a", "nombre_completo": "Profesional Psicosocial A", "rol": "PSICOSOCIAL", "fundacion_id": 1, "unidades": ["UCA CENTRAL A"]}
        other_professional = {"id": 404, "username": "psico.otro", "nombre_completo": "Profesional Psicosocial Otro", "rol": "PSICOSOCIAL", "fundacion_id": 1, "unidades": ["UCA CENTRAL A"]}

        giu = GestionIntegralRepository(str(db), str(data_dir), str(output)); giu.init_schema()
        motor = MotorGestionRepository(str(db), str(data_dir), str(output)); motor.init_schema()
        families = FamiliasRedesRepository(str(db), str(data_dir), str(output)); families.init_schema()
        ps = ComponentePsicosocialRepository(str(db), str(data_dir), str(output)); ps.init_schema()
        planning = CentroPlaneacionRepository(str(db), str(data_dir), str(output)); planning.init_schema()

        exp_a = giu.sync_all_units(1, "2026", "CONTRATO-A", coordinator_a)[0]
        exp_b = giu.sync_all_units(2, "2026", "CONTRATO-B", coordinator_b)[0]
        families.sync_family_records(1, exp_a["id"], exp_a["unidad_nombre"], exp_a.get("unidad_id"), coordinator_a)
        families.sync_family_records(2, exp_b["id"], exp_b["unidad_nombre"], exp_b.get("unidad_id"), coordinator_b)

        # El profesional se asigna únicamente a expedientes de su fundación/UCA.
        first_ps_sync = ps.sync_expedientes(1, professional_a, exp_a["unidad_nombre"])
        second_ps_sync = ps.sync_expedientes(1, professional_a, exp_a["unidad_nombre"])
        tenant_b_sync = ps.sync_expedientes(2, coordinator_b, exp_b["unidad_nombre"])
        require(first_ps_sync["creados"] == 2, "No se crearon dos referencias psicosociales para la UCA A")
        require(second_ps_sync["creados"] == 0 and second_ps_sync["actualizados"] == 2, "Sincronización psicosocial no idempotente")
        cases_a = ps.list_expedientes(1, {"profesional_id": professional_a["id"]})
        cases_b = ps.list_expedientes(2, {})
        require(len(cases_a) == first_ps_sync["creados"] and len(cases_a) > 0, "Asignación psicosocial de la UCA A incorrecta")
        require(len(cases_b) == tenant_b_sync["creados"] and len(cases_b) > 0, "Aislamiento psicosocial de la UCA B incorrecto")
        require(not ps.list_expedientes(1, {"profesional_id": other_professional["id"]}), "Otro profesional obtuvo expedientes no asignados")
        dashboard_a = ps.dashboard(1, coordinator_a, {"vista_coordinacion": True})
        require(dashboard_a["vista"] == "COORDINACION" and dashboard_a["resumen"]["expedientes"] == len(cases_a), "El dashboard coordinador no abrió el componente psicosocial")

        case = cases_a[0]
        char1 = ps.create_characterization(1, case["id"], {
            "tipo": "INICIAL", "fecha_caracterizacion": date.today().isoformat(),
            "factores_protectores": ["Red familiar ficticia"],
            "situaciones_acompanar": ["Situación ficticia"],
            "conclusion_profesional": "Conclusión ficticia para revisión humana",
        }, professional_a)
        char2 = ps.create_characterization(1, case["id"], {
            "tipo": "SEGUIMIENTO", "fecha_caracterizacion": date.today().isoformat(),
            "factores_protectores": ["Apoyo comunitario ficticio"],
            "situaciones_acompanar": [],
            "conclusion_profesional": "Segunda versión ficticia",
        }, professional_a)
        require(char1["version"] == 1 and char2["version"] == 2, "El versionado de caracterización falló")
        detail = ps.expediente(1, case["id"])
        active = [row for row in detail["caracterizaciones"] if int(row.get("activo") or 0) == 1]
        require(len(active) == 1 and active[0]["version"] == 2, "No se conservó una única caracterización activa")
        validated = ps.review_characterization(1, char2["id"], coordinator_a, approve=True)
        require(validated["estado"] == "VALIDADA", "La coordinación no validó la caracterización")

        plan = ps.create_plan(1, case["id"], {
            "nombre": "Plan ficticio", "objetivo_general": "Objetivo ficticio",
            "fecha_inicio": date.today().isoformat(),
            "fecha_fin_estimada": (date.today() + timedelta(days=15)).isoformat(),
        }, professional_a)
        action = ps.create_action(1, plan["id"], {
            "titulo": "Visita ficticia", "descripcion": "Acción de prueba",
            "fecha_inicio": date.today().isoformat(),
            "fecha_limite": (date.today() + timedelta(days=4)).isoformat(),
            "responsable_id": professional_a["id"], "responsable_nombre": professional_a["nombre_completo"],
            "prioridad": "ALTA", "requiere_evidencia": True,
        }, professional_a)
        expect_error(lambda: ps.update_action(1, action["id"], {"estado": "VALIDADA", "porcentaje": 100}, coordinator_a, allow_validate=True), "evidencia")
        action = ps.update_action(1, action["id"], {
            "estado": "VALIDADA", "porcentaje": 100,
            "resultado": "Resultado ficticio", "evidencia_referencia": "EV-PS-001",
        }, coordinator_a, allow_validate=True)
        require(action["estado"] == "VALIDADA", "La acción no quedó validada")
        plan = ps.close_plan(1, plan["id"], {"resultado_final": "Resultado final ficticio"}, coordinator_a)
        require(plan["estado"] == "CERRADO", "El plan no cerró con validación humana")
        ps.add_followup(1, case["id"], {"fecha": date.today().isoformat(), "descripcion": "Seguimiento ficticio", "resultado": "Atendido"}, professional_a)
        report = ps.prepare_report(1, case["id"], professional_a, include_restricted=True)
        require(Path(report["ruta_archivo"]).is_file(), "No se generó el informe psicosocial")
        require(ps.document_path(1, report["id"]), "Falló la validación de integridad del informe")

        # Dos actividades familiares alimentan el calendario central; las referencias
        # espejo del Motor de Gestión no deben duplicarlas.
        for index in range(2):
            families.create_activity(1, {
                "expediente_uca_id": exp_a["id"], "unidad_nombre": exp_a["unidad_nombre"],
                "tipo": "ESCUELA_FAMILIAS", "titulo": f"Escuela ficticia {index + 1}",
                "objetivo": "Objetivo de prueba", "fecha_programada": (date.today() + timedelta(days=index)).isoformat(),
                "fecha_limite_cierre": (date.today() + timedelta(days=index + 2)).isoformat(),
            }, professional_a)
        sync1 = planning.synchronize(1, coordinator_a)
        sync2 = planning.synchronize(1, coordinator_a)
        activities = planning.list_activities(1, {})
        require(sync1["creadas"] == 3, "El centro no incorporó las dos actividades y la acción psicosocial")
        require(sync2["creadas"] == 0 and sync2["actualizadas"] == 3, "Sincronización del centro no idempotente")
        require(len(activities) == 3, "El Motor de Gestión duplicó actividades misionales")
        require(not planning.list_activities(2, {}), "La fundación B recibió actividades de la A")

        # Dependencia, borradores documentales y cierre controlado.
        first, second = activities[0], activities[1]
        planning.add_dependency(1, second["id"], first["id"], coordinator_a)
        expect_error(lambda: planning.update_activity(1, second["id"], {"estado_flujo": "APROBADA", "porcentaje": 100}, coordinator_a, True), "dependencias")
        docs_first = planning.prepare_documents(1, first["id"], ["AGENDA", "ACTA", "LISTADO_ASISTENCIA", "INFORME"], professional_a)
        require(len(docs_first) == 4 and all(row["estado"] == "BORRADOR" for row in docs_first), "Los productos no quedaron como borradores")
        planning.update_activity(1, first["id"], {"estado_flujo": "APROBADA", "porcentaje": 100}, coordinator_a, True)
        require(planning.activity(1, second["id"])["bloqueada"] == 0, "La dependencia no se liberó")
        planning.prepare_documents(1, second["id"], ["ACTA"], professional_a)
        planning.update_activity(1, second["id"], {"estado_flujo": "APROBADA", "porcentaje": 100}, coordinator_a, True)

        # Un profesional no puede elevar la vista a coordinación usando un parámetro.
        professional_dashboard = planning.dashboard(1, professional_a, {"vista": "coordinacion"})
        require(professional_dashboard["vista"] == "ROL", "Escalamiento de vista por parámetro detectado")
        require(all(row.get("responsable_id") == professional_a["id"] for row in professional_dashboard["actividades"]), "El profesional vio actividades ajenas")
        other_dashboard = planning.dashboard(1, other_professional, {"vista": "coordinacion"})
        require(other_dashboard["vista"] == "ROL" and not other_dashboard["actividades"], "Otro profesional obtuvo agenda ajena")

        package = planning.export_monthly_package(1, coordinator_a, date.today().strftime("%Y-%m"))
        require(Path(package["ruta"]).is_file(), "No se generó paquete mensual")
        with zipfile.ZipFile(package["ruta"]) as archive:
            require({"00_RESUMEN.json", "01_POR_COMPONENTE.json", "02_POR_UCA.json", "LEEME.txt"} <= set(archive.namelist()), "Paquete mensual incompleto")

        # La vista UCA incluye ambos dominios nuevos.
        engine = UCAIntegrationEngine(str(db), str(data_dir))
        view = engine.build_view(giu.get_expediente(exp_a["id"], 1))
        component_codes = {row["codigo"] for row in view["componentes"]}
        require({"planeacion_operativa", "psicosocial"} <= component_codes, "Expediente UCA no integró los dominios nuevos")

        conn = sqlite3.connect(db)
        try:
            require(conn.execute("SELECT COUNT(*) FROM cpo_actividad_metadata WHERE fundacion_id=1").fetchone()[0] == 3, "Metadatos del centro duplicados")
            require(conn.execute("SELECT COUNT(*) FROM ps_expedientes WHERE fundacion_id=2").fetchone()[0] == len(cases_b), "Datos tenant B alterados")
            require(conn.execute("SELECT COUNT(*) FROM ps_auditoria_accesos WHERE fundacion_id=1").fetchone()[0] > 0, "No existe trazabilidad psicosocial")
        finally:
            conn.close()

    print("PASS test_centro_planeacion_psicosocial_v2_7_0")


if __name__ == "__main__":
    run()
