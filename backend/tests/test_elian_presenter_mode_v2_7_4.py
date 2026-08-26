"""Contrato del modo presentador no invasivo de ELIAN."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


controller = read("frontend/js/liam/liam-controller.js")
tour = read("frontend/js/liam/elian-platform-tour.js")
styles = read("frontend/css/elian-presenter.css")
index = read("frontend/index.html")
config = read("backend/modules/asistente_capacitacion/config.py")

assert 'id="elian-presenter"' in controller
assert 'id="elian-presenter-caption"' in controller
assert 'data-action="elian-pause"' in controller
assert 'data-action="elian-repeat"' in controller
assert 'data-action="elian-mute"' in controller
assert 'data-action="elian-prev"' in controller
assert 'data-action="elian-next"' in controller
assert 'data-action="elian-cancel"' in controller
assert "function enterPresenter()" in controller
assert "function exitPresenter(" in controller
assert "enterPresenter,mode:'automatic'" in controller
assert "options.enterPresenter?.()" in tour
assert "enterPresenter();announce(msg)" in controller
assert "document.body.classList.add('elian-presenter-active')" in controller
assert "document.body.classList.remove('elian-presenter-active')" in controller
assert "window.LIAM_MOVEMENT?.remove()" in controller
assert "pointer-events: none" in styles
assert ".liam-panel { width: min(380px" in styles
assert '.liam-shell[data-mode="presenter"] > .liam-panel' in styles
assert "elian-presenter.css?v=2.7.4-presenter-1" in index
assert "liam-controller.js?v=2.7.4-presenter-1" in index
assert "Esta plataforma fue diseñada por" in tour
assert "fue creada el" in tour
assert "Su versión actual es" in tour
assert "profile.description" in tour
assert "await options.announceAsync(`Recorrido completado" in tour
for key in (
    "ui_mode", "chat_panel_mode", "chat_panel_max_width", "tour_panel_mode",
    "presenter_overlay", "captions_enabled", "compact_controls_enabled",
    "transcript_enabled", "diagnostics_enabled", "diagnostics_read_only",
):
    assert f"'{key}'" in config

print("ELIAN_PRESENTER_MODE_V2_7_4_PASS")
