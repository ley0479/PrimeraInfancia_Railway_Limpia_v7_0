from modules.asistente_capacitacion.action_policy import decision, require


def test_unknown_actions_are_denied():
    result=decision('invented_write_tool','SUPERADMIN')
    assert result['allowed'] is False


def test_read_and_navigation_do_not_require_confirmation():
    for action in ('open_module','search_beneficiary','get_pending_activities_summary'):
        result=decision(action,'DOCENTE')
        assert result['allowed'] is True
        assert result['confirmation']=='none'


def test_generation_requires_explicit_confirmation():
    result=decision('download_rpp','DOCENTE')
    assert result['allowed'] is True
    assert result['risk']=='generation'
    assert result['confirmation']=='explicit'


def test_credit_mutations_are_superadmin_only():
    for action in ('add_credits','renew_days','suspend_subscription'):
        assert decision(action,'SUPERADMIN')['allowed'] is True
        assert decision(action,'GERENTE')['allowed'] is False


def test_disconnected_write_operations_fail_closed():
    assert decision('replace_master_database','SUPERADMIN')['allowed'] is False
    visible=decision('replace_master_database','SUPERADMIN',require_connected=False)
    assert visible['allowed'] is True
    assert visible['connected'] is False
    try:
        require('replace_master_database','SUPERADMIN')
    except PermissionError:
        pass
    else:
        raise AssertionError('Una operación no conectada no puede ejecutarse.')


def test_validated_motors_are_connected_with_role_limits():
    assert decision('download_ram','DOCENTE')['allowed'] is True
    assert decision('publish_master_database','GERENTE')['allowed'] is True
    assert decision('update_user','GERENTE')['allowed'] is False
    assert decision('update_user','SUPERADMIN')['allowed'] is True
    assert decision('update_foundation','SUPERADMIN')['allowed'] is True
    assert decision('create_user','SUPERADMIN')['allowed'] is True
    assert decision('create_foundation','GERENTE')['allowed'] is False
    assert decision('consolidate_master_database','NUTRICIONISTA')['allowed'] is True


if __name__=='__main__':
    test_unknown_actions_are_denied()
    test_read_and_navigation_do_not_require_confirmation()
    test_generation_requires_explicit_confirmation()
    test_credit_mutations_are_superadmin_only()
    test_disconnected_write_operations_fail_closed()
    test_validated_motors_are_connected_with_role_limits()
    print('PASS: política central de acciones LIAN')
