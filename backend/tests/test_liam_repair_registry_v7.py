"""Registro de reparaciones cerrado y autorizado."""
from pathlib import Path
import sys
BACKEND=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BACKEND))
from modules.asistente_capacitacion.repair_registry import public_registry,require_repair

allowed=public_registry('SUPERADMIN')
assert len(allowed)==1 and allowed[0]['id']=='integrity_safe_repair'
assert allowed[0]['preview_first'] is True and allowed[0]['arbitrary_commands'] is False
assert public_registry('GERENTE')==[]
try:require_repair('shell_command','SUPERADMIN')
except PermissionError:pass
else:raise AssertionError('Se aceptó una reparación fuera del registro.')
try:require_repair('integrity_safe_repair','GERENTE')
except PermissionError:pass
else:raise AssertionError('Un rol no autorizado accedió a la reparación.')
print('LIAM_REPAIR_REGISTRY_V7_PASS')
