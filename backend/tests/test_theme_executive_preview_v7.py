"""Contrato estatico para la vista previa ejecutiva aislada.

No importa Flask, no abre la base de datos y no consume servicios.
"""
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "frontend" / "index.html"
CSS = ROOT / "frontend" / "css" / "themes" / "executive-preview.css"
JS = ROOT / "frontend" / "js" / "modules" / "theme-executive-preview.js"
STORAGE_KEY = "pi_executive_theme_preview_v1"
SCOPE = '#app-shell[data-preview-theme="executive"]'


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_preview_files_are_loaded_with_cache_busting() -> None:
    html = read(INDEX)
    assert CSS.is_file() and JS.is_file()
    assert './css/themes/executive-preview.css?v=2.7.0-executive-preview-1' in html
    assert './js/modules/theme-executive-preview.js?v=2.7.0-executive-preview-1' in html
    assert html.index('executive-preview.css') < html.index('accessibility-pi.css')
    assert html.index('app.js?v=') < html.index('theme-executive-preview.js')


def test_preview_is_local_superadmin_only_and_disabled_by_default() -> None:
    js = read(JS)
    assert "const DEFAULT_ENABLED = false" in js
    assert "SUPERADMIN" in js
    assert STORAGE_KEY in js
    assert "localStorage.setItem(STORAGE_KEY" in js
    assert "localStorage.removeItem(STORAGE_KEY)" in js
    assert "dataset.previewTheme" in js
    assert "delete shell.dataset.previewTheme" in js
    assert "executive" in js and "institutional" in js


def test_preview_has_no_network_routes_or_protected_data_operations() -> None:
    combined = read(JS) + "\n" + read(CSS)
    forbidden = (
        "fetch(", "XMLHttpRequest", "WebSocket", "/api/", "DATABASE_URL",
        "indexedDB", "document.cookie", "CREATE TABLE", "ALTER TABLE",
        "DROP TABLE", "navigator.serviceWorker",
    )
    assert all(token not in combined for token in forbidden)
    assert not re.search(r"\.(docx|xlsx|xls|pdf)\b", combined, re.IGNORECASE)


def test_css_is_scoped_and_print_is_neutralized() -> None:
    css = read(CSS)
    selectors = []
    for line in css.splitlines():
        candidate = line.strip().removesuffix(",").removesuffix("{").strip()
        if line.strip().endswith(("{", ",")) and candidate and not candidate.startswith(("@", "/*")):
            selectors.append(candidate)
    assert selectors
    assert all(selector.startswith("#app-shell") for selector in selectors)
    assert SCOPE in css
    assert "@media print" in css
    assert "data-preview-theme" in css
    assert "!important" not in css
    protected = (".print-area", ".print-target-active", ".formato-rpp", ".formato-ram", ".formato-bienestarina")
    assert all(name not in css for name in protected)


def test_restore_control_is_accessible_and_logout_is_observed() -> None:
    js = read(JS)
    assert "Restaurar Tema Institucional" in js
    assert "Vista previa Tema Ejecutivo" in js
    assert "aria-live" in js
    assert "cerrarSesion" in js
    assert "addEventListener('click'" in js
    assert "MutationObserver" in js
