"""Contratos de fuente única para docentes y descarga RPP multi-fundación."""

import ast
from pathlib import Path


APP = Path(__file__).resolve().parents[1] / 'app.py'


def function_source(name: str) -> str:
    source = APP.read_text(encoding='utf-8')
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(source, node) or ''
    raise AssertionError(f'No existe {name}')


def test_docentes_consultan_talento_humano_de_base_maestra():
    source = function_source('obtener_talentos_por_unidad')
    assert 'FROM master_talento_humano' in source
    assert 'COALESCE(fundacion_id,1) = ?' in source


def test_rpp_consulta_participantes_con_fundacion_explicita():
    source = function_source('_alpha59_obtener_usuarios_unidad')
    assert 'SELECT * FROM master_ninos WHERE activo=1 AND COALESCE(fundacion_id,1)=?' in source
    assert '(tenant_id,)' in source


if __name__ == '__main__':
    test_docentes_consultan_talento_humano_de_base_maestra()
    test_rpp_consulta_participantes_con_fundacion_explicita()
    print('OK: Base Maestra alimenta docentes y RPP por fundación')
