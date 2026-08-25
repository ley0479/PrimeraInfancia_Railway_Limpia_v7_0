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
        }
        g.current_user = users[identity]

    register_asistente_capacitacion(app, database)
    client = app.test_client()

    tour = client.get('/api/asistente-capacitacion/elian/platform-tour', headers={'X-Test-Identity':'admin-a'})
    assert tour.status_code == 200
    payload = tour.get_json()
    assert payload['modules'][0]['module_id'] == 'dashboard'
    assert any(item['module_id'] == 'componente-psicosocial' for item in payload['modules'])

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

print('ELIAN_HTTP_MULTITENANT_V7_PASS')
