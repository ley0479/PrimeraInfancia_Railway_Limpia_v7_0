from modules.asistente_capacitacion.action_intents import propose_action


def test_rpp_action_requires_missing_group_instead_of_guessing():
    value = propose_action('Lian, genera el RPP de Bajo Pacurita para septiembre', screen_context={'selected_year': 2026})
    assert value['arguments']['unit'] == 'Bajo Pacurita'
    assert value['arguments']['month'] == 9
    assert value['arguments']['year'] == 2026
    assert value['arguments']['group'] is None
    assert value['missing'] == ['grupo etario']


def test_complete_rpp_action_is_still_confirmation_required():
    value = propose_action('Genera el RPP de Bajo Pacurita para septiembre de 2026, grupo 3 a 5 años')
    assert value['arguments'] == {'unit': 'Bajo Pacurita', 'month': 9, 'year': 2026, 'group': '3_5_ANOS'}
    assert value['missing'] == []
    assert value['confirmation_required'] is True


def test_bienestarina_uses_exact_spoken_unit_and_valid_period_context():
    value = propose_action('Ian, necesito el formato de Bienestarina de la unidad 15', screen_context={'selected_month': 9, 'selected_year': 2026})
    assert value['id'] == 'download_bienestarina'
    assert value['arguments'] == {'unit': '15', 'month': 9, 'year': 2026, 'module': 'formatos'}
    assert value['missing'] == []
    assert value['confirmation_required'] is False


def test_bienestarina_requests_missing_period_instead_of_inventing_it():
    value = propose_action('Sácame Bienestarina de la unidad 15')
    assert value['arguments']['unit'] == '15'
    assert value['missing'] == ['mes', 'año']


def test_non_action_does_not_create_proposal():
    assert propose_action('Explícame qué es el RPP') is None


def test_navigation_and_read_only_intents_are_closed_actions():
    assert propose_action('Lian, abre el calendario')['arguments']['module'] == 'calendario-inteligente'
    assert propose_action('Muéstrame mis entregables pendientes')['server_tool'] == 'get_pending_activities_summary'
    pending = propose_action('Muéstrame los pendientes de mi equipo de septiembre de 2026')
    assert pending['arguments'] == {'period': '2026-09', 'scope': 'team'}
    search = propose_action('Busca el niño con documento 1077456789')
    assert search['server_tool'] == 'search_foundation_beneficiaries'
    assert search['arguments']['query'] == '1077456789'
    assert search['arguments']['query'] == '1077456789'


def test_ram_master_user_and_foundation_proposals():
    ram=propose_action('Genera el RAM de Bajo Pacurita para septiembre de 2026')
    assert ram['id']=='download_ram' and ram['arguments']['month']==9 and ram['confirmation_required'] is True
    master=propose_action('Publica la Base Maestra versión 17')
    assert master['id']=='publish_master_database' and master['arguments']['version_id']==17
    user=propose_action('Suspende usuario 42')
    assert user['id']=='update_user' and user['arguments']=={'user_id':42,'active':False,'module':'administracion'}
    foundation=propose_action('Reactiva fundación 8')
    assert foundation['id']=='update_foundation' and foundation['arguments']['active'] is True
    consolidate=propose_action('Consolida la Base Maestra')
    assert consolidate['id']=='consolidate_master_database'
    create_user=propose_action('Crea usuario usuario docente.pacifico correo docente@pacifico.org rol docente fundación 8')
    assert create_user['id']=='create_user' and create_user['missing']==[]
    create_foundation=propose_action('Crea una fundación llamada Nuevo Amanecer con NIT 900.123.456-7')
    assert create_foundation['id']=='create_foundation' and create_foundation['arguments']['name']=='Nuevo Amanecer'


def test_monthly_relation_and_nutrition_report_requires_confirmation():
    value=propose_action('Genera la Relación del Mes y el informe nutricional de septiembre de 2026')
    assert value['id']=='generate_monthly_reports'
    assert value['arguments']['month']==9 and value['arguments']['year']==2026
    assert value['confirmation_required'] is True


def test_period_comparison_uses_two_explicit_months_and_context_year():
    value = propose_action(
        'Liam compara agosto contra septiembre',
        screen_context={'selected_year': 2026},
    )
    assert value['server_tool'] == 'compare_periods'
    assert value['arguments'] == {'period_a': '2026-08', 'period_b': '2026-09'}
    assert value['missing'] == []
    assert value['confirmation_required'] is False


def test_custom_report_intent_maps_only_predefined_fields():
    value = propose_action('Liam crea un reporte con unidad, docente y número de niños')
    assert value['server_tool'] == 'build_custom_report_preview'
    assert value['arguments']['report'] == 'unit_coverage'
    assert value['arguments']['fields'] == ['unit', 'teacher', 'children_count']
    assert value['confirmation_required'] is False


def test_deliverable_supervisor_intent_uses_selected_period():
    value = propose_action('Liam supervisa los entregables de septiembre de 2026')
    assert value['server_tool'] == 'supervise_deliverables'
    assert value['arguments']['period'] == '2026-09'
    assert value['confirmation_required'] is False


def test_system_health_intent_is_closed_tool():
    value = propose_action('Liam, dime el estado del sistema')
    assert value['server_tool'] == 'get_system_health'
    assert value['confirmation_required'] is False


def test_backup_status_intent_is_read_only():
    value=propose_action('Liam cuál es el estado de las copias de seguridad')
    assert value['server_tool']=='get_backup_status'
    assert value['confirmation_required'] is False


def test_module_usage_intent_is_read_only_and_bounded():
    value=propose_action('Liam muéstrame los módulos poco usados en 60 días')
    assert value['server_tool']=='get_module_usage' and value['arguments']['days']==60
    assert value['confirmation_required'] is False


def test_foundation_portfolio_intent_is_closed_tool():
    value = propose_action('Liam, cuáles fundaciones están próximas a vencer')
    assert value['server_tool'] == 'get_foundation_portfolio'
    assert value['confirmation_required'] is False


def test_master_quality_intent_never_requests_mutation():
    value = propose_action('Liam revisa la calidad de la Base Maestra')
    assert value['server_tool'] == 'analyze_master_data_quality'
    assert value['confirmation_required'] is False


def test_early_warning_intent_uses_risk_language():
    value=propose_action('Liam muéstrame las alertas tempranas de septiembre de 2026')
    assert value['server_tool']=='get_early_warnings'
    assert value['arguments']['period']=='2026-09'
    assert value['confirmation_required'] is False


def test_incident_center_intent_filters_open_items():
    value=propose_action('Liam muéstrame mis incidencias abiertas')
    assert value['server_tool']=='get_incident_center'
    assert value['arguments']['status']=='OPEN'
    assert value['confirmation_required'] is False


def test_known_solution_intent_requires_explicit_error_code():
    value=propose_action('Liam busca una solución conocida para DOC_RPP_002')
    assert value['server_tool']=='get_known_solution'
    assert value['arguments']['code']=='DOC_RPP_002'
    assert value['confirmation_required'] is False


def test_technical_diagnostic_intent_requires_incident_id():
    value=propose_action('Liam muéstrame el diagnóstico técnico de INC-20260914-150000-AAAAAA')
    assert value['server_tool']=='get_technical_diagnostic'
    assert value['arguments']['incident_id']=='INC-20260914-150000-AAAAAA'
    assert value['confirmation_required'] is False


def test_notification_center_intent_is_read_only():
    value=propose_action('Liam qué notificaciones tengo')
    assert value['server_tool']=='get_notification_center'
    assert value['confirmation_required'] is False


def test_communication_intent_creates_draft_not_send_action():
    value=propose_action('Liam prepara un aviso para los docentes con pendientes de septiembre de 2026')
    assert value['server_tool']=='prepare_communication_draft'
    assert value['arguments']=={'audience':'pending_deliverables','period':'2026-09'}
    assert value['confirmation_required'] is False


def test_favorite_intent_resolves_name_without_executing_locally():
    value=propose_action('Liam ejecuta Pendientes docentes')
    assert value['server_tool']=='run_command_favorite'
    assert value['arguments']['name']=='pendientes docentes'


def test_liam_center_intent_is_closed_read_only_tool():
    value=propose_action('Liam muéstrame el Centro Liam')
    assert value['server_tool']=='get_liam_center'
    assert value['confirmation_required'] is False


def test_role_dashboard_uses_session_period_and_requested_scope():
    value=propose_action('Liam muéstrame mi tablero del equipo',screen_context={'selected_period':'2026-09'})
    assert value['server_tool']=='get_role_dashboard'
    assert value['arguments']=={'period':'2026-09','scope':'team'}
    assert value['confirmation_required'] is False


def test_meeting_brief_uses_context_without_creating_tasks():
    value=propose_action('Liam prepara la reunión',screen_context={'selected_period':'2026-09'})
    assert value['server_tool']=='prepare_meeting_brief'
    assert value['arguments']=={'period':'2026-09'} and value['confirmation_required'] is False


def test_meeting_followup_extracts_only_a_draft():
    value=propose_action('Liam compromisos de la reunión compromiso: revisar informe; responsable: Ana; fecha: 2026-09-30')
    assert value['server_tool']=='prepare_meeting_followup'
    assert value['arguments']['commitments']==[{'title':'revisar informe','responsible':'ana','due_date':'2026-09-30'}]
    assert value['confirmation_required'] is False


def test_admin_dev_request_is_a_draft_not_code_execution():
    value=propose_action('Liam necesito agregar un filtro en Base Maestra')
    assert value['server_tool']=='prepare_dev_change_request'
    assert value['arguments']['module']=='base-maestra' and value['confirmation_required'] is False


def test_admin_dev_review_requires_an_explicit_scoped_request_id():
    value=propose_action('Liam revisa el impacto de DEV-20260914-ABC12345')
    assert value['server_tool']=='get_dev_change_review'
    assert value['arguments']['request_id']=='DEV-20260914-ABC12345'
    assert value['confirmation_required'] is False


def test_safe_repair_requires_confirmation_but_preview_does_not():
    preview=propose_action('Liam muéstrame el plan de reparación')
    assert preview['client_handler']=='safe_repair_preview' and preview['confirmation_required'] is False
    apply=propose_action('Liam repara el sistema')
    assert apply['client_handler']=='safe_repair_apply' and apply['confirmation_required'] is True


if __name__=='__main__':
    test_rpp_action_requires_missing_group_instead_of_guessing()
    test_complete_rpp_action_is_still_confirmation_required()
    test_bienestarina_uses_exact_spoken_unit_and_valid_period_context()
    test_bienestarina_requests_missing_period_instead_of_inventing_it()
    test_non_action_does_not_create_proposal()
    test_navigation_and_read_only_intents_are_closed_actions()
    test_ram_master_user_and_foundation_proposals()
    test_monthly_relation_and_nutrition_report_requires_confirmation()
    test_period_comparison_uses_two_explicit_months_and_context_year()
    test_custom_report_intent_maps_only_predefined_fields()
    test_deliverable_supervisor_intent_uses_selected_period()
    test_system_health_intent_is_closed_tool()
    test_backup_status_intent_is_read_only()
    test_module_usage_intent_is_read_only_and_bounded()
    test_foundation_portfolio_intent_is_closed_tool()
    test_master_quality_intent_never_requests_mutation()
    test_early_warning_intent_uses_risk_language()
    test_incident_center_intent_filters_open_items()
    test_known_solution_intent_requires_explicit_error_code()
    test_technical_diagnostic_intent_requires_incident_id()
    test_notification_center_intent_is_read_only()
    test_communication_intent_creates_draft_not_send_action()
    test_favorite_intent_resolves_name_without_executing_locally()
    test_liam_center_intent_is_closed_read_only_tool()
    test_role_dashboard_uses_session_period_and_requested_scope()
    test_meeting_brief_uses_context_without_creating_tasks()
    test_meeting_followup_extracts_only_a_draft()
    test_admin_dev_request_is_a_draft_not_code_execution()
    test_admin_dev_review_requires_an_explicit_scoped_request_id()
    test_safe_repair_requires_confirmation_but_preview_does_not()
    print('LIAM_ACTION_INTENTS_V7_PASS')
