from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
backend = (ROOT / 'backend' / 'modules' / 'institucional_normativo.py').read_text(encoding='utf-8')
frontend = (ROOT / 'frontend' / 'js' / 'modules' / 'institucional-normativo.js').read_text(encoding='utf-8')
html = (ROOT / 'frontend' / 'index.html').read_text(encoding='utf-8')

assert "request.args.get('scope')" in backend
assert "SELECT * FROM identidad_global_archivos" in backend
assert "'foto_admin':'foto_admin_path'" in backend
assert "'nombre_admin': cfg['nombre_admin']" in backend
assert "foto_admin_url: visual.foto_admin_url" in frontend
assert "?scope=${scope}" in frontend
assert "await cargarCatalogoIdentidadVisual(true);" in frontend
assert 'institucional-logo-header' in html
assert 'institucional-foto-admin-header' in html
assert "entrante[key] === null" in frontend
assert "'favicon_url', 'foto_admin_url', 'nombre_admin', 'cargo_admin'" in frontend
print('IDENTIDAD_CATALOGO_GLOBAL_HEADER_V7_PASS')
