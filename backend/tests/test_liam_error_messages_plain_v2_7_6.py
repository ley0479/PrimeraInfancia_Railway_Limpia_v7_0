from backend.modules.asistente_capacitacion.error_center import classify


def test_permission_error_is_explained_without_technical_path():
    result = classify(
        code='INTERNAL_SERVER_ERROR',
        message="PermissionError: permission denied: '/data/tenants/1'",
        status=500,
    )

    assert 'guardar el archivo' in result['cause']
    assert '/data/' not in result['cause']
    assert result['safe_retry'] is False


def test_missing_database_table_tells_user_what_to_do():
    result = classify(
        code='INTERNAL_SERVER_ERROR',
        message='UndefinedTable: relation master_ninos does not exist',
        status=500,
    )

    assert 'base de datos' in result['cause']
    assert 'Base Maestra' in result['solution']


def test_timeout_avoids_repeated_submissions():
    result = classify(code='INTERNAL_SERVER_ERROR', message='Worker timeout', status=500)

    assert 'tiempo' in result['cause']
    assert 'varias veces' in result['solution']
    assert result['safe_retry'] is True
