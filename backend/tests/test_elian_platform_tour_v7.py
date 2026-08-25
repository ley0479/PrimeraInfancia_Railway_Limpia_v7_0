"""Contrato de recorrido transversal seguro y configuración desacoplada de ELIAN."""
from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))

from modules.asistente_capacitacion.config import public_elian_flags
from modules.asistente_capacitacion.elian_module_registry import ELIAN_MODULE_REGISTRY, authorized_modules


def read(relative):
    return (ROOT / relative).read_text(encoding='utf-8')


os.environ['ENABLE_LIAM_ASSISTANT'] = 'true'
os.environ.pop('ENABLE_ELIAN_ASSISTANT', None)
flags = public_elian_flags()
assert flags['enabled'] is True
assert flags['assistant_name'] == 'ELIAN'
assert flags['avatar_variant'] == 'afro_colombian_institutional'

ids = [item['module_id'] for item in ELIAN_MODULE_REGISTRY]
assert len(ids) >= 16 and len(ids) == len(set(ids))
assert ids[0] == 'dashboard'
allowed = authorized_modules(['dashboard', 'base-maestra'])
assert [item['module_id'] for item in allowed] == ['dashboard', 'base-maestra']
for item in ELIAN_MODULE_REGISTRY:
    for field in ('purpose', 'authorized_users', 'inputs', 'data_source', 'validations', 'outputs', 'downstream_use', 'frequent_errors', 'next_step'):
        assert field in item

engine = read('frontend/js/liam/elian-platform-tour.js')
routes = read('backend/modules/asistente_capacitacion/routes.py')
schema = read('backend/modules/asistente_capacitacion/schema.py')
controller = read('frontend/js/liam/liam-controller.js')
admin_ui = read('frontend/js/liam/elian-admin-config.js')
html = read('frontend/index.html')
for event in ('module-open-requested','module-loading','module-ready','module-guide-started','module-guide-completed','module-guide-paused','module-guide-resumed','module-guide-skipped','tour-completed','tour-failed'):
    assert event in engine
for control in ('pause','resume','repeat','skip','previous','next','cancel'):
    assert f'function {control}' in engine
assert 'window.mostrarSeccion(module.route)' in engine
assert 'elian_platform_tour_progress' in schema
assert "@bp.get('/elian/platform-tour')" in routes
assert "@bp.route('/elian/platform-tour/progress'" in routes
assert "@bp.route('/elian/visual-config'" in routes
assert 'd.elian||' in controller
assert 'elian-admin-config.js' in html
assert 'administracion.elian.visual-config' in html
assert "method:'PUT'" in admin_ui
assert (ROOT / 'frontend/assets/lia/elian-afro-institutional-male-v1.png').stat().st_size > 100_000
assert (ROOT / 'frontend/assets/lia/elian-afro-institutional-female-v1.png').stat().st_size > 100_000
for forbidden in ('eval(', 'new Function', 'document.write('):
    assert forbidden not in engine

print('ELIAN_PLATFORM_TOUR_V7_PASS')
