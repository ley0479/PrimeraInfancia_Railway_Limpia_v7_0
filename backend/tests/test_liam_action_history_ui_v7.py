from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
index=(ROOT/'frontend'/'index.html').read_text(encoding='utf-8')
controller=(ROOT/'frontend'/'js'/'liam'/'liam-controller.js').read_text(encoding='utf-8')
assert 'id="liam-action-history"' in index and 'id="liam-action-history-content"' in index
assert 'data-action="liam-action-history"' in index
assert 'aria-controls="liam-action-history-content"' in index and 'aria-live="polite"' in index
assert "request('/actions/history?limit=50')" in controller
assert "cell.textContent=String(value??'—')" in controller
assert "host.setAttribute('aria-busy','true')" in controller and "cell.scope='col'" in controller
assert 'Acciones ejecutadas mediante LIAM en la fundación activa' in controller
assert 'innerHTML' not in controller[controller.index('async function viewActionHistory'):controller.index('async function viewHistoryStats')]
assert 'liam-controller.js?v=2.7.5-action-history-2' in index
print('LIAM_ACTION_HISTORY_UI_V7_PASS')
