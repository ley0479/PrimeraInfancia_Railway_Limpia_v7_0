"""Alcances técnicos cerrados para planes ADMIN/DEV; nunca ejecutan código."""
from __future__ import annotations

COMMON_TESTS=('backend/tests/test_elian_http_multitenant_v7.py','backend/tests/test_liam_feature_gate_http_v7.py')
SCOPES={
 'base-maestra':(('backend/modules/base_maestra/routes.py','backend/modules/base_maestra/services.py','backend/modules/base_maestra/repository.py','frontend/js/modules/base-maestra.js'),('backend/tests/test_base_maestra_http_contract.py','backend/tests/test_rpp_tenant_base_maestra_v2_7_2.py')),
 'calendario-inteligente':(('backend/modules/calendario_inteligente/routes.py','backend/modules/calendario_inteligente/services.py','backend/modules/calendario_inteligente/repository.py','frontend/js/modules/calendario-inteligente.js'),('backend/tests/test_attendance_calendar_integration_v2_7_0.py',)),
 'salud-nutricion':(('backend/modules/salud_nutricion/routes.py','backend/modules/salud_nutricion/services.py','backend/modules/salud_nutricion/repository.py'),('backend/tests/test_salud_nutricion_integral_v2_6_0.py',)),
 'talento':(('backend/modules/talento_humano/routes.py','backend/modules/talento_humano/services.py','backend/modules/talento_humano/repository.py'),('backend/tests/test_base_maestra_talento_mapping.py',)),
 'relacion-mes':(('backend/services/relacion_mes_service.py','frontend/js/modules/relacion-mes.js'),('backend/tests/test_relacion_mes_service.py','backend/tests/test_relacion_mes_age_ranges_regression_v2_7_4.py')),
 'facturacion':(('backend/modules/facturacion_suscripcion/routes.py','backend/modules/facturacion_suscripcion/services.py','backend/modules/facturacion_suscripcion/repository.py'),()),
 'administracion':(('backend/modules/seguridad/routes.py','backend/modules/seguridad/services.py','frontend/js/app.js'),('backend/tests/test_tunnel_admin_recovery_v2_4_1.py',)),
 'backups':(('backend/modules/backups/routes.py','backend/modules/backups/services.py','frontend/js/modules/backups.js'),('backend/tests/test_backup_restore_reauthentication_v7.py',)),
 'dashboard':(('frontend/index.html','frontend/js/app.js'),()),
 'manual-operativo':(('backend/modules/asistente_capacitacion/knowledge_base.py','frontend/js/liam/manual-maestro.js'),('backend/tests/test_liam_manual_master_v7.py',)),
}

def plan_for(module):
    key=str(module or '').strip().lower();files,tests=SCOPES.get(key,((),()))
    if not files:raise ValueError('El módulo todavía no tiene un alcance técnico cerrado para sandbox.')
    return {'module':key,'allowed_files':list(files),'test_files':list(dict.fromkeys((*tests,*COMMON_TESTS))),'forbidden_paths':['.env','.git','railway.json','datos productivos','backups físicos'],'commands_generated':False,'deployment_allowed':False}
