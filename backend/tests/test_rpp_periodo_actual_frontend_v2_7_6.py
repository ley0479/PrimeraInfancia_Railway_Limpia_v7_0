"""Regresión: RPP no debe iniciar silenciosamente en enero."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_selector_inicia_en_mes_actual() -> None:
    source = (ROOT / "frontend" / "js" / "app.js").read_text(encoding="utf-8")
    start = source.index("function inicializarPeriodoFormatos()")
    end = source.index("document.addEventListener('DOMContentLoaded', inicializarPeriodoFormatos)", start)
    function = source[start:end]
    assert "mesInput.value = String(ahora.getMonth() + 1)" in function
    assert "if (mesInput && !mesInput.value)" not in function


def test_menu_no_fue_reemplazado_y_cache_se_actualizo() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    assert 'id="sidebar-institucional"' in html
    assert 'id="menu-lateral-institucional"' in html
    assert "2.7.6-rpp-periodo-1" in html


if __name__ == "__main__":
    test_selector_inicia_en_mes_actual()
    test_menu_no_fue_reemplazado_y_cache_se_actualizo()
    print("Periodo actual RPP v2.7.6: PASS")
