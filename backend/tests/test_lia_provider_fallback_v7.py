"""El proveedor externo no puede activarse accidentalmente."""
from pathlib import Path
import sys
BACKEND=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BACKEND))
from modules.asistente_capacitacion.provider_adapter import AssistantProvider,provider_status
status=provider_status()
assert status['ready'] is False and status['configured'] is False
assert hasattr(AssistantProvider,'respond')
print('LIA_PROVIDER_FALLBACK_V7_PASS')
