"""La Regional de la UDS nunca puede reemplazar el nombre real de la UDS."""
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))

import app  # noqa: E402


frame = pd.DataFrame({
    'Tipo de Unidad': ['Unidad de Servicio', 'Unidad de Servicio'],
    'Nombre de la Regional de la Unidad de servicio': ['Chocó', 'Chocó'],
    'Código del Municipio de la Unidad de servicio': ['27077', '27077'],
    'Nombre Municipio de la Unidad de servicio': ['Bajo Baudó', 'Bajo Baudó'],
    'Nombre del Centro Zonal': ['CZ Baudó', 'CZ Baudó'],
    'Código de la unidad de servicio': ['001', '002'],
    'Nombre de la unidad de servicio': ['YUDILSA ASPRILLA IBARGUEN', 'ALFONSA MILENA MORENO'],
    'Documento del beneficiario': ['10001', '10002'],
})

assert app.detectar_columna_unidad(frame) == 'Nombre de la unidad de servicio'
normalized = app.limpiar_y_normalizar_dataframe(frame)
assert set(normalized['unidad']) == {'YUDILSA ASPRILLA IBARGUEN', 'ALFONSA MILENA MORENO'}
assert 'CHOCO' not in set(normalized['unidad'])

print('CUENTAME_UNIT_COLUMN_DETECTION_PASS')
