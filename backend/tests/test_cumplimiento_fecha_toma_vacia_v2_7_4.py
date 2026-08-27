from pathlib import Path


def test_consulta_nutricional_ignora_fecha_toma_vacia():
    app_source = (Path(__file__).parents[1] / "app.py").read_text(encoding="utf-8")
    start = app_source.index("def contar_peso_talla_vencido")
    end = app_source.index("def contar_entregables", start)
    function_source = app_source[start:end]

    assert "date(NULLIF(TRIM(s.fecha_toma), '')) >= date(?)" in function_source
    assert "date(s.fecha_toma) >= date(?)" not in function_source


if __name__ == "__main__":
    test_consulta_nutricional_ignora_fecha_toma_vacia()
    print("CUMPLIMIENTO_FECHA_TOMA_VACIA_PASS")
