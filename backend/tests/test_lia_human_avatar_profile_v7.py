"""Avatar desacoplado y ficha institucional no inventada."""
import os
from pathlib import Path
import sys
BACKEND=Path(__file__).resolve().parents[1]; ROOT=BACKEND.parent
sys.path.insert(0,str(BACKEND))
from modules.asistente_capacitacion.platform_profile import get_platform_profile
from modules.asistente_capacitacion.assistant_service import respond

os.environ.pop('LIA_PLATFORM_DESIGNER',None);os.environ.pop('LIA_PLATFORM_CREATED_DATE',None)
assert get_platform_profile()['identity_confirmed'] is False
answer=respond(question='¿Quién diseñó y en qué fecha se creó?',module='dashboard',role='SUPERADMIN')
assert answer['confidence']=='insufficient' and 'no debo inventarlas' in answer['message']
assert (ROOT/'frontend/assets/lia/lia-human-v1.png').stat().st_size>100_000
avatar=(ROOT/'frontend/js/lia-assistant/avatar-controller.js').read_text(encoding='utf-8')
for state in ('idle','listening','thinking','speaking','guiding','success','warning','error'):
    assert state in avatar
print('LIA_HUMAN_AVATAR_PROFILE_V7_PASS')
