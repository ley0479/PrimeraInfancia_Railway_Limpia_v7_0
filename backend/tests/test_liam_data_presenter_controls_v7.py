"""La explicación visual permite seguimiento por voz y navegación manual accesible."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
controller=(ROOT/'frontend/js/liam/liam-controller.js').read_text(encoding='utf-8')
styles=(ROOT/'frontend/css/lia-dynamic-ui.css').read_text(encoding='utf-8')
index=(ROOT/'frontend/index.html').read_text(encoding='utf-8')

for marker in ('data-lia-presenter-avatar','data-lia-presenter-status','data-lia-presenter-action="previous"','data-lia-presenter-action="next"','role="status"','aria-live="polite"'):assert marker in controller
assert 'activatePresentationItem((state.dataPresentation?.index||0)-1)' in controller
assert 'activatePresentationItem((state.dataPresentation?.index||0)+1)' in controller
assert 'prefers-reduced-motion: reduce' in controller and 'behavior: reduced ? "auto" : "smooth"' in controller
assert '.lia-data-point.lia-data-active' in styles and '.lia-data-point.lia-data-explained' in styles
assert '.lia-presenter-controls' in styles and ':focus-visible' in styles
assert 'lia-dynamic-ui.css?v=2.7.5-presenter-controls-1' in index
assert 'liam-controller.js?v=2.7.5-action-history-1' in index
print('LIAM_DATA_PRESENTER_CONTROLS_V7_PASS')
