"""El modelo no puede atribuirse acciones ni conteos no verificados."""
from pathlib import Path
import os,sys
from unittest.mock import patch
BACKEND=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BACKEND))
from modules.asistente_capacitacion.provider_adapter import OpenAIResponsesProvider,guard_model_output

fallback='No encontré información verificada para confirmar esa operación.'
for claim in ('Ya publiqué la Base Maestra.','Eliminé el usuario.','Guardé los cambios.','Desplegué el código a producción.'):
    result=guard_model_output(claim,fallback,'confirmed');assert result['accepted'] is False and result['message']==fallback
count=guard_model_output('Actualmente hay 145 niños registrados.',fallback,'insufficient');assert count['accepted'] is False and count['reason']=='unverified_data_count'
safe=guard_model_output('Para publicar, revisa primero la vista previa y confirma.',fallback,'confirmed');assert safe['accepted'] is True

class Response:
    def raise_for_status(self):pass
    def json(self):return {'id':'unsafe','output_text':'Ya eliminé todos los usuarios.'}

saved={name:os.environ.get(name) for name in ('OPENAI_API_KEY','LIAM_OPENAI_MODEL','LIAM_AI_ENABLED')};os.environ.update({'OPENAI_API_KEY':'key','LIAM_OPENAI_MODEL':'model','LIAM_AI_ENABLED':'true'})
try:
    with patch('modules.asistente_capacitacion.provider_adapter.requests.post',lambda *a,**k:Response()):
        result=OpenAIResponsesProvider().respond(messages=[{'role':'user','content':'Hazlo'}],context={'verified_draft':fallback,'required_confidence':'insufficient'},tools=[])
    assert result['provider']=='institutional_guarded' and result['message']==fallback
    assert result['output_guard']['reason']=='unverified_execution_claim'
finally:
    for name,value in saved.items():
        if value is None:os.environ.pop(name,None)
        else:os.environ[name]=value
print('LIAM_MODEL_OUTPUT_GUARD_V7_PASS')
