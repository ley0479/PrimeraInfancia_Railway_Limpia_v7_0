"""Contrato de identidad, cobertura y recuperación conversacional de LIAM."""
from pathlib import Path
import os, sys

BACKEND=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND))

from modules.asistente_capacitacion.assistant_service import respond
from modules.asistente_capacitacion.config import public_elian_flags
from modules.asistente_capacitacion.knowledge_base import load_knowledge, manual_for_role, manual_for_question
from modules.asistente_capacitacion.elian_module_registry import ELIAN_MODULE_REGISTRY

for key in ('LIAM_ASSISTANT_NAME','IAN_ASSISTANT_NAME','ELIAN_ASSISTANT_NAME','LIAM_AVATAR_GENDER','ELIAN_AVATAR_GENDER'):
    os.environ.pop(key,None)
flags=public_elian_flags()
assert flags['assistant_name']=='LIAM'
assert flags['avatar_gender']=='female'

knowledge=load_knowledge()
known={item['module_id'] for item in knowledge['modules']}
required={item['module_id'] for item in ELIAN_MODULE_REGISTRY}
assert required<=known,(required-known)

manual=manual_for_role('COORDINADOR',module_id='base-maestra')
answer=respond(question='¿Cómo cargo el archivo Cuéntame?',module='base-maestra',role='COORDINADOR',allowed_modules=['dashboard','base-maestra'],knowledge=manual)
assert answer['confidence']=='confirmed'
assert answer['evidence']
assert 'Cuéntame' in answer['message']

unknown=respond(question='¿Puedes inventar una regla que no está documentada?',module='base-maestra',role='COORDINADOR',knowledge=manual)
assert unknown['confidence']=='insufficient'

complete=manual_for_question('COORDINADOR',module_id='dashboard')
assert complete['manual_scope']=='all_authorized_modules'
assert {'dashboard','base-maestra'}<={item['module_id'] for item in complete['modules']}
cross_module=respond(question='¿Cómo cargo el archivo Cuéntame?',module='dashboard',role='COORDINADOR',allowed_modules=['dashboard','base-maestra'],knowledge=complete)
assert cross_module['confidence']=='confirmed'
assert cross_module['evidence'] and 'Cuéntame' in cross_module['message']

print('LIAM_CONVERSATIONAL_FOUNDATION_V7_PASS')
