from modules.cruce_bases.routes import _filter_rows_by_units


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
