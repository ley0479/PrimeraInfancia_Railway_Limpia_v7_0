from pathlib import Path


def main():
    root = Path(__file__).parents[2]
    html = (root / "frontend" / "index.html").read_text(encoding="utf-8")
    js = (root / "frontend" / "js" / "app.js").read_text(encoding="utf-8")
    assert "Coordinadores y equipos de Talento Humano" in html
    assert "talentoImprimirTodos()" in html
    assert "/api/base-maestra/resumen" in js
    assert "function talentoFiltrarEquipo" in js
    assert "function talentoImprimirEquipo" in js
    assert "function talentoImprimirTodos" in js
    assert "duplicados omitidos" in js
    print("TALENTO_EQUIPOS_IMPRESION_PASS")


if __name__ == "__main__":
    main()
