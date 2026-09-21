from modules.cruce_bases.routes import _age_months_at_period, _filter_rows_by_units


def test_unit_report_accepts_catalog_aliases_and_url_variants():
    rows = [
        {'documento': '1', 'unidad': 'BOCA PACURITA'},
        {'documento': '2', 'unidad': 'UCA BAJO PACURITA'},
        {'documento': '3', 'unidad': 'OTRA UNIDAD'},
    ]
    filtered = _filter_rows_by_units(rows, ['BAJO%20PACURITA'])
    assert [row['documento'] for row in filtered] == ['1', '2']


def test_unit_report_without_unit_filter_keeps_all_rows():
    rows = [{'documento': '1', 'unidad': 'BAJO PACURITA'}]
    assert _filter_rows_by_units(rows, []) == rows


def test_report_age_uses_birth_date_at_selected_period():
    row = {'fecha_nacimiento': '2024-09-15', 'edad_meses': 99}
    assert _age_months_at_period(row, 2026, 9) == 23


def test_report_age_uses_stored_value_only_without_valid_birth_date():
    assert _age_months_at_period({'edad_meses': '31'}, 2026, 9) == 31
