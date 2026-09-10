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


def test_non_action_does_not_create_proposal():
    assert propose_action('Explícame qué es el RPP') is None


def test_navigation_and_read_only_intents_are_closed_actions():
    assert propose_action('Lian, abre el calendario')['arguments']['module'] == 'calendario-inteligente'
    assert propose_action('Muéstrame mis entregables pendientes')['server_tool'] == 'get_pending_activities_summary'
    search = propose_action('Busca el niño con documento 1077456789')
    assert search['client_handler'] == 'search_beneficiary'
    assert search['arguments']['query'] == '1077456789'
