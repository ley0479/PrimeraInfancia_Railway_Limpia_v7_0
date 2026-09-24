from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_legacy_xhr_uses_the_clear_error_translator():
    source = (ROOT / 'frontend' / 'js' / 'app.js').read_text(encoding='utf-8')

    assert 'Error técnico del servidor' not in source
    assert "construirMensajeErrorClaro(resultado, xhr.status" in source
    assert 'Qué ocurrió:' in source
    assert 'Qué debe hacer:' in source


def test_frontend_cache_version_points_to_clear_errors_v2():
    html = (ROOT / 'frontend' / 'index.html').read_text(encoding='utf-8')

    assert 'app.js?v=2.7.6-liam-errors-2' in html
