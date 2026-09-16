from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
schema = (ROOT / "backend/modules/salud_nutricion/schema.py").read_text(encoding="utf-8")
service = (ROOT / "backend/modules/salud_nutricion/integral.py").read_text(encoding="utf-8")
frontend = (ROOT / "frontend/js/modules/salud-nutricion.js").read_text(encoding="utf-8")
index = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
repository = (ROOT / "backend/modules/salud_nutricion/repository.py").read_text(encoding="utf-8")
compat = (ROOT / "backend/modules/sqlalchemy_compat.py").read_text(encoding="utf-8")

for table in ("sn_periodos_mensuales", "sn_informes_mensuales", "sn_actas_institucionales", "sn_acta_tareas"):
    assert f"CREATE TABLE IF NOT EXISTS {table}" in schema
assert "UNIQUE(fundacion_id, anio_mes)" in schema
assert "UNIQUE(fundacion_id, anio, consecutivo)" in schema
assert "integridad_sha256" in schema
assert "El periodo est\\u00e1 aprobado y es inmutable" in service
assert 'number = f"ACTA-SN-{year}-{consecutive:04d}"' in service
assert "APROBAR_PERIODO_SALUD" in service and "CERRAR_ACTA_INSTITUCIONAL" in service
assert "generate_monthly_report" in service and "monthly_report_path" in service
assert "_write_institutional_minutes_pdf" in service
assert "start_job(\"INFORME_MENSUAL_SALUD\"" in service
assert '"status_url": f"/api/jobs/{job[\'id\']}"' in service
assert '@bp.route("/integral/periodos-mensuales", methods=["GET", "POST"])' in service
assert '@bp.route("/integral/actas", methods=["GET", "POST"])' in service
assert "@require_roles(*COORDINATION_ROLES)" in service
assert "snGuardarPeriodoMensual" in frontend and "snCrearActaInstitucional" in frontend
assert "snGenerarInformeMensual" in frontend
assert "esperarJobOperativo(data.job_id" in frontend
assert "ENABLE ROW LEVEL SECURITY" in repository and "FORCE ROW LEVEL SECURITY" in repository
assert "CREATE POLICY" in repository and "app.current_fundacion_id" in repository
assert "if self.table_exists(table)" in repository and "if not tables:" in repository
assert "enable_rls = getattr(self.repo, '_enable_institutional_rls', None)" in service
assert "set_config('app.current_fundacion_id'" in compat and "app.allow_global" in compat
assert 'snMostrarVista(\'mensuales\')' in index and 'snMostrarVista(\'actas\')' in index
assert "salud-nutricion.js?v=2.7.0-informes-actas-1" in index
print("SALUD_NUTRICION_INFORMES_ACTAS_V7_PASS")
