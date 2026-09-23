"""Regresión: RPP usa la última importación Cuéntame del tenant."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_usuarios_es_fuente_prioritaria_sin_mezclar_tenants() -> None:
    source = (ROOT / 'backend' / 'app.py').read_text(encoding='utf-8')
    start = source.index('def _alpha59_obtener_usuarios_unidad(unidad):')
    end = source.index("@app.route('/api/formatos/diagnostico'", start)
    function = source[start:end]
    assert "grupos_fuente = (('usuarios',), ('master_ninos',), ('beneficiarios',))" in function
    assert "COALESCE(fundacion_id,1)=?" in function
    assert "if usuarios:" in function


if __name__ == '__main__':
    test_usuarios_es_fuente_prioritaria_sin_mezclar_tenants()
    print('Fuente Cuéntame prioritaria para RPP: PASS')
