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
    assert './css/themes/executive-preview.css?v=2.7.0-theme-selector-1' in html
    assert './js/modules/theme-executive-preview.js?v=2.7.0-theme-selector-1' in html
    assert html.index('executive-preview.css') < html.index('accessibility-pi.css')
    assert html.index('app.js?v=') < html.index('theme-executive-preview.js')


def test_preview_is_local_superadmin_only_and_supports_emergency_disable() -> None:
    js = read(JS)
    assert "const DEFAULT_ENABLED = true" in js
    assert "typeof window.__PI_EXECUTIVE_PREVIEW_ENABLED__ === 'boolean'" in js
    assert "SUPERADMIN" in js
    assert STORAGE_KEY in js
    assert "localStorage.setItem(STORAGE_KEY" in js
    assert "localStorage.removeItem(STORAGE_KEY)" in js
    assert "dataset.previewTheme" in js
    assert "delete shell.dataset.previewTheme" in js
    assert all(theme in js for theme in ('executive', 'institutional', 'corporate-glass', 'quantum-dark', 'biotech', 'creator'))


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
    assert "Tema Institucional" in js
    assert "Selector de temas visuales" in js
    assert "Seleccionar tema" in js
    assert "aria-live" in js
    assert "cerrarSesion" in js
    assert "addEventListener('click'" in js
    assert "MutationObserver" in js


def test_control_does_not_share_accessibility_corner() -> None:
    css = read(CSS)
    control = re.search(r'#app-shell > \.pi-executive-preview-control\s*\{([^}]+)\}', css)
    assert control
    declarations = control.group(1)
    assert "left: calc(18.5rem + 18px)" in declarations
    assert "right: auto" in declarations
    assert "left: max(12px, env(safe-area-inset-left, 0px))" in css
