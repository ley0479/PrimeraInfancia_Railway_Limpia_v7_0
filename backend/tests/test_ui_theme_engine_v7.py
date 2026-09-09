from pathlib import Path
import ast
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding='utf-8')


def test_closed_registry_contains_the_six_professional_themes() -> None:
    source = read('backend/modules/theme_manager/theme_registry.py')
    required = {'ocean-deep', 'neutral-professional', 'natura-green', 'aurora-violet', 'warm-sand', 'executive-premium'}
    assert all(key in source for key in required)
    assert 'THEME_KEYS = frozenset' in source
    ast.parse(source)


def test_theme_manager_has_no_runtime_ddl() -> None:
    routes = read('backend/modules/theme_manager/routes.py')
    services = read('backend/modules/theme_manager/services.py')
    register_body = routes[routes.index('def register_theme_manager'):]
    assert 'before_request' not in register_body
    assert 'init_schema(database_path)' not in register_body
    assert 'def init_schema(database_path: str)' in services
    assert '    init_schema(database_path)' not in services
    assert 'init_theme_manager_schema' in read('backend/init_hosting.py')


def test_frontend_uses_one_variable_engine_and_postgresql_manager() -> None:
    html = read('frontend/index.html')
    manager = read('frontend/js/modules/theme-manager.js')
    css = read('frontend/css/design-system/theme-engine.css')
    assert 'theme-engine.css?v=2.7.0-theme-engine-1' in html
    assert 'theme-executive-preview' not in html
    assert "root.dataset.theme =" in manager
    assert '/api/theme-manager' in manager
    assert "app:theme-changed" in manager
    assert '@media print' in css
    assert '--pi-success' not in css and '--pi-danger' not in css


def test_chart_adapter_is_loaded_and_does_not_change_elian_identity() -> None:
    html = read('frontend/index.html')
    adapter = read('frontend/js/themes/chart-theme-adapter.js')
    assert 'chart-theme-adapter.js' in html
    assert "app:theme-changed" in adapter
    forbidden = ('gender', 'skin', 'hair', 'voice', 'liam-avatar', 'elian-inline')
    assert all(token not in adapter.lower() for token in forbidden)


def test_registry_and_user_preference_persist_in_database() -> None:
    sys.path.insert(0, str(ROOT / 'backend'))
    from modules.theme_manager.services import init_schema, list_themes, save_user_preference
    with tempfile.TemporaryDirectory() as temporary:
        database = str(Path(temporary) / 'themes.sqlite3')
        init_schema(database)
        themes = list_themes(database, fundacion_id=9)
        assert [theme['codigo'] for theme in themes] == sorted([
            'ocean-deep', 'neutral-professional', 'natura-green', 'aurora-violet',
            'warm-sand', 'executive-premium', 'alto-contraste'
        ], key=lambda code: next(t['nombre'] for t in themes if t['codigo'] == code).lower())
        context = save_user_preference(database, {
            'id': 77, 'fundacion_id': 9, 'rol': 'DOCENTE', 'username': 'prueba'
        }, {'tema_codigo': 'natura-green', 'modo': 'claro', 'layout': 'compacto'})
        assert context['tema']['codigo'] == 'natura-green'
        assert context['fundacion_id'] == 9
