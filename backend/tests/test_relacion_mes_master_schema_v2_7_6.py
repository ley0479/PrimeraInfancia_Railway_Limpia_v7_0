from pathlib import Path


def test_relacion_mes_uses_documento_as_nui_without_requiring_legacy_column():
    app_source = (Path(__file__).parents[1] / 'app.py').read_text(encoding='utf-8')
    route_source = app_source.split('def relacion_mes_generar():', 1)[1].split(
        'from services.relacion_mes_service', 1
    )[0]

    assert 'documento AS nui' in route_source
    assert 'documento, nui, nombre_completo' not in route_source
