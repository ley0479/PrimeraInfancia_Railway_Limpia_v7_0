from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend" / "modules" / "institucional_normativo.py"
FRONTEND = ROOT / "frontend" / "js" / "modules" / "institucional-normativo.js"
INDEX = ROOT / "frontend" / "index.html"


def main():
    backend = BACKEND.read_text(encoding="utf-8")
    repair = backend[backend.index("def _repair_missing_branding_references"):backend.index("def _row_to_dict")]
    before_request = backend[backend.index("def _ensure_schema"):backend.index("@bp.route('/api/configuracion-publica")]
    assert "SET activo=0" not in repair
    assert "=NULL" not in repair
    assert "_repair_missing_branding_references(" not in before_request

    frontend = FRONTEND.read_text(encoding="utf-8")
    assert "primeraInfanciaIdentityScope" in frontend
    assert "sessionStorage.setItem(IDENTITY_SCOPE_KEY, scope.value)" in frontend
    save = frontend[frontend.index("async function guardarConfiguracionInstitucional"):frontend.index("async function subirArchivoConfiguracion")]
    assert "await cargarConfiguracionInstitucional(true)" in save
    assert "await cargarIdentidadEfectiva(true)" in save

    html = INDEX.read_text(encoding="utf-8")
    assert "institucional-normativo.js?v=2.7.4-identidad-persistente-1" in html
    print("IDENTIDAD_INSTITUCIONAL_PERSISTENTE_REFRESH_PASS")


if __name__ == "__main__":
    main()
