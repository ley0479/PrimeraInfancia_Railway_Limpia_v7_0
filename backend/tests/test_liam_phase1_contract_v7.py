"""Contrato aditivo de LIAM: apagado seguro, registros cerrados y UI no invasiva."""
from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))

from modules.asistente_capacitacion.config import public_liam_flags


def read(relative):
    return (ROOT / relative).read_text(encoding='utf-8')


os.environ.pop('ENABLE_LIAM_ASSISTANT', None)
flags = public_liam_flags()
assert flags['enabled'] is False
assert flags['walk_enabled'] is False
assert flags['realtime_voice_enabled'] is False

os.environ['ENABLE_LIAM_ASSISTANT'] = 'true'
flags = public_liam_flags()
assert flags['enabled'] is True
assert flags['teleport_enabled'] is True
assert flags['walk_enabled'] is False

state = read('frontend/js/liam/liam-state-machine.js')
for name in ('idle', 'listening', 'thinking', 'speaking', 'walking_left', 'pointing_right', 'teleport_in', 'success', 'warning', 'error'):
    assert name in state

registry = read('frontend/js/liam/liam-control-registry.js')
assert 'querySelector(item.selector)' in registry
assert 'eval(' not in registry
assert 'new Function' not in registry

controller = read('frontend/js/liam/liam-controller.js')
assert 'LIAM no se cargó' in controller
assert 'd.liam||{}' in controller
assert 'innerHTML=' not in controller

css = read('frontend/css/liam-assistant.css')
assert '.liam-shell' in css
assert 'pointer-events:none' in css
assert '@media(max-width:768px)' in css
assert 'prefers-reduced-motion:reduce' in css

html = read('frontend/index.html')
assert 'liam-controller.js' in html
assert 'data-help-id="base-maestra.units.process"' in html

asset = ROOT / 'frontend/assets/lia/liam-poster-v1.png'
assert asset.exists() and asset.stat().st_size > 100_000
png_header = asset.read_bytes()[:26]
assert png_header[:8] == b'\x89PNG\r\n\x1a\n'

print('LIAM_PHASE1_CONTRACT_V7_PASS')
