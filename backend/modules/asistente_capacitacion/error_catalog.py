"""Catálogo estable y público de errores explicables por LÍA."""
ERROR_CATALOG = {
    'UNIT_COLUMN_NOT_MAPPED': {'title':'No se identificó la columna de unidad','message':'El archivo fue leído, pero no existe una columna de unidad confirmada.','severity':'warning','retryable':True,'actions':['review_detected_columns','open_mapping']},
    'PARTICIPANTES_REQUERIDOS': {'title':'No se identificaron participantes','message':'La lectura terminó, pero no encontró filas reconocibles de participantes. Revisa el mapeo antes de aprobar.','severity':'error','retryable':True,'actions':['open_mapping']},
    'FAILED_TO_FETCH': {'title':'La comunicación no terminó correctamente','message':'No te preocupes: tus datos no se modificaron con esta solicitud. Comprueba la conexión y la sesión antes de intentar nuevamente.','severity':'warning','retryable':True,'actions':['retry']},
    'FILE_NOT_GENERATED': {'title':'El archivo todavía no está disponible','message':'No existe confirmación del servidor de que la generación terminó y el archivo esté disponible.','severity':'warning','retryable':True,'actions':['check_status']},
}

def explain(code: str) -> dict:
    key = str(code or '').strip().upper().replace(' ', '_')
    item = ERROR_CATALOG.get(key)
    if not item:
        return {'code':key or 'UNKNOWN','title':'Necesitamos revisar un poco más','message':'Todavía no hay información suficiente para confirmar la causa. Conserva el request_id y consulta el diagnóstico del módulo; tus datos no se cambiarán durante esta revisión.','severity':'warning','retryable':False,'actions':[],'confidence':'insufficient'}
    return {'code':key, **item, 'confidence':'confirmed'}
