"""Contrato de UI dinámica y renderizado seguro para Lía."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def test_backend_emits_structured_visual_contract():
    routes=(ROOT/'backend/modules/asistente_capacitacion/routes.py').read_text(encoding='utf-8')
    for field in ("'text'", "'componentType'", "'data'", "'targetSelector'", "'schemaVersion'"):
        assert field in routes
    assert "metric-card" in routes and "table" in routes and "spotlight" in routes

def test_frontend_renders_without_injecting_data_as_html():
    controller=(ROOT/'frontend/js/liam/liam-controller.js').read_text(encoding='utf-8')
    css=(ROOT/'frontend/css/lia-dynamic-ui.css').read_text(encoding='utf-8')
    html=(ROOT/'frontend/index.html').read_text(encoding='utf-8')
    assert "function renderStructured" in controller and "function highlightElement" in controller
    assert 'td.textContent = String(value' in controller and 'value.textContent = String(item.value' in controller
    assert "lia-data-drawer" in css and "lia-spotlight" in css
    assert "lia-dynamic-ui.css?v=2.7.5-dynamic-ui-1" in html

if __name__=='__main__':
    test_backend_emits_structured_visual_contract()
    test_frontend_renders_without_injecting_data_as_html()
    print('LIA_DYNAMIC_UI_V7_PASS')
