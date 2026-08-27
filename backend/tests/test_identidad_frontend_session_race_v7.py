from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
IDENTITY_JS = ROOT / "frontend" / "js" / "modules" / "institucional-normativo.js"
INDEX_HTML = ROOT / "frontend" / "index.html"


def test_identidad_publica_no_sobrescribe_una_sesion_autenticada():
    source = IDENTITY_JS.read_text(encoding="utf-8")

    assert "if (token()) return cargarIdentidadEfectiva(silent);" in source
    assert "if (token()) return data;" in source
    assert "if (token()) cargarIdentidadEfectiva(true);" in source
    assert "else cargarIdentidadPublica(true);" in source


def test_javascript_institucional_tiene_version_nueva_de_cache():
    html = INDEX_HTML.read_text(encoding="utf-8")

    assert "institucional-normativo.js?v=2.7.4-identidad-persistente-1" in html


def test_carga_de_imagen_ignora_respuestas_anteriores():
    source = IDENTITY_JS.read_text(encoding="utf-8")
    assert "img.dataset.identityRequest = requestId;" in source
    assert "img.dataset.identityRequest !== requestId" in source


def main():
    test_identidad_publica_no_sobrescribe_una_sesion_autenticada()
    test_javascript_institucional_tiene_version_nueva_de_cache()
    test_carga_de_imagen_ignora_respuestas_anteriores()
    print("Identidad efectiva protegida contra carrera de sesión: PASS")


if __name__ == "__main__":
    main()
