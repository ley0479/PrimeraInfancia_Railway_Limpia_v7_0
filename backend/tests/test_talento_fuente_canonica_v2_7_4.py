from pathlib import Path


def test_tabla_talento_prioriza_base_maestra_publicada():
    source = (Path(__file__).parents[1] / "modules" / "talento_humano" / "services.py").read_text(encoding="utf-8")
    start = source.index("def list_talento(self)")
    end = source.index("def integral_dashboard", start)
    block = source[start:end]
    assert "list_master_talento(fundacion_id)" in block
    assert "fuente_canonica" in block
    assert "solo_lectura" in block
    assert "list_talento(fundacion_id, False)" in block


def test_frontend_protege_registros_publicados():
    source = (Path(__file__).parents[2] / "frontend" / "js" / "app.js").read_text(encoding="utf-8")
    assert "item.solo_lectura" in source
    assert ">Base Maestra</span>" in source


if __name__ == "__main__":
    test_tabla_talento_prioriza_base_maestra_publicada()
    test_frontend_protege_registros_publicados()
    print("TALENTO_FUENTE_CANONICA_PASS")
