"""Contrato del modo Hazlo conmigo: progreso de sesión y pasos obligatorios."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
engine = (ROOT / 'frontend/js/liam/liam-tour-engine.js').read_text(encoding='utf-8')

assert "progressPrefix='liam-tour-progress:'" in engine
assert 'sessionStorage.setItem(progressKey(activeId)' in engine
assert 'readProgress(id,active.length)' in engine
assert "nextFlags.restart===true?0" in engine
assert "if(expected&&!eventConfirmed)" in engine
assert "event.detail?.name===expected)next(true)" in engine
assert "clearProgress(completedId)" in engine
assert "function cancel(){saveProgress()" in engine
assert '.click()' not in engine

print('LIAM_GUIDED_PROGRESS_V7_PASS')
