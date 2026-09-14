from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_workspace_dock_assets_are_loaded_with_cachebuster():
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    assert "workspace-dock-themes.css?v=2.7.5-dock-themes-1" in html
    assert "workspace-dock-themes.js?v=2.7.5-dock-themes-1" in html


def test_workspace_theme_is_persistent_and_accessible():
    js = (ROOT / "frontend" / "js" / "modules" / "workspace-dock-themes.js").read_text(encoding="utf-8")
    assert "primeraInfanciaWorkspaceThemeV1" in js
    assert "localStorage.setItem" in js
    assert "aria-pressed" in js
    assert "event.key === 'Escape'" in js
    assert "max-width: 1024px" in js


def test_desktop_dock_keeps_mobile_drawer_and_hides_badges():
    css = (ROOT / "frontend" / "css" / "workspace-dock-themes.css").read_text(encoding="utf-8")
    assert '@media (min-width: 1025px)' in css
    assert '@media (max-width: 1024px)' in css
    assert 'width: 76px !important' in css
    assert '.pi-menu-item small' in css
    assert 'display: none !important' in css
    assert 'light-emerald' in css
