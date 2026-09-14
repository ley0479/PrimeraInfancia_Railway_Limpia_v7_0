"""Orquestador central: contexto → herramienta → permiso → servicio → trazabilidad."""
from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any
import uuid

from .capability_registry import describe
from .tool_registry import execute


@dataclass(frozen=True)
class ToolOutcome:
    result: dict
    telemetry: dict


def _data_only(value: Any, depth: int = 0) -> Any:
    """Normaliza argumentos como datos; nunca los interpreta como instrucciones."""
    if depth > 5: raise ValueError('Los parámetros de la herramienta son demasiado profundos.')
    if isinstance(value,dict):
        if len(value)>40: raise ValueError('La herramienta recibió demasiados parámetros.')
        return {str(key)[:80]:_data_only(item,depth+1) for key,item in value.items()}
    if isinstance(value,list):return [_data_only(item,depth+1) for item in value[:200]]
    if isinstance(value,str):return value[:2000]
    if value is None or isinstance(value,(bool,int,float)):return value
    return str(value)[:2000]


class LiamOrchestrator:
    def __init__(self,database_path: str):self.database_path=database_path

    def run(self,tool_name: str,*,args: dict|None,tenant_id: int,user: dict,module: str='',request_id: str='') -> ToolOutcome:
        trace_id=str(request_id or uuid.uuid4().hex)[:64]
        capability=describe(tool_name)
        if not capability:raise PermissionError('La capacidad solicitada no está registrada en LIAM.')
        started=perf_counter()
        result=execute(tool_name,args=_data_only(args or {}),database_path=self.database_path,tenant_id=int(tenant_id),user=dict(user or {}))
        elapsed=round((perf_counter()-started)*1000,2)
        scope=result.get('scope') if isinstance(result,dict) else None
        if capability.get('tenant_scoped') and isinstance(scope,dict):
            returned=scope.get('foundation_id')
            if returned is not None and int(returned)!=int(tenant_id):
                raise PermissionError('La herramienta devolvió un alcance institucional no autorizado.')
        telemetry={'trace_id':trace_id,'tool':tool_name,'engine':capability['engine'],'source':capability['source'],'tenant_scoped':capability['tenant_scoped'],'read_only':capability['read_only'],'duration_ms':elapsed,'module':str(module or '')[:80]}
        return ToolOutcome(result=result,telemetry=telemetry)

