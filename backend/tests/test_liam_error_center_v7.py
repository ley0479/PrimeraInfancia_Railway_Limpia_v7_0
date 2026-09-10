from modules.asistente_capacitacion.error_center import classify
from modules.asistente_capacitacion.schema import SCHEMA_SQL


def test_classifies_common_failures_without_blame():
    assert classify(code='ROLE_FORBIDDEN',message='No tienes permiso',status=403)['type']=='error_permisos'
    assert classify(code='RPP_TEMPLATE_NOT_FOUND',message='Plantilla oficial no encontrada',status=422)['type']=='error_plantilla'
    assert classify(code='FAILED_TO_FETCH',message='Failed to fetch',status=503)['type']=='error_red'


def test_incident_schema_is_tenant_scoped():
    assert 'lia_error_incidents' in SCHEMA_SQL
    assert 'fundacion_id INTEGER NOT NULL' in SCHEMA_SQL


def test_diagnosis_redacts_identifiers():
    value=classify(code='INVALID_DATA',message='Falló el documento 1077456789',status=422)
    assert '1077456789' not in value['cause']
