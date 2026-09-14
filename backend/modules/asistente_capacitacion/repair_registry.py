"""Registro cerrado de reparaciones que LIAM puede proponer."""
from __future__ import annotations

REGISTRY={'integrity_safe_repair':{
    'label':'Reparación segura de integridad',
    'description':'Analiza y aplica solamente correcciones permitidas por el Motor de Integridad.',
    'endpoint':'/api/integrity/safe-repair','roles':['SUPERADMIN'],'risk':'critical',
    'confirmation':'explicit','preview_first':True,'arbitrary_commands':False,
    'business_data_changes':False,
}}

def public_registry(role: str) -> list[dict]:
    normalized=str(role or '').upper()
    return [{'id':key,**value} for key,value in REGISTRY.items() if normalized in value['roles']]

def require_repair(repair_id: str,role: str) -> dict:
    item=REGISTRY.get(str(repair_id or ''))
    if not item:raise PermissionError('La reparación no está registrada en LIAM.')
    if str(role or '').upper() not in item['roles']:raise PermissionError('Tu rol no tiene permiso para ejecutar esta reparación.')
    return {'id':repair_id,**item}
