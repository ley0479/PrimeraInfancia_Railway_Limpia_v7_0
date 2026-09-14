"""Contrato de UI dinámica y renderizado seguro para Lía."""
from pathlib import Path
from modules.asistente_capacitacion.action_intents import propose_action, propose_read_actions

ROOT=Path(__file__).resolve().parents[2]

def test_backend_emits_structured_visual_contract():
    routes=(ROOT/'backend/modules/asistente_capacitacion/routes.py').read_text(encoding='utf-8')
    for field in ("'text'", "'componentType'", "'data'", "'targetSelector'", "'schemaVersion'"):
        assert field in routes
    assert "metric-card" in routes and "table" in routes and "spotlight" in routes
    assert "UDS: {x.get('unit')" in routes and "La consulta no devolvió registros" in (ROOT/'frontend/js/liam/liam-controller.js').read_text(encoding='utf-8')

def test_frontend_renders_without_injecting_data_as_html():
    controller=(ROOT/'frontend/js/liam/liam-controller.js').read_text(encoding='utf-8')
    routes=(ROOT/'backend/modules/asistente_capacitacion/routes.py').read_text(encoding='utf-8')
    css=(ROOT/'frontend/css/lia-dynamic-ui.css').read_text(encoding='utf-8')
    html=(ROOT/'frontend/index.html').read_text(encoding='utf-8')
    assert "function renderStructured" in controller and "function highlightElement" in controller
    assert 'td.textContent = String(value' in controller and 'value.textContent = String(item.value' in controller
    assert "lia-data-drawer" in css and "lia-spotlight" in css
    assert "lia-dynamic-ui.css?v=2.7.5-presenter-controls-1" in html
    assert 'renderStructured(result.ui)' in controller and '"X-Liam-Module"' in controller
    assert "ui=visual_payload({'message':'Datos consultados por Lía.','tool_result':result},active_module)" in routes
    assert "function syncDataPresentation" in controller and "lia-data-active" in css
    assert "data-lia-presenter-avatar" in controller and "pointing_right" in controller
    assert "lia-relation-format" in css and "maxColumns" in controller
    assert "function configureDataDrawer" in controller and 'data-lia-drawer-action="ratio"' in controller
    assert 'data-ratio="40"' in css and 'data-maximized="true"' in css

def test_master_report_phrases_force_data_cards():
    for question in ('Dame el informe de la Base Maestra','Muéstrame el registro de la Base Maestra','Explica la Base Maestra'):
        assert propose_action(question)['server_tool']=='get_foundation_data_summary'
        assert propose_read_actions(question)[0]['server_tool']=='get_foundation_data_summary'

if __name__=='__main__':
    test_backend_emits_structured_visual_contract()
    test_frontend_renders_without_injecting_data_as_html()
    test_master_report_phrases_force_data_cards()
    print('LIA_DYNAMIC_UI_V7_PASS')
