"""Compromisos posteriores: borradores validados, sin escritura."""
from pathlib import Path
import sys
BACKEND=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BACKEND))
from modules.asistente_capacitacion.tool_registry import execute

args={'commitments':[{'title':'Revisar informe','responsible':'Ana','due_date':'2026-09-30'},{'title':'Cargar evidencia','responsible':'','due_date':'2026-02-31'}]}
result=execute('prepare_meeting_followup',args=args,database_path='unused',tenant_id=7,user={'id':2,'rol':'COORDINADOR'})
assert result['scope']['foundation_id']==7 and result['tasks_created'] is False and result['draft_only'] is True
assert result['summary']=={'total':2,'complete':1,'incomplete':1}
assert result['commitments'][0]['ready_for_confirmation'] is True
assert result['commitments'][1]['missing']==['responsable','fecha']
try:execute('prepare_meeting_followup',args=args,database_path='unused',tenant_id=7,user={'id':3,'rol':'DOCENTE'})
except PermissionError:pass
else:raise AssertionError('Un rol no autorizado preparó seguimiento gerencial.')
print('LIAM_MEETING_FOLLOWUP_V7_PASS')
