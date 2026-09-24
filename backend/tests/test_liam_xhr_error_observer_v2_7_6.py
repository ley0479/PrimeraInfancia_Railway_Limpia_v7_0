from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_liam_observes_fetch_and_legacy_xhr_errors():
    observer = (ROOT / 'frontend' / 'js' / 'liam' / 'liam-error-observer.js').read_text(encoding='utf-8')

    assert 'window.fetch=async function' in observer
    assert 'XMLHttpRequest.prototype.open' in observer
    assert "this.addEventListener('loadend'" in observer
    assert "notify(JSON.parse(this.responseText||'{}'),this.status)" in observer
    assert 'notified.has(incident)' in observer


def test_liam_opens_when_an_incident_arrives():
    controller = (ROOT / 'frontend' / 'js' / 'liam' / 'liam-controller.js').read_text(encoding='utf-8')
    handler = controller.split('document.addEventListener("liam:platform-error"', 1)[1].split(
        'document.addEventListener("liam:operational-error"', 1
    )[0]

    assert 'open();' in handler
    assert 'LIA_SPEECH?.speak(message)' in handler
    assert '2.7.6-liam-errors-1' in controller
