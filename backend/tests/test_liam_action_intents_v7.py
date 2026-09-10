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


if __name__=='__main__':
    test_rpp_action_requires_missing_group_instead_of_guessing()
    test_complete_rpp_action_is_still_confirmation_required()
    test_non_action_does_not_create_proposal()
    test_navigation_and_read_only_intents_are_closed_actions()
    test_ram_master_user_and_foundation_proposals()
    print('LIAM_ACTION_INTENTS_V7_PASS')
