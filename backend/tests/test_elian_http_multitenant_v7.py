"""Prueba HTTP aislada de progreso, roles y configuración visual ELIAN."""
from pathlib import Path
import os
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))

from flask import Flask, g, request
from modules.asistente_capacitacion.routes import register_asistente_capacitacion

os.environ['ENABLE_LIA_ASSISTANT'] = 'true'
os.environ['ENABLE_LIAM_ASSISTANT'] = 'true'

with tempfile.TemporaryDirectory() as folder:
    app = Flask(__name__)
    database = str(Path(folder) / 'elian.sqlite3')

    @app.before_request
    def test_identity():
        identity = request.headers.get('X-Test-Identity', 'admin-a')
        users = {
            'admin-a': {'id': 10, 'fundacion_id': 1, 'rol': 'SUPERADMIN', 'username': 'admin-a'},
            'teacher-b': {'id': 20, 'fundacion_id': 2, 'rol': 'DOCENTE', 'username': 'teacher-b'},
            'manager-a': {'id': 11, 'fundacion_id': 1, 'rol': 'GERENTE', 'username': 'manager-a'},
            'coordinator-a': {'id': 12, 'fundacion_id': 1, 'rol': 'COORDINADOR', 'username': 'coordinator-a'},
            'nutrition-a': {'id': 13, 'fundacion_id': 1, 'rol': 'NUTRICIONISTA', 'username': 'nutrition-a'},
            'psychosocial-a': {'id': 14, 'fundacion_id': 1, 'rol': 'PSICOSOCIAL', 'username': 'psychosocial-a'},
        }
        g.current_user = users[identity]

    register_asistente_capacitacion(app, database)
    client = app.test_client()

    tour = client.get('/api/asistente-capacitacion/elian/platform-tour', headers={'X-Test-Identity':'admin-a'})
    assert tour.status_code == 200
    payload = tour.get_json()
    assert payload['modules'][0]['module_id'] == 'dashboard'
    assert any(item['module_id'] == 'componente-psicosocial' for item in payload['modules'])

    expected = {
        'manager-a': {'dashboard','administracion','facturacion'},
        'coordinator-a': {'dashboard','talento','componente-psicosocial'},
        'teacher-b': {'dashboard','planeacion-pedagogica','formatos'},
        'nutrition-a': {'dashboard','base-maestra','salud-nutricion'},
        'psychosocial-a': {'dashboard','familias-redes','componente-psicosocial'},
    }
    for identity, required in expected.items():
        response = client.get('/api/asistente-capacitacion/elian/platform-tour', headers={'X-Test-Identity':identity})
        assert response.status_code == 200
        visible = {item['module_id'] for item in response.get_json()['modules']}
        assert required <= visible

    update = client.put('/api/asistente-capacitacion/elian/platform-tour/progress', json={
        'status':'paused', 'mode':'interactive', 'current_module_id':'base-maestra',
        'current_step':1, 'completed_modules':['dashboard'], 'skipped_modules':[],
    }, headers={'X-Test-Identity':'admin-a'})
    assert update.status_code == 200

    isolated = client.get('/api/asistente-capacitacion/elian/platform-tour/progress', headers={'X-Test-Identity':'teacher-b'})
    assert isolated.status_code == 200 and isolated.get_json()['progress'] is None

    forbidden = client.put('/api/asistente-capacitacion/elian/visual-config', json={'avatar_gender':'female'}, headers={'X-Test-Identity':'teacher-b'})
    assert forbidden.status_code == 403
    configured = client.put('/api/asistente-capacitacion/elian/visual-config', json={
        'assistant_name':'ELIAN', 'avatar_gender':'male',
        'avatar_variant':'afro_colombian_institutional', 'motion_level':'light',
    }, headers={'X-Test-Identity':'admin-a'})
    assert configured.status_code == 200 and configured.get_json()['asset_ready'] is True
    for variant in ('afro_colombian_institutional','afro_colombian_technological','afro_colombian_educational'):
        for gender in ('male','female'):
            selected = client.put('/api/asistente-capacitacion/elian/visual-config', json={
                'assistant_name':'ELIAN', 'avatar_gender':gender,
                'avatar_variant':variant, 'motion_level':'light',
            }, headers={'X-Test-Identity':'admin-a'})
            assert selected.status_code == 200
            body = selected.get_json()
            assert body['asset_ready'] is True
            assert gender in body['configuration']['avatar_asset_path']

print('ELIAN_HTTP_MULTITENANT_V7_PASS')
