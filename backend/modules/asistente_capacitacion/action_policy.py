"""Política central y cerrada para acciones solicitadas a LIAN."""
from __future__ import annotations

from dataclasses import asdict, dataclass

ALL_AUTHENTICATED = frozenset({'SUPERADMIN','GERENTE','COORDINADOR','DOCENTE','NUTRICIONISTA','PSICOSOCIAL','AUXILIAR_ADMINISTRATIVO'})

@dataclass(frozen=True)
class ActionRule:
    action: str
    risk: str
    roles: frozenset[str]
    confirmation: str = 'none'
    connected: bool = True
    description: str = ''

RULES = {
    'propose_platform_action': ActionRule('propose_platform_action','proposal',ALL_AUTHENTICATED),
    'open_module': ActionRule('open_module','navigation',ALL_AUTHENTICATED,description='Abrir un módulo autorizado.'),
    'search_beneficiary': ActionRule('search_beneficiary','read',ALL_AUTHENTICATED),
    'get_pending_activities_summary': ActionRule('get_pending_activities_summary','read',ALL_AUTHENTICATED),
    'get_document_processing_status': ActionRule('get_document_processing_status','read',ALL_AUTHENTICATED),
    'get_format_generation_status': ActionRule('get_format_generation_status','read',ALL_AUTHENTICATED),
    'get_structured_error': ActionRule('get_structured_error','read',ALL_AUTHENTICATED),
    'download_rpp': ActionRule('download_rpp','generation',ALL_AUTHENTICATED,'explicit'),
    'download_ram': ActionRule('download_ram','generation',ALL_AUTHENTICATED,'explicit'),
    'publish_master_database': ActionRule('publish_master_database','modification',frozenset({'SUPERADMIN','GERENTE','AUXILIAR_ADMINISTRATIVO'}),'explicit'),
    'consolidate_master_database': ActionRule('consolidate_master_database','modification',frozenset({'SUPERADMIN','GERENTE','AUXILIAR_ADMINISTRATIVO','NUTRICIONISTA'}),'explicit'),
    'replace_master_database': ActionRule('replace_master_database','critical',frozenset({'SUPERADMIN'}),'reauthentication',False),
    'create_user': ActionRule('create_user','administration',frozenset({'SUPERADMIN'}),'explicit'),
    'update_user': ActionRule('update_user','administration',frozenset({'SUPERADMIN'}),'explicit'),
    'delete_user': ActionRule('delete_user','critical',frozenset({'SUPERADMIN'}),'reauthentication',False),
    'create_foundation': ActionRule('create_foundation','administration',frozenset({'SUPERADMIN'}),'explicit'),
    'update_foundation': ActionRule('update_foundation','administration',frozenset({'SUPERADMIN'}),'explicit'),
    'delete_foundation': ActionRule('delete_foundation','critical',frozenset({'SUPERADMIN'}),'reauthentication',False),
    'add_credits': ActionRule('add_credits','financial',frozenset({'SUPERADMIN'}),'explicit'),
    'renew_days': ActionRule('renew_days','financial',frozenset({'SUPERADMIN'}),'explicit'),
    'suspend_subscription': ActionRule('suspend_subscription','financial',frozenset({'SUPERADMIN'}),'explicit'),
}

def decision(action: str, role: str, *, require_connected: bool = True) -> dict:
    name=str(action or '').strip(); normalized_role=str(role or '').strip().upper(); rule=RULES.get(name)
    if not rule:return {'allowed':False,'reason':'La acción no está registrada en la política segura de LIAN.','action':name}
    payload=asdict(rule);payload['roles']=sorted(rule.roles)
    if normalized_role not in rule.roles:payload.update(allowed=False,reason='Tu rol no tiene permiso para ejecutar esta operación.')
    elif require_connected and not rule.connected:payload.update(allowed=False,reason='Esta operación todavía no está conectada a un ejecutor seguro de LIAN.')
    else:payload.update(allowed=True,reason='Acción autorizada por la política central.')
    return payload

def require(action: str, role: str, *, require_connected: bool = True) -> dict:
    result=decision(action,role,require_connected=require_connected)
    if not result['allowed']:raise PermissionError(result['reason'])
    return result

def public_policy(role: str) -> list[dict]:
    return [decision(name,role,require_connected=False) for name in sorted(RULES)]
