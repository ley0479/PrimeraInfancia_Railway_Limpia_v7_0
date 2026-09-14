from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_workspace_dock_assets_are_loaded_with_cachebuster():
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    assert "workspace-dock-themes.css?v=2.7.5-dock-themes-6" in html
    assert "workspace-dock-themes.js?v=2.7.5-dock-themes-6" in html
    assert html.index("responsive-mobile.css") < html.index("workspace-dock-themes.css")


def test_workspace_theme_is_persistent_and_accessible():
    js = (ROOT / "frontend" / "js" / "modules" / "workspace-dock-themes.js").read_text(encoding="utf-8")
    assert "primeraInfanciaWorkspaceThemeV1" in js
    assert "localStorage.setItem" in js
    assert "aria-pressed" in js
    assert "event.key === 'Escape'" in js
    assert "item.addEventListener('dblclick', execute)" in js
    assert "data-dock-selected" in js
    assert "pointerleave" not in js
    assert "!openGroup.contains(event.target)" not in js
    assert "max-width: 1024px" in js


def test_desktop_dock_keeps_mobile_drawer_and_hides_badges():
    css = (ROOT / "frontend" / "css" / "workspace-dock-themes.css").read_text(encoding="utf-8")
    assert '@media (min-width: 1025px)' in css
    assert '@media (max-width: 1024px)' in css
    assert 'width: 230px !important' in css
    assert '--workspace-sidebar: #425573' in css
    assert '--workspace-dock: #2d3d56' in css
    assert '--workspace-header: #2d3c53' in css
    assert '--workspace-sidebar: #f6f7fb' in css
    assert 'left: 73px' in css
    assert '.liam-panel' in css
    assert 'font-weight: 700' in css
    assert 'color: #000 !important' in css
    assert '--pi-surface: #ffffff !important' in css
    assert '.ci-calendar-grid' in css
    assert 'section [class*="-card"]' in css
    assert '.pi-menu-item small' in css
    assert 'display: none !important' in css
    assert 'light-emerald' in css
