from __future__ import annotations

import json
import os
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
try:
    from werkzeug.utils import secure_filename
except Exception:
    def secure_filename(filename: str) -> str:
        filename = str(filename or 'archivo')
        filename = ''.join(ch if ch.isalnum() or ch in {'-', '_', '.'} else '_' for ch in filename)
        return filename.strip('._') or 'archivo'

from .repository import BaseMaestraRepository, now_iso

TIPOS_FUENTE = {'cuentame', 'talento_humano', 'salud_nutricion'}
ALLOWED_EXTENSIONS = {'.xlsx', '.xls', '.xlsm', '.ods', '.csv', '.txt', '.tsv', '.tab', '.dat', '.html', '.htm', '.json'}

ALIASES = {
    'documento': ['documento_del_beneficiario', 'numero_documento_beneficiario', 'número_documento_beneficiario', 'documento_beneficiario', 'documento', 'numero_documento', 'número_documento', 'numero_de_documento', 'número_de_documento', 'identificacion', 'identificación', 'numero_identificacion', 'num_identificacion', 'cedula', 'cedula_ciudadania', 'doc', 'documento_usuario', 'no_documento'],
    'tipo_documento': ['tipo_de_documento_del_beneficiario', 'tipo_documento_beneficiario', 'tipo_documento', 'tipo_de_documento', 'td', 'tipo_doc', 'tipo_identificacion'],
    'nombres': ['nombres', 'nombre', 'nombre_completo', 'beneficiario', 'nombres_y_apellidos', 'usuario', 'niño', 'nino', 'nina', 'niña'],
    'apellidos': ['apellidos', 'apellido', 'primer_apellido', 'segundo_apellido'],
    'primer_nombre': ['primer_nombre_del_beneficiario', 'primer_nombre_beneficiario', 'primer_nombre', 'nombre_1'],
    'segundo_nombre': ['segundo_nombre_del_beneficiario', 'segundo_nombre_beneficiario', 'segundo_nombre', 'nombre_2'],
    'primer_apellido': ['primer_apellido_del_beneficiario', 'primer_apellido_beneficiario', 'primer_apellido', 'apellido_1'],
    'segundo_apellido': ['segundo_apellido_del_beneficiario', 'segundo_apellido_beneficiario', 'segundo_apellido', 'apellido_2'],
    'fecha_nacimiento': ['fecha_de_nacimiento_del_beneficiario', 'fecha_nacimiento_beneficiario', 'fecha_nacimiento', 'fecha_de_nacimiento', 'fec_nacimiento', 'nacimiento'],
    'edad_meses': ['edad_meses', 'meses', 'edad_en_meses'],
    'grupo_etario': ['grupo_etario', 'grupo_edad', 'rango_edad', 'grupo_de_edad', 'nombre_tipo_de_beneficiario', 'tipo_de_beneficiario'],
    'sexo': ['sexo_del_beneficiario', 'sexo_beneficiario', 'sexo', 'genero', 'género'],
    'estado': ['estado_del_beneficiario', 'estado_beneficiario', 'estado', 'estado_usuario', 'estado_del_niño', 'estado_del_nino', 'activo'],
    'fecha_ingreso': ['fecha_de_atencion_del_beneficiario_a_la_uds', 'fecha_atencion_beneficiario_uds', 'fecha_ingreso', 'fecha_de_ingreso', 'ingreso'],
    'fecha_retiro': ['fecha_retiro', 'fecha_de_retiro', 'retiro'],
    'unidad_servicio': ['nombre_de_la_unidad_de_servicio', 'nombre_unidad_de_servicio', 'unidad_servicio', 'unidad_de_servicio', 'nombre_unidad', 'nombre_uds', 'uds', 'uca', 'unidad', 'servicio'],
    'codigo_unidad': ['codigo_de_la_unidad_de_servicio', 'codigo_unidad_de_servicio', 'codigo_unidad_servicio', 'codigo_unidad', 'código_unidad', 'cod_unidad'],
    'coordinador': ['coordinador', 'coordinadora', 'responsable', 'coordinador_responsable', 'coordinador_a_cargo', 'coordinadora_a_cargo', 'nombre_coordinador', 'nombre_de_coordinador', 'jefe_inmediato', 'lider_equipo', 'líder_equipo'],
    'docente': ['docente', 'agente_educativo', 'agente', 'madre_comunitaria'],
    'modalidad': ['modalidad', 'servicio_modalidad', 'nombre_tipo_de_beneficiario', 'tipo_de_unidad'],
    'cargo': ['cargo', 'rol', 'perfil', 'tipo_cargo', 'tipo_de_cargo', 'tipo_equipo', 'funcion', 'función', 'nombre_cargo', 'nombre_del_cargo', 'denominacion_cargo', 'denominación_cargo', 'denominacion_del_cargo', 'denominación_del_cargo', 'descripcion_cargo', 'descripción_cargo', 'cargo_contractual', 'cargo_en_el_contrato', 'perfil_profesional', 'rol_en_el_equipo', 'tipo_de_talento_humano', 'ocupacion', 'ocupación'],
    'telefono': ['telefono', 'teléfono', 'celular', 'contacto'],
    'correo': ['correo', 'email', 'e_mail'],
    'peso': ['peso', 'peso_kg', 'peso_en_kg'],
    'talla': ['talla', 'talla_cm', 'longitud', 'estatura'],
    'perimetro_braquial': ['perimetro_braquial', 'perímetro_braquial', 'pb', 'circunferencia_braquial'],
    'diagnostico_nutricional': ['diagnostico_nutricional', 'diagnóstico_nutricional', 'diagnostico', 'diagnóstico', 'diagnostico_global', 'estado_nutricional'],
    'estado_nutricional': ['estado_nutricional', 'clasificacion_nutricional', 'clasificación_nutricional'],
    'carne_salud': ['carne_salud', 'carné_salud', 'carnet_salud', 'carne_de_salud', 'carné_de_salud'],
    'control_crecimiento': ['control_crecimiento', 'crecimiento_desarrollo', 'control_cyd', 'control_de_crecimiento_y_desarrollo'],
    'carne_crecimiento': ['carne_crecimiento', 'carné_crecimiento', 'carnet_crecimiento', 'carne_crecimiento_desarrollo'],
    'vacunas': ['vacunas', 'esquema_vacunacion', 'esquema_vacunación', 'carnet_vacunas'],
    'fecha_toma': ['fecha_toma', 'fecha_valoracion', 'fecha_valoración', 'fecha_medicion', 'fecha_medición'],
    'observaciones': ['observaciones', 'observacion', 'comentarios'],
}


def norm_key(value: Any) -> str:
    text = str(value or '').strip().lower()
    text = ''.join(ch for ch in unicodedata.normalize('NFD', text) if unicodedata.category(ch) != 'Mn')
    text = re.sub(r'[^a-z0-9]+', '_', text).strip('_')
    return text


def clean_text(value: Any) -> str:
    if value is None:
        return ''
    try:
        if pd.isna(value):
            return ''
    except Exception:
        pass
    text = str(value).strip()
    if text.lower() in {'nan', 'none', 'null', 'nat'}:
        return ''
    return re.sub(r'\s+', ' ', text)


def normalize_doc(value: Any) -> str:
    text = clean_text(value)
    if not text:
        return ''
    if re.fullmatch(r'\d+\.0', text):
        text = text[:-2]
    return re.sub(r'[^A-Za-z0-9]', '', text).upper()


def normalize_name(value: Any) -> str:
    return clean_text(value).upper()


def normalize_tipo_fuente(tipo: str | None) -> str:
    value = norm_key(tipo or '')
    if value in {'talento', 'talento_humano', 'th'}:
        return 'talento_humano'
    if value in {'nutricion', 'salud', 'salud_nutricion', 'peso_talla', 'peso_y_talla'}:
        return 'salud_nutricion'
    return 'cuentame'


def to_float(value: Any) -> float | None:
    text = clean_text(value).replace(',', '.')
    if not text:
        return None
    match = re.search(r'-?\d+(?:\.\d+)?', text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except Exception:
        return None


def to_int(value: Any) -> int | None:
    f = to_float(value)
    return int(f) if f is not None else None


def make_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    seen: dict[str, int] = {}
    columns = []
    for col in df.columns:
        key = norm_key(col)
        if not key:
            key = 'columna'
        seen[key] = seen.get(key, 0) + 1
        columns.append(key if seen[key] == 1 else f'{key}_{seen[key]}')
    df.columns = columns
    return df


def _excel_sheet_score(columns: list[Any]) -> tuple[int, dict[str, Any]]:
    """Puntúa hojas Excel para escoger la base real de beneficiarios.

    Los archivos Cuéntame suelen traer una hoja resumen antes de la hoja real.
    La hoja correcta para beneficiarios contiene, entre otras, las columnas exactas:
    "Nombre de la unidad de servicio", "Código de la unidad de servicio" y
    "Documento del beneficiario". Esta función evita tomar columnas ambiguas como
    "Tipo de Unidad" o "Nombre de la Regional de la Unidad de servicio".
    """
    normalized = [norm_key(c) for c in columns]
    colset = set(normalized)
    score = 0
    reasons: list[str] = []

    exact_weights = {
        'nombre_de_la_unidad_de_servicio': 200,
        'codigo_de_la_unidad_de_servicio': 80,
        'documento_del_beneficiario': 160,
        'tipo_de_documento_del_beneficiario': 40,
        'primer_nombre_del_beneficiario': 35,
        'primer_apellido_del_beneficiario': 35,
        'fecha_de_nacimiento_del_beneficiario': 35,
        'sexo_del_beneficiario': 20,
    }
    for col, weight in exact_weights.items():
        if col in colset:
            score += weight
            reasons.append(col)

    # Señales negativas típicas de hojas resumen.
    if len(columns) <= 8 and not {'documento_del_beneficiario', 'nombre_de_la_unidad_de_servicio'} & colset:
        score -= 100
        reasons.append('posible_hoja_resumen')
    if any(str(c).lower().startswith('unnamed') for c in columns):
        score -= 30
        reasons.append('columnas_unnamed')

    return score, {'columnas_normalizadas': normalized, 'razones': reasons}


def _read_excel_best_sheet(path: str, engine: str | None = None) -> tuple[pd.DataFrame, dict[str, Any]]:
    xl = pd.ExcelFile(path, engine=engine) if engine else pd.ExcelFile(path)
    candidates: list[dict[str, Any]] = []
    for sheet in xl.sheet_names:
        try:
            # Leer pocos registros para puntuar rápido y luego la hoja completa.
            sample = pd.read_excel(path, sheet_name=sheet, dtype=object, nrows=20, engine=engine) if engine else pd.read_excel(path, sheet_name=sheet, dtype=object, nrows=20)
            score, detail = _excel_sheet_score(list(sample.columns))
            candidates.append({
                'sheet': sheet,
                'score': score,
                'columns': [str(c) for c in sample.columns],
                'detail': detail,
            })
        except Exception as exc:
            candidates.append({'sheet': sheet, 'score': -9999, 'columns': [], 'error': str(exc)})
    candidates.sort(key=lambda x: x.get('score', -9999), reverse=True)
    selected = candidates[0]['sheet'] if candidates else 0
    df = pd.read_excel(path, sheet_name=selected, dtype=object, engine=engine) if engine else pd.read_excel(path, sheet_name=selected, dtype=object)
    meta = {
        'hojas_encontradas': xl.sheet_names,
        'hoja_seleccionada': selected,
        'seleccion_hoja': candidates,
    }
    return make_columns(df), meta


def read_tabular_file_with_metadata(path: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    ext = Path(path).suffix.lower()
    if ext in {'.xlsx', '.xls', '.xlsm'}:
        return _read_excel_best_sheet(path)
    if ext == '.ods':
        df, meta = _read_excel_best_sheet(path, engine='odf')
        return df, meta
    if ext in {'.html', '.htm'}:
        tables = pd.read_html(path)
        if not tables:
            return pd.DataFrame(), {'tipo_lectura': 'html', 'tablas': 0}
        return make_columns(tables[0]), {'tipo_lectura': 'html', 'tablas': len(tables), 'tabla_seleccionada': 0}
    if ext == '.json':
        return make_columns(pd.read_json(path)), {'tipo_lectura': 'json'}
    sep_candidates = [';', ',', '\t', '|'] if ext not in {'.tsv', '.tab'} else ['\t', ';', ',']
    last_error = None
    for sep in sep_candidates:
        try:
            df = pd.read_csv(path, sep=sep, dtype=object, encoding='utf-8-sig')
            if len(df.columns) > 1 or sep == sep_candidates[-1]:
                return make_columns(df), {'tipo_lectura': 'csv', 'separador': sep}
        except Exception as exc:
            last_error = exc
    try:
        return make_columns(pd.read_csv(path, sep=None, engine='python', dtype=object, encoding='latin-1')), {'tipo_lectura': 'csv', 'separador': 'auto_latin1'}
    except Exception as exc:
        raise ValueError(f'No se pudo leer el archivo tabular: {last_error or exc}')


def read_tabular_file(path: str) -> pd.DataFrame:
    df, _meta = read_tabular_file_with_metadata(path)
    return df



def _detectar_columnas_unidad(columns: list[str]) -> dict[str, Any]:
    """Diagnóstico de columnas de unidad para evitar tomar la columna incorrecta."""
    cols = [str(c) for c in columns]
    normalizadas = [norm_key(c) for c in cols]
    prioridad_unidad = [
        'nombre_de_la_unidad_de_servicio',
        'nombre_unidad_de_servicio',
        'unidad_de_servicio',
        'unidad_servicio',
        'nombre_unidad',
        'nombre_uds',
        'uds',
    ]
    prioridad_codigo = [
        'codigo_de_la_unidad_de_servicio',
        'codigo_unidad_de_servicio',
        'codigo_unidad_servicio',
        'codigo_unidad',
    ]
    descartadas = {
        'tipo_de_unidad',
        'nombre_de_la_regional_de_la_unidad_de_servicio',
        'codigo_del_municipio_de_la_unidad_de_servicio',
        'nombre_municipio_de_la_unidad_de_servicio',
    }
    unidad = next((c for c in prioridad_unidad if c in normalizadas), None)
    codigo = next((c for c in prioridad_codigo if c in normalizadas), None)
    candidatas = [c for c in normalizadas if 'unidad' in c]
    return {
        'columna_unidad_usada': unidad,
        'columna_codigo_unidad_usada': codigo,
        'columnas_unidad_candidatas': candidatas,
        'columnas_unidad_descartadas': [c for c in candidatas if c in descartadas],
    }


def _resumen_unidades_staging(rows: list[dict[str, Any]], columnas: list[str], tipo_fuente: str, read_meta: dict[str, Any]) -> dict[str, Any]:
    unidades_counter = Counter()
    unidades_original: dict[str, str] = {}
    sin_unidad = 0
    for row in rows:
        unidad = clean_text(row.get('unidad_servicio'))
        if not unidad:
            sin_unidad += 1
            continue
        normalizada = normalize_name(unidad)
        unidades_counter[normalizada] += 1
        unidades_original.setdefault(normalizada, unidad)
    unidades = [
        {'unidad': unidades_original.get(nombre, nombre), 'unidad_normalizada': nombre, 'registros': count}
        for nombre, count in sorted(unidades_counter.items(), key=lambda kv: kv[0])
    ]
    diagnostico_columnas = _detectar_columnas_unidad(columnas)
    alertas: list[str] = []
    if normalize_tipo_fuente(tipo_fuente) == 'cuentame':
        if diagnostico_columnas.get('columna_unidad_usada') != 'nombre_de_la_unidad_de_servicio' and 'nombre_de_la_unidad_de_servicio' in [norm_key(c) for c in columnas]:
            alertas.append('La base contiene "Nombre de la unidad de servicio", pero no se está usando como columna principal de UDS.')
        if len(unidades) < 30 and 'nombre_de_la_unidad_de_servicio' in [norm_key(c) for c in columnas]:
            alertas.append('La base parece estar siendo leída con una columna incorrecta de unidad.')
    return {
        'total_unidades_detectadas': len(unidades),
        'unidades_detectadas': unidades,
        'registros_sin_unidad': sin_unidad,
        'diagnostico_columnas_unidad': diagnostico_columnas,
        'hoja_seleccionada': read_meta.get('hoja_seleccionada'),
        'hojas_encontradas': read_meta.get('hojas_encontradas') or [],
        'alertas': alertas,
    }

def pick(row: dict[str, Any], field: str) -> Any:
    keys = [norm_key(a) for a in ALIASES.get(field, [field])]
    for key in keys:
        if key in row and clean_text(row.get(key)):
            return row.get(key)
    # búsqueda parcial controlada
    for key, value in row.items():
        if key in keys:
            return value
    return ''


def combine_names(row: dict[str, Any]) -> tuple[str, str, str]:
    pn = clean_text(pick(row, 'primer_nombre'))
    sn = clean_text(pick(row, 'segundo_nombre'))
    pa = clean_text(pick(row, 'primer_apellido'))
    sa = clean_text(pick(row, 'segundo_apellido'))
    nombres = clean_text(pick(row, 'nombres'))
    apellidos = clean_text(pick(row, 'apellidos'))
    if pn or sn:
        nombres = clean_text(f'{pn} {sn}')
    if pa or sa:
        apellidos = clean_text(f'{pa} {sa}')
    completo = clean_text(f'{nombres} {apellidos}') if apellidos and apellidos not in nombres else nombres
    return normalize_name(nombres), normalize_name(apellidos), normalize_name(completo)


def calcular_alertas_nutricionales(item: dict[str, Any]) -> list[str]:
    alertas = []
    diag = norm_key(item.get('diagnostico_nutricional') or item.get('estado_nutricional'))
    if not item.get('peso') and not item.get('talla'):
        alertas.append('SIN PESO Y TALLA')
    elif not item.get('peso'):
        alertas.append('SIN PESO')
    elif not item.get('talla'):
        alertas.append('SIN TALLA')
    if not item.get('perimetro_braquial'):
        alertas.append('SIN PERÍMETRO BRAQUIAL')
    if not item.get('diagnostico_nutricional') and not item.get('estado_nutricional'):
        alertas.append('SIN DIAGNÓSTICO NUTRICIONAL')
    if 'bajo' in diag and 'riesgo' not in diag:
        alertas.append('BAJO PESO')
    if 'riesgo' in diag and 'bajo' in diag:
        alertas.append('RIESGO DE BAJO PESO')
    if 'sobrepeso' in diag:
        alertas.append('SOBREPESO')
    if 'obesidad' in diag:
        alertas.append('OBESIDAD')
    if 'talla_baja' in diag or ('talla' in diag and 'baja' in diag):
        alertas.append('TALLA BAJA')
    return sorted(set(alertas))


def map_staging_row(tipo_fuente: str, raw: dict[str, Any], fila: int, carga_id: int, ctx: dict[str, Any]) -> dict[str, Any]:
    tipo_fuente = normalize_tipo_fuente(tipo_fuente)
    raw_clean = {norm_key(k): clean_text(v) for k, v in raw.items()}
    nombres, apellidos, nombre_completo = combine_names(raw_clean)
    now = now_iso()
    base = {
        'carga_id': carga_id,
        'fila': fila,
        'documento': normalize_doc(pick(raw_clean, 'documento')),
        'tipo_documento': clean_text(pick(raw_clean, 'tipo_documento')).upper(),
        'nombres': nombres,
        'apellidos': apellidos,
        'nombre_completo': nombre_completo,
        'unidad_servicio': normalize_name(pick(raw_clean, 'unidad_servicio')),
        'coordinador': normalize_name(pick(raw_clean, 'coordinador')),
        'corporacion_id': ctx.get('corporacion_id'),
        'fundacion_id': ctx.get('fundacion_id') or 1,
        'datos_json': json.dumps(raw_clean, ensure_ascii=False, default=str),
        'errores_json': '[]',
        'fecha_creacion': now,
    }
    if tipo_fuente == 'talento_humano':
        cargo = normalize_name(pick(raw_clean, 'cargo'))
        return {
            **base,
            'cargo': cargo,
            'rol_normalizado': normalizar_rol_talento(cargo),
            'telefono': clean_text(pick(raw_clean, 'telefono')),
            'correo': clean_text(pick(raw_clean, 'correo')),
            'estado': normalize_name(pick(raw_clean, 'estado')) or 'ACTIVO',
        }
    if tipo_fuente == 'salud_nutricion':
        item = {
            **base,
            'peso': to_float(pick(raw_clean, 'peso')),
            'talla': to_float(pick(raw_clean, 'talla')),
            'perimetro_braquial': to_float(pick(raw_clean, 'perimetro_braquial')),
            'diagnostico_nutricional': normalize_name(pick(raw_clean, 'diagnostico_nutricional')),
            'estado_nutricional': normalize_name(pick(raw_clean, 'estado_nutricional')),
            'carne_salud': normalize_name(pick(raw_clean, 'carne_salud')),
            'control_crecimiento': normalize_name(pick(raw_clean, 'control_crecimiento')),
            'carne_crecimiento': normalize_name(pick(raw_clean, 'carne_crecimiento')),
            'vacunas': normalize_name(pick(raw_clean, 'vacunas')),
            'fecha_toma': clean_text(pick(raw_clean, 'fecha_toma')),
            'observaciones': clean_text(pick(raw_clean, 'observaciones')),
            'alertas_json': '[]',
        }
        item['alertas_json'] = json.dumps(calcular_alertas_nutricionales(item), ensure_ascii=False)
        return item
    return {
        **base,
        'fecha_nacimiento': clean_text(pick(raw_clean, 'fecha_nacimiento')),
        'edad_meses': to_int(pick(raw_clean, 'edad_meses')),
        'grupo_etario': normalize_name(pick(raw_clean, 'grupo_etario')),
        'sexo': normalize_name(pick(raw_clean, 'sexo')),
        'estado': normalize_name(pick(raw_clean, 'estado')) or 'ACTIVO',
        'fecha_ingreso': clean_text(pick(raw_clean, 'fecha_ingreso')),
        'fecha_retiro': clean_text(pick(raw_clean, 'fecha_retiro')),
        'codigo_unidad': clean_text(pick(raw_clean, 'codigo_unidad')),
        'docente': normalize_name(pick(raw_clean, 'docente')),
        'modalidad': normalize_name(pick(raw_clean, 'modalidad')),
    }


def normalizar_rol_talento(cargo: str) -> str:
    c = norm_key(cargo)
    if 'coord' in c:
        return 'COORDINADOR'
    if 'docente' in c or 'agente' in c or 'pedagog' in c or 'educador' in c:
        return 'DOCENTE'
    if 'aux' in c:
        return 'AUXILIAR'
    if 'psico' in c:
        return 'PSICOSOCIAL'
    if 'trabaj' in c and 'social' in c:
        return 'PSICOSOCIAL'
    if 'nutri' in c:
        return 'NUTRICIONISTA'
    if 'enferm' in c:
        return 'ENFERMERIA'
    if 'administr' in c:
        return 'ADMINISTRATIVO'
    if 'servicios_generales' in c or 'aseo' in c:
        return 'SERVICIOS_GENERALES'
    return cargo.upper() if cargo else 'TALENTO_HUMANO'


def get_user_context() -> dict[str, Any]:
    try:
        from flask import g
        user = getattr(g, 'current_user', {}) or {}
    except Exception:
        user = {}
    return {
        'usuario_id': user.get('id'),
        'usuario': user.get('username') or user.get('email') or user.get('nombre_completo') or 'sistema',
        'fundacion_id': int(user.get('fundacion_id') or 1),
        'rol': user.get('rol') or 'SUPERADMIN',
        'raw': user,
    }


def guardar_fuente(database_path: str, upload_folder: str, file_storage, tipo_fuente: str, ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    ctx = {**get_user_context(), **(ctx or {})}
    tipo_fuente = normalize_tipo_fuente(tipo_fuente)
    repo = BaseMaestraRepository(database_path)
    repo.init_schema()
    ctx['corporacion_id'] = ctx.get('corporacion_id') or repo.corporacion_para_fundacion(ctx.get('fundacion_id'))

    original = file_storage.filename or 'archivo'
    ext = Path(original).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError('Formato no permitido para Base Maestra. Usa Excel, CSV, TXT, TSV, HTML, JSON u ODS.')
    os.makedirs(upload_folder, exist_ok=True)
    safe = secure_filename(original)
    nombre_guardado = f"BASE_MAESTRA_{tipo_fuente.upper()}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{safe}"
    ruta = os.path.join(upload_folder, nombre_guardado)
    file_storage.save(ruta)

    df, read_meta = read_tabular_file_with_metadata(ruta)
    df = df.dropna(how='all')
    columnas = list(df.columns)
    carga_id = repo.crear_carga({
        'tipo_fuente': tipo_fuente,
        'nombre_archivo_original': original,
        'nombre_archivo_guardado': nombre_guardado,
        'ruta_archivo': ruta,
        'extension': ext,
        'usuario_id': ctx.get('usuario_id'),
        'usuario': ctx.get('usuario'),
        'corporacion_id': ctx.get('corporacion_id'),
        'fundacion_id': ctx.get('fundacion_id'),
        'total_registros': int(len(df.index)),
        'columnas': columnas,
        'metadata': {'fase': 'carga_fuente', 'arquitectura': 'base_maestra_alpha75_unidades', 'lectura_archivo': read_meta},
    })

    staging_rows = []
    errores = []
    for idx, raw in enumerate(df.to_dict(orient='records'), start=2):
        try:
            row = map_staging_row(tipo_fuente, raw, idx, carga_id, ctx)
            staging_rows.append(row)
        except Exception as exc:
            errores.append({'fila': idx, 'error': str(exc)})
    resumen_unidades = _resumen_unidades_staging(staging_rows, columnas, tipo_fuente, read_meta)
    repo.insertar_staging(tipo_fuente, staging_rows)
    metadata_final = {
        'fase': 'carga_fuente',
        'arquitectura': 'base_maestra_alpha75_unidades',
        'lectura_archivo': read_meta,
        'resumen_unidades': resumen_unidades,
    }
    repo.actualizar_carga(
        carga_id,
        total_registros=int(len(df.index)),
        registros_validos=len(staging_rows),
        registros_error=len(errores),
        estado='cargado' if not errores else 'cargado_con_observaciones',
        columnas_json=json.dumps(columnas, ensure_ascii=False),
        errores_json=json.dumps(errores, ensure_ascii=False),
        metadata_json=json.dumps(metadata_final, ensure_ascii=False, default=str),
    )
    return {
        'message': 'Fuente cargada correctamente para Base Maestra.',
        'carga_id': carga_id,
        'tipo_fuente': tipo_fuente,
        'nombre_archivo': original,
        'total_registros': int(len(df.index)),
        'registros_cargados': len(staging_rows),
        'errores': errores[:50],
        'columnas': columnas,
        'estado': 'cargado' if not errores else 'cargado_con_observaciones',
        'hoja_seleccionada': resumen_unidades.get('hoja_seleccionada'),
        'hojas_encontradas': resumen_unidades.get('hojas_encontradas'),
        'resumen_unidades': resumen_unidades,
        'total_unidades_detectadas': resumen_unidades.get('total_unidades_detectadas'),
        'unidades_detectadas': resumen_unidades.get('unidades_detectadas'),
        'alertas_unidades': resumen_unidades.get('alertas'),
    }



def validar_carga(database_path: str, carga_id: int, ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    ctx = {**get_user_context(), **(ctx or {})}
    repo = BaseMaestraRepository(database_path)
    repo.init_schema()
    carga = repo.fetch_one("SELECT * FROM cargas_archivos WHERE id = ?", (carga_id,))
    if not carga:
        raise ValueError('Carga no encontrada.')
    if ctx.get('rol') != 'SUPERADMIN' and int(carga.get('fundacion_id') or 1) != int(ctx.get('fundacion_id') or 1):
        raise PermissionError('No tienes permiso para validar esta carga.')
    tipo = normalize_tipo_fuente(carga.get('tipo_fuente'))
    rows = repo.staging_rows(tipo, carga_id=carga_id)
    with repo.connect() as conn:
        conn.execute("DELETE FROM master_inconsistencias WHERE carga_id = ? AND version_id IS NULL", (carga_id,))
        conn.commit()

    total = len(rows)
    errors = 0
    warnings = 0
    docs = []
    for row in rows:
        documento = normalize_doc(row.get('documento'))
        nombre = clean_text(row.get('nombre_completo'))
        unidad = clean_text(row.get('unidad_servicio'))
        docs.append(documento)
        def issue(sev: str, tipo_i: str, campo: str, desc: str):
            nonlocal errors, warnings
            if sev == 'CRITICA':
                errors += 1
            else:
                warnings += 1
            repo.registrar_inconsistencia({
                'carga_id': carga_id,
                'tipo_fuente': tipo,
                'severidad': sev,
                'tipo': tipo_i,
                'documento': documento,
                'nombre': nombre,
                'unidad_servicio': unidad,
                'campo': campo,
                'descripcion': desc,
                'corporacion_id': carga.get('corporacion_id'),
                'fundacion_id': carga.get('fundacion_id') or 1,
                'datos': {'fila': row.get('fila')},
            })
        if not documento:
            issue('CRITICA', 'DOCUMENTO_VACIO', 'documento', 'Registro sin documento de identidad. No se puede consolidar como maestro.')
        if tipo == 'cuentame':
            if not nombre:
                issue('ADVERTENCIA', 'NOMBRE_VACIO', 'nombre_completo', 'Registro sin nombre completo.')
            if not unidad:
                issue('ADVERTENCIA', 'UNIDAD_VACIA', 'unidad_servicio', 'Registro sin unidad de servicio.')
            if not row.get('sexo'):
                issue('ADVERTENCIA', 'SEXO_VACIO', 'sexo', 'Registro sin sexo.')
        elif tipo == 'salud_nutricion':
            if row.get('peso') in {None, ''} and row.get('talla') in {None, ''}:
                issue('ADVERTENCIA', 'SIN_PESO_TALLA', 'peso_talla', 'Registro sin peso y talla.')
            if not row.get('diagnostico_nutricional') and not row.get('estado_nutricional'):
                issue('ADVERTENCIA', 'SIN_DIAGNOSTICO', 'diagnostico_nutricional', 'Registro sin diagnóstico nutricional.')
        elif tipo == 'talento_humano':
            if not row.get('cargo'):
                issue('ADVERTENCIA', 'CARGO_VACIO', 'cargo', 'Talento humano sin cargo o perfil.')
            if not unidad:
                issue('ADVERTENCIA', 'UNIDAD_TALENTO_VACIA', 'unidad_servicio', 'Talento humano sin unidad asignada.')

    counts = Counter([d for d in docs if d])
    duplicados = 0
    for doc, count in counts.items():
        if count > 1:
            duplicados += count - 1
            repo.registrar_inconsistencia({
                'carga_id': carga_id,
                'tipo_fuente': tipo,
                'severidad': 'ADVERTENCIA',
                'tipo': 'DOCUMENTO_DUPLICADO',
                'documento': doc,
                'campo': 'documento',
                'descripcion': f'Documento repetido {count} veces en la fuente {tipo}. Se consolidará un solo registro maestro.',
                'corporacion_id': carga.get('corporacion_id'),
                'fundacion_id': carga.get('fundacion_id') or 1,
                'datos': {'repeticiones': count},
            })
            warnings += 1

    validos = max(total - errors, 0)
    calidad = round((validos / total * 100) if total else 0, 2)
    if errors:
        semaforo, estado = 'ROJO', 'rechazado'
    elif warnings or duplicados:
        semaforo, estado = 'AMARILLO', 'validado_con_advertencias'
    else:
        semaforo, estado = 'VERDE', 'validado'
    recomendaciones = []
    if errors:
        recomendaciones.append('Corrige documentos vacíos antes de publicar la Base Maestra.')
    if warnings:
        recomendaciones.append('Revisa advertencias antes de consolidar para mejorar la calidad de datos.')
    if not rows:
        recomendaciones.append('La carga no tiene registros disponibles para validar.')
        semaforo, estado = 'ROJO', 'rechazado'
    resumen = {
        'total_registros': total,
        'registros_validos': validos,
        'registros_error': errors,
        'errores_criticos': errors,
        'advertencias': warnings,
        'duplicados': duplicados,
        'calidad_porcentaje': calidad,
        'semaforo': semaforo,
        'estado': estado,
        'tipo_fuente': tipo,
    }
    validacion_id = repo.guardar_validacion({
        'carga_id': carga_id,
        'tipo_fuente': tipo,
        'fundacion_id': carga.get('fundacion_id') or 1,
        'corporacion_id': carga.get('corporacion_id'),
        'estado': estado,
        'semaforo': semaforo,
        **resumen,
        'reporte': resumen,
        'recomendaciones': recomendaciones,
        'usuario_id': ctx.get('usuario_id'),
        'usuario': ctx.get('usuario'),
    })
    repo.actualizar_carga(carga_id, registros_validos=validos, registros_error=errors, estado=estado)
    return {'validacion_id': validacion_id, 'carga_id': carga_id, 'resumen': resumen, 'recomendaciones': recomendaciones}


def validar_fuentes_pendientes(database_path: str, ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    ctx = {**get_user_context(), **(ctx or {})}
    repo = BaseMaestraRepository(database_path)
    repo.init_schema()
    rows = repo.fetch_all(
        """
        SELECT * FROM cargas_archivos
        WHERE fundacion_id = ? AND estado IN ('cargado','cargado_con_observaciones')
        ORDER BY fecha_carga DESC
        """,
        (ctx.get('fundacion_id') or 1,),
    )
    resultados = []
    for row in rows:
        resultados.append(validar_carga(database_path, int(row['id']), ctx))
    return {'validaciones': resultados, 'total_validaciones': len(resultados)}


def load_existing_table_rows(repo: BaseMaestraRepository, fundacion_id: int, tipo: str) -> list[dict[str, Any]]:
    """Fallback seguro: permite crear Base Maestra inicial con datos ya cargados en la plataforma."""
    rows: list[dict[str, Any]] = []
    with repo.connect() as conn:
        conn.row_factory = None
        cur = conn.cursor()
        def columns(table: str) -> set[str]:
            try:
                return {r[1] for r in cur.execute(f'PRAGMA table_info({table})').fetchall()}
            except Exception:
                return set()
        if tipo == 'cuentame':
            table = 'usuarios' if columns('usuarios') else 'beneficiarios'
            cols = columns(table)
            if not cols:
                return []
            where = 'WHERE COALESCE(fundacion_id, 1) = ?' if 'fundacion_id' in cols else ''
            params = (fundacion_id,) if where else ()
            qcols = ','.join(cols)
            cur.execute(f'SELECT {qcols} FROM {table} {where}', params)
            names = [d[0] for d in cur.description]
            for i, raw_row in enumerate(cur.fetchall(), start=1):
                raw = dict(zip(names, raw_row))
                nombres = raw.get('nombres') or raw.get('nombre') or ' '.join([clean_text(raw.get('primer_nombre')), clean_text(raw.get('segundo_nombre'))]).strip()
                apellidos = raw.get('apellidos') or ' '.join([clean_text(raw.get('primer_apellido')), clean_text(raw.get('segundo_apellido'))]).strip()
                rows.append({
                    'id': -i,
                    'carga_id': None,
                    'documento': normalize_doc(raw.get('documento')),
                    'tipo_documento': clean_text(raw.get('tipo_documento')),
                    'nombres': normalize_name(nombres),
                    'apellidos': normalize_name(apellidos),
                    'nombre_completo': normalize_name(raw.get('nombre') or f'{nombres} {apellidos}'),
                    'fecha_nacimiento': clean_text(raw.get('fecha_nacimiento')),
                    'edad_meses': to_int(raw.get('edad_meses')),
                    'grupo_etario': normalize_name(raw.get('grupo_edad') or raw.get('grupo_etario')),
                    'sexo': normalize_name(raw.get('sexo')),
                    'estado': normalize_name(raw.get('estado')) or 'ACTIVO',
                    'fecha_ingreso': clean_text(raw.get('fecha_ingreso')),
                    'fecha_retiro': clean_text(raw.get('fecha_retiro')),
                    'unidad_servicio': normalize_name(raw.get('unidad')),
                    'codigo_unidad': clean_text(raw.get('codigo_unidad_servicio')),
                    'coordinador': normalize_name(raw.get('coordinador') or raw.get('coordinador_nombre')),
                    'docente': normalize_name(raw.get('docente')),
                    'modalidad': normalize_name(raw.get('modalidad')),
                    'fundacion_id': fundacion_id,
                    'corporacion_id': repo.corporacion_para_fundacion(fundacion_id),
                    'datos_json': json.dumps(raw, ensure_ascii=False, default=str),
                    'fecha_creacion': now_iso(),
                })
        elif tipo == 'salud_nutricion':
            for table in ['sn_valoraciones', 'peso_talla']:
                cols = columns(table)
                if not cols:
                    continue
                where = 'WHERE COALESCE(fundacion_id, 1) = ?' if 'fundacion_id' in cols else ''
                params = (fundacion_id,) if where else ()
                cur.execute(f"SELECT {','.join(cols)} FROM {table} {where}", params)
                names = [d[0] for d in cur.description]
                for i, raw_row in enumerate(cur.fetchall(), start=1):
                    raw = dict(zip(names, raw_row))
                    rows.append({
                        'id': -i,
                        'carga_id': None,
                        'documento': normalize_doc(raw.get('documento')),
                        'nombre_completo': normalize_name(raw.get('nombre_completo') or raw.get('nombre')),
                        'unidad_servicio': normalize_name(raw.get('unidad')),
                        'peso': to_float(raw.get('peso_kg') or raw.get('peso')),
                        'talla': to_float(raw.get('talla_cm') or raw.get('talla')),
                        'perimetro_braquial': to_float(raw.get('perimetro_braquial_cm') or raw.get('perimetro_braquial')),
                        'diagnostico_nutricional': normalize_name(raw.get('diagnostico_global') or raw.get('estado_nutricional')),
                        'estado_nutricional': normalize_name(raw.get('estado_nutricional') or raw.get('diagnostico_global')),
                        'fecha_toma': clean_text(raw.get('fecha_valoracion') or raw.get('fecha_toma') or raw.get('fecha_medicion')),
                        'observaciones': clean_text(raw.get('observaciones')),
                        'fundacion_id': fundacion_id,
                        'corporacion_id': repo.corporacion_para_fundacion(fundacion_id),
                        'datos_json': json.dumps(raw, ensure_ascii=False, default=str),
                        'alertas_json': '[]',
                    })
        elif tipo == 'talento_humano':
            for table in ['th_personas', 'coordinadores']:
                cols = columns(table)
                if not cols:
                    continue
                where = 'WHERE COALESCE(fundacion_id, 1) = ?' if 'fundacion_id' in cols else ''
                params = (fundacion_id,) if where else ()
                cur.execute(f"SELECT {','.join(cols)} FROM {table} {where}", params)
                names = [d[0] for d in cur.description]
                for i, raw_row in enumerate(cur.fetchall(), start=1):
                    raw = dict(zip(names, raw_row))
                    nombre = raw.get('nombre') or raw.get('nombres') or raw.get('coordinador')
                    cargo = normalize_name(raw.get('cargo') or raw.get('perfil') or raw.get('tipo_equipo'))
                    rows.append({
                        'id': -i,
                        'carga_id': None,
                        'documento': normalize_doc(raw.get('documento')),
                        'nombres': normalize_name(raw.get('nombres') or nombre),
                        'apellidos': normalize_name(raw.get('apellidos')),
                        'nombre_completo': normalize_name(nombre),
                        'cargo': cargo,
                        'rol_normalizado': normalizar_rol_talento(cargo),
                        'unidad_servicio': normalize_name(raw.get('unidad')),
                        'coordinador': normalize_name(raw.get('coordinador')),
                        'telefono': clean_text(raw.get('telefono')),
                        'estado': normalize_name(raw.get('estado')) or 'ACTIVO',
                        'fundacion_id': fundacion_id,
                        'corporacion_id': repo.corporacion_para_fundacion(fundacion_id),
                        'datos_json': json.dumps(raw, ensure_ascii=False, default=str),
                    })
    return rows


def latest_rows_for_type(repo: BaseMaestraRepository, tipo: str, fundacion_id: int) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    carga = repo.ultima_carga(tipo, fundacion_id, estados=('validado', 'validado_con_advertencias', 'cargado', 'cargado_con_observaciones'))
    if carga:
        rows = repo.staging_rows(tipo, carga_id=int(carga['id']))
        if tipo == 'talento_humano':
            for row in rows:
                try:
                    original = json.loads(row.get('datos_json') or '{}')
                except Exception:
                    original = {}
                cargo_detectado = normalize_name(pick(original, 'cargo'))
                if cargo_detectado:
                    row['cargo'] = cargo_detectado
                elif norm_key(row.get('cargo')) == norm_key(original.get('componente')):
                    # Una versión anterior aceptaba "componente" como cargo y podía
                    # convertir a todo un equipo en ADMINISTRATIVO/PEDAGÓGICO.
                    row['cargo'] = ''
                row['rol_normalizado'] = normalizar_rol_talento(row.get('cargo') or row.get('rol_normalizado') or '')
                if not clean_text(row.get('coordinador')):
                    row['coordinador'] = normalize_name(pick(original, 'coordinador'))
                if not clean_text(row.get('unidad_servicio')):
                    row['unidad_servicio'] = normalize_name(pick(original, 'unidad_servicio'))
        return rows, carga
    return load_existing_table_rows(repo, fundacion_id, tipo), None


def consolidate_by_document(rows: list[dict[str, Any]], repo: BaseMaestraRepository, version_id: int, carga: dict[str, Any] | None, tipo: str, fundacion_id: int, corporacion_id: int) -> dict[str, dict[str, Any]]:
    by_doc: dict[str, dict[str, Any]] = {}
    for row in rows:
        doc = normalize_doc(row.get('documento'))
        if not doc:
            repo.registrar_inconsistencia({
                'version_id': version_id,
                'carga_id': carga.get('id') if carga else None,
                'tipo_fuente': tipo,
                'severidad': 'CRITICA',
                'tipo': 'DOCUMENTO_VACIO',
                'descripcion': 'Registro sin documento en fase de consolidación.',
                'nombre': row.get('nombre_completo'),
                'unidad_servicio': row.get('unidad_servicio'),
                'corporacion_id': corporacion_id,
                'fundacion_id': fundacion_id,
                'datos': row,
            })
            continue
        if doc not in by_doc:
            by_doc[doc] = dict(row)
            by_doc[doc]['documento'] = doc
            continue
        # Completa campos vacíos sin sobrescribir dato válido.
        actual = by_doc[doc]
        for key, value in row.items():
            if not clean_text(actual.get(key)) and clean_text(value):
                actual[key] = value
            elif key in {'unidad_servicio', 'estado', 'diagnostico_nutricional'} and clean_text(actual.get(key)) and clean_text(value) and clean_text(actual.get(key)) != clean_text(value):
                repo.registrar_inconsistencia({
                    'version_id': version_id,
                    'carga_id': carga.get('id') if carga else None,
                    'tipo_fuente': tipo,
                    'severidad': 'ADVERTENCIA',
                    'tipo': 'CONFLICTO_DATO_DUPLICADO',
                    'documento': doc,
                    'nombre': actual.get('nombre_completo') or row.get('nombre_completo'),
                    'unidad_servicio': actual.get('unidad_servicio') or row.get('unidad_servicio'),
                    'campo': key,
                    'descripcion': f'Documento duplicado con valores diferentes en {key}. Se conservó el primer dato válido.',
                    'valor_1': actual.get(key),
                    'valor_2': value,
                    'corporacion_id': corporacion_id,
                    'fundacion_id': fundacion_id,
                    'datos': {'fila_actual': actual.get('fila'), 'fila_duplicada': row.get('fila')},
                })
        repo.registrar_inconsistencia({
            'version_id': version_id,
            'carga_id': carga.get('id') if carga else None,
            'tipo_fuente': tipo,
            'severidad': 'ADVERTENCIA',
            'tipo': 'DOCUMENTO_DUPLICADO_CONSOLIDADO',
            'documento': doc,
            'nombre': actual.get('nombre_completo'),
            'unidad_servicio': actual.get('unidad_servicio'),
            'campo': 'documento',
            'descripcion': 'Registro duplicado consolidado en un solo maestro.',
            'corporacion_id': corporacion_id,
            'fundacion_id': fundacion_id,
            'datos': {'fila_duplicada': row.get('fila')},
        })
    return by_doc


def consolidar_base_maestra(database_path: str, ctx: dict[str, Any] | None = None, observaciones: str = '') -> dict[str, Any]:
    ctx = {**get_user_context(), **(ctx or {})}
    fundacion_id = int(ctx.get('fundacion_id') or 1)
    repo = BaseMaestraRepository(database_path)
    repo.init_schema()
    corporacion_id = ctx.get('corporacion_id') or repo.corporacion_para_fundacion(fundacion_id)

    cuentame_rows, carga_cuentame = latest_rows_for_type(repo, 'cuentame', fundacion_id)
    talento_rows, carga_talento = latest_rows_for_type(repo, 'talento_humano', fundacion_id)
    salud_rows, carga_salud = latest_rows_for_type(repo, 'salud_nutricion', fundacion_id)
    if not cuentame_rows:
        raise ValueError('No hay registros de niños/Cuéntame para consolidar. Carga o importa primero la fuente de niños.')

    version_id = repo.crear_version_borrador({
        'fundacion_id': fundacion_id,
        'corporacion_id': corporacion_id,
        'usuario_id': ctx.get('usuario_id'),
        'usuario': ctx.get('usuario'),
        'cargas': {
            'cuentame': carga_cuentame.get('id') if carga_cuentame else 'tabla_actual_usuarios',
            'talento_humano': carga_talento.get('id') if carga_talento else 'tabla_actual_talento',
            'salud_nutricion': carga_salud.get('id') if carga_salud else 'tabla_actual_salud_nutricion',
        },
        'observaciones': observaciones,
    })

    ninos = consolidate_by_document(cuentame_rows, repo, version_id, carga_cuentame, 'cuentame', fundacion_id, corporacion_id)
    salud = consolidate_by_document(salud_rows, repo, version_id, carga_salud, 'salud_nutricion', fundacion_id, corporacion_id)
    talento_by_unidad: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in talento_rows:
        unidad = normalize_name(item.get('unidad_servicio'))
        if unidad:
            talento_by_unidad[unidad].append(item)

    now = now_iso()
    for doc, nino in list(ninos.items()):
        sn = salud.get(doc, {})
        for key in ['peso', 'talla', 'perimetro_braquial', 'diagnostico_nutricional', 'estado_nutricional', 'carne_salud', 'control_crecimiento', 'carne_crecimiento', 'vacunas', 'fecha_toma', 'observaciones']:
            if clean_text(sn.get(key)) and not clean_text(nino.get(key)):
                nino[key] = sn.get(key)
        alertas = calcular_alertas_nutricionales(nino)
        nino['alertas_json'] = json.dumps(alertas, ensure_ascii=False)
        if doc not in salud and salud_rows:
            repo.registrar_inconsistencia({
                'version_id': version_id,
                'tipo_fuente': 'salud_nutricion',
                'severidad': 'ADVERTENCIA',
                'tipo': 'NINO_SIN_SALUD_NUTRICION',
                'documento': doc,
                'nombre': nino.get('nombre_completo'),
                'unidad_servicio': nino.get('unidad_servicio'),
                'descripcion': 'Niño presente en Cuéntame sin registro asociado en salud/nutrición.',
                'corporacion_id': corporacion_id,
                'fundacion_id': fundacion_id,
            })

    # Niños que aparecen en salud/nutrición pero no en Cuéntame.
    for doc, sn in salud.items():
        if doc not in ninos:
            repo.registrar_inconsistencia({
                'version_id': version_id,
                'tipo_fuente': 'salud_nutricion',
                'severidad': 'ADVERTENCIA',
                'tipo': 'SALUD_SIN_CUENTAME',
                'documento': doc,
                'nombre': sn.get('nombre_completo'),
                'unidad_servicio': sn.get('unidad_servicio'),
                'descripcion': 'Registro de salud/nutrición sin niño correspondiente en Cuéntame.',
                'corporacion_id': corporacion_id,
                'fundacion_id': fundacion_id,
            })

    active_old = repo.fetch_all("SELECT * FROM master_ninos WHERE fundacion_id = ? AND activo = 1", (fundacion_id,))
    old_by_doc = {normalize_doc(row.get('documento')): row for row in active_old if normalize_doc(row.get('documento'))}

    with repo.connect() as conn:
        cur = conn.cursor()
        # Inserción de niños maestros.
        for doc, nino in ninos.items():
            cur.execute(
                """
                INSERT INTO master_ninos
                (version_id, activo, documento, tipo_documento, nombres, apellidos, nombre_completo, fecha_nacimiento,
                 edad_meses, grupo_etario, sexo, estado, fecha_ingreso, fecha_retiro, unidad_servicio, codigo_unidad,
                 coordinador, docente, modalidad, peso, talla, perimetro_braquial, diagnostico_nutricional,
                 estado_nutricional, carne_salud, control_crecimiento, carne_crecimiento, vacunas, alertas_json,
                 fuente_cuentame_carga_id, fuente_nutricion_carga_id, fuente_talento_carga_id, fuente_original,
                 archivo_origen, corporacion_id, fundacion_id, estado_validacion, fecha_carga, fecha_consolidacion,
                 usuario_consolida, datos_json, fecha_actualizacion)
                VALUES (?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'VALIDADO', ?, ?, ?, ?, ?)
                """,
                (
                    version_id, doc, nino.get('tipo_documento'), nino.get('nombres'), nino.get('apellidos'),
                    nino.get('nombre_completo'), nino.get('fecha_nacimiento'), nino.get('edad_meses'), nino.get('grupo_etario'),
                    nino.get('sexo'), nino.get('estado') or 'ACTIVO', nino.get('fecha_ingreso'), nino.get('fecha_retiro'),
                    nino.get('unidad_servicio'), nino.get('codigo_unidad'), nino.get('coordinador'), nino.get('docente'),
                    nino.get('modalidad'), nino.get('peso'), nino.get('talla'), nino.get('perimetro_braquial'),
                    nino.get('diagnostico_nutricional'), nino.get('estado_nutricional'), nino.get('carne_salud'),
                    nino.get('control_crecimiento'), nino.get('carne_crecimiento'), nino.get('vacunas'),
                    nino.get('alertas_json') or '[]', carga_cuentame.get('id') if carga_cuentame else None,
                    carga_salud.get('id') if carga_salud else None, carga_talento.get('id') if carga_talento else None,
                    'BASE_MAESTRA_ALPHA28',
                    carga_cuentame.get('nombre_archivo_original') if carga_cuentame else 'TABLA_ACTUAL_USUARIOS',
                    corporacion_id, fundacion_id, now, now, ctx.get('usuario'),
                    json.dumps(nino, ensure_ascii=False, default=str), now,
                ),
            )
            if doc in salud:
                sn = salud[doc]
                cur.execute(
                    """
                    INSERT INTO master_salud_nutricion
                    (version_id, activo, documento, peso, talla, perimetro_braquial, diagnostico_nutricional,
                     estado_nutricional, carne_salud, control_crecimiento, carne_crecimiento, vacunas, fecha_toma,
                     observaciones, alertas_json, fuente_carga_id, corporacion_id, fundacion_id, fecha_consolidacion, datos_json)
                    VALUES (?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        version_id, doc, sn.get('peso'), sn.get('talla'), sn.get('perimetro_braquial'),
                        sn.get('diagnostico_nutricional'), sn.get('estado_nutricional'), sn.get('carne_salud'),
                        sn.get('control_crecimiento'), sn.get('carne_crecimiento'), sn.get('vacunas'), sn.get('fecha_toma'),
                        sn.get('observaciones'), sn.get('alertas_json') or nino.get('alertas_json') or '[]',
                        carga_salud.get('id') if carga_salud else None, corporacion_id, fundacion_id, now,
                        json.dumps(sn, ensure_ascii=False, default=str),
                    ),
                )

        # Talento humano maestro.
        for item in talento_rows:
            cur.execute(
                """
                INSERT INTO master_talento_humano
                (version_id, activo, documento, tipo_documento, nombres, apellidos, nombre_completo, cargo,
                 rol_normalizado, unidad_servicio, coordinador, telefono, correo, estado, fuente_carga_id,
                 corporacion_id, fundacion_id, fecha_consolidacion, datos_json)
                VALUES (?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    version_id, normalize_doc(item.get('documento')), item.get('tipo_documento'), item.get('nombres'),
                    item.get('apellidos'), item.get('nombre_completo'), item.get('cargo'), item.get('rol_normalizado'),
                    item.get('unidad_servicio'), item.get('coordinador'), item.get('telefono'), item.get('correo'),
                    item.get('estado') or 'ACTIVO', carga_talento.get('id') if carga_talento else None,
                    corporacion_id, fundacion_id, now, json.dumps(item, ensure_ascii=False, default=str),
                ),
            )

        # Unidades maestras.
        unidades: dict[str, dict[str, Any]] = {}
        for n in ninos.values():
            unidad = normalize_name(n.get('unidad_servicio'))
            if not unidad:
                continue
            entry = unidades.setdefault(unidad, {'nombre': unidad, 'codigo_unidad': n.get('codigo_unidad'), 'coordinador': n.get('coordinador'), 'modalidad': n.get('modalidad'), 'total_ninos': 0})
            entry['total_ninos'] += 1
            if not entry.get('coordinador') and n.get('coordinador'):
                entry['coordinador'] = n.get('coordinador')
        for unidad, entry in unidades.items():
            entry['total_talento'] = len(talento_by_unidad.get(unidad, []))
            cur.execute(
                """
                INSERT INTO master_unidades
                (version_id, activo, nombre, codigo_unidad, coordinador, total_ninos, total_talento,
                 modalidad, corporacion_id, fundacion_id, fecha_consolidacion, datos_json)
                VALUES (?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    version_id, unidad, entry.get('codigo_unidad'), entry.get('coordinador'), entry.get('total_ninos'),
                    entry.get('total_talento'), entry.get('modalidad'), corporacion_id, fundacion_id, now,
                    json.dumps(entry, ensure_ascii=False, default=str),
                ),
            )
        conn.commit()

    # Movimientos e historial frente a la versión activa anterior.
    registrar_movimientos_historial(repo, version_id, ninos, old_by_doc, fundacion_id, corporacion_id, ctx)

    inconsistencias = repo.fetch_all("SELECT * FROM master_inconsistencias WHERE version_id = ?", (version_id,))
    criticas = sum(1 for item in inconsistencias if item.get('severidad') == 'CRITICA')
    advertencias = sum(1 for item in inconsistencias if item.get('severidad') != 'CRITICA')
    calidad = round(max(0, 100 - (criticas * 5) - (advertencias * 0.5)), 2)
    resumen = resumen_de_version(repo, version_id, fundacion_id)
    resumen.update({'errores_criticos': criticas, 'advertencias': advertencias, 'calidad_porcentaje': calidad})
    repo.actualizar_version_resumen(version_id, resumen, criticas, advertencias, calidad)
    return {
        'message': 'Base Maestra consolidada en borrador. La versión activa anterior no fue modificada.',
        'version_id': version_id,
        'estado': 'BORRADOR',
        'resumen': resumen,
        'inconsistencias': inconsistencias[:100],
        'puede_publicar': criticas == 0,
    }


def registrar_movimientos_historial(repo: BaseMaestraRepository, version_id: int, ninos: dict[str, dict[str, Any]], old_by_doc: dict[str, dict[str, Any]], fundacion_id: int, corporacion_id: int, ctx: dict[str, Any]) -> None:
    now = now_iso()
    new_docs = set(ninos.keys())
    old_docs = set(old_by_doc.keys())
    movimientos = []
    historial = []
    for doc in sorted(new_docs - old_docs):
        n = ninos[doc]
        movimientos.append(('NUEVO', doc, n.get('nombre_completo'), None, n.get('unidad_servicio'), None, n.get('coordinador'), None, n.get('estado'), None, n.get('diagnostico_nutricional'), 'Niño nuevo en la versión consolidada.', n))
    for doc in sorted(old_docs - new_docs):
        old = old_by_doc[doc]
        movimientos.append(('RETIRADO', doc, old.get('nombre_completo'), old.get('unidad_servicio'), None, old.get('coordinador'), None, old.get('estado'), None, old.get('diagnostico_nutricional'), None, 'Niño no aparece en la nueva consolidación.', old))
    for doc in sorted(new_docs & old_docs):
        n = ninos[doc]
        old = old_by_doc[doc]
        changed = False
        comparisons = [
            ('unidad_servicio', 'CAMBIO_UNIDAD'),
            ('coordinador', 'CAMBIO_COORDINADOR'),
            ('estado', 'CAMBIO_ESTADO'),
            ('diagnostico_nutricional', 'CAMBIO_DIAGNOSTICO_NUTRICIONAL'),
        ]
        for field, tipo in comparisons:
            old_val = clean_text(old.get(field))
            new_val = clean_text(n.get(field))
            if old_val != new_val:
                changed = True
                historial.append((doc, field, old_val, new_val, tipo, n))
                movimientos.append((tipo, doc, n.get('nombre_completo'), old.get('unidad_servicio'), n.get('unidad_servicio'), old.get('coordinador'), n.get('coordinador'), old.get('estado'), n.get('estado'), old.get('diagnostico_nutricional'), n.get('diagnostico_nutricional'), f'Cambio detectado en {field}.', n))
        if not changed:
            movimientos.append(('PERMANECE', doc, n.get('nombre_completo'), old.get('unidad_servicio'), n.get('unidad_servicio'), old.get('coordinador'), n.get('coordinador'), old.get('estado'), n.get('estado'), old.get('diagnostico_nutricional'), n.get('diagnostico_nutricional'), 'Niño permanece sin cambios principales.', n))
    with repo.connect() as conn:
        for m in movimientos:
            conn.execute(
                """
                INSERT INTO master_movimientos
                (version_id, tipo_movimiento, documento, nombre, unidad_anterior, unidad_nueva,
                 coordinador_anterior, coordinador_nuevo, estado_anterior, estado_nuevo,
                 diagnostico_anterior, diagnostico_nuevo, detalle, corporacion_id, fundacion_id,
                 fecha_movimiento, datos_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (version_id, *m[:12], corporacion_id, fundacion_id, now, json.dumps(m[12], ensure_ascii=False, default=str)),
            )
        for h in historial:
            conn.execute(
                """
                INSERT INTO master_historial_cambios
                (version_id, documento, campo, valor_anterior, valor_nuevo, tipo_movimiento, fuente_cambio,
                 archivo_origen, usuario, corporacion_id, fundacion_id, fecha_cambio, datos_json)
                VALUES (?, ?, ?, ?, ?, ?, 'BASE_MAESTRA', 'CONSOLIDACION_ALPHA28', ?, ?, ?, ?, ?)
                """,
                (version_id, h[0], h[1], h[2], h[3], h[4], ctx.get('usuario'), corporacion_id, fundacion_id, now, json.dumps(h[5], ensure_ascii=False, default=str)),
            )
        conn.commit()


def resumen_de_version(repo: BaseMaestraRepository, version_id: int | None, fundacion_id: int) -> dict[str, Any]:
    where_version = 'version_id = ?' if version_id else 'fundacion_id = ? AND activo = 1'
    param = (version_id,) if version_id else (fundacion_id,)
    with repo.connect() as conn:
        total_ninos = conn.execute(f"SELECT COUNT(*) c FROM master_ninos WHERE {where_version}", param).fetchone()['c']
        total_unidades = conn.execute(f"SELECT COUNT(*) c FROM master_unidades WHERE {where_version}", param).fetchone()['c']
        total_coord = conn.execute(f"SELECT COUNT(DISTINCT COALESCE(coordinador,'')) c FROM master_ninos WHERE {where_version} AND COALESCE(coordinador,'') <> ''", param).fetchone()['c']
        activos = conn.execute(f"SELECT COUNT(*) c FROM master_ninos WHERE {where_version} AND UPPER(COALESCE(estado,'')) NOT LIKE '%RETIR%'", param).fetchone()['c']
        alertas = conn.execute(f"SELECT COUNT(*) c FROM master_ninos WHERE {where_version} AND COALESCE(alertas_json,'[]') NOT IN ('[]','')", param).fetchone()['c']
        duplicados = conn.execute("SELECT COUNT(*) c FROM master_inconsistencias WHERE version_id = ? AND tipo LIKE '%DUPLICADO%'", (version_id or 0,)).fetchone()['c'] if version_id else 0
        criticas = conn.execute("SELECT COUNT(*) c FROM master_inconsistencias WHERE version_id = ? AND severidad = 'CRITICA'", (version_id or 0,)).fetchone()['c'] if version_id else 0
        advertencias = conn.execute("SELECT COUNT(*) c FROM master_inconsistencias WHERE version_id = ? AND severidad <> 'CRITICA'", (version_id or 0,)).fetchone()['c'] if version_id else 0
        movs = {}
        if version_id:
            for row in conn.execute("SELECT tipo_movimiento, COUNT(*) total FROM master_movimientos WHERE version_id = ? GROUP BY tipo_movimiento", (version_id,)).fetchall():
                movs[row['tipo_movimiento']] = row['total']
    return {
        'total_ninos': int(total_ninos or 0),
        'total_unidades': int(total_unidades or 0),
        'total_coordinadores': int(total_coord or 0),
        'total_ninos_activos': int(activos or 0),
        'total_alertas': int(alertas or 0),
        'duplicados': int(duplicados or 0),
        'errores_criticos': int(criticas or 0),
        'advertencias': int(advertencias or 0),
        'movimientos': movs,
        'calidad_porcentaje': round(max(0, 100 - int(criticas or 0) * 5 - int(advertencias or 0) * 0.5), 2),
    }



# -----------------------------------------------------------------------------
# ALPHA31 — Panel Principal alimentado por Base Maestra publicada
# -----------------------------------------------------------------------------
GRUPO_RPP_LABELS = {
    'rpp_0_6_gestantes': '0 A 6 MESES Y GESTANTES',
    'rpp_6_11': '6 A 11 MESES 29 DIAS',
    'rpp_1_2': '1 A 2 ANOS 11 MESES',
    'rpp_3_5': '3 A 5 ANOS 11 MESES',
    'inconsistente': 'SIN CLASIFICAR',
}

DOCUMENTAL_ALIASES = {
    'registro_civil': ['registro_civil', 'registro', 'rc', 'documento_nino', 'documento_niño', 'soporte_documento', 'documento_identidad_soporte'],
    'documento_acudiente': ['documento_acudiente', 'cedula_acudiente', 'identificacion_acudiente', 'doc_acudiente', 'documento_madre_padre'],
    'afiliacion_salud': ['afiliacion_salud', 'eps', 'certificado_eps', 'soporte_eps', 'seguridad_social', 'sisben'],
    'carne_salud': ['carne_salud', 'carnet_salud', 'carné_salud', 'carne_de_salud'],
    'vacunas': ['vacunas', 'esquema_vacunacion', 'esquema_vacunación', 'carnet_vacunas'],
    'crecimiento_desarrollo': ['control_crecimiento', 'crecimiento_desarrollo', 'control_cyd', 'control_de_crecimiento_y_desarrollo'],
}


def parse_json_safe(value: Any) -> dict[str, Any]:
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def raw_pick(raw: dict[str, Any], aliases: list[str]) -> Any:
    if not raw:
        return ''
    normalized = {norm_key(k): v for k, v in raw.items()}
    for alias in aliases:
        key = norm_key(alias)
        if key in normalized and clean_text(normalized.get(key)):
            return normalized.get(key)
    return ''


def valor_presente_si(value: Any) -> bool:
    text = norm_key(value)
    if not text:
        return False
    negativos = {'no', 'n', 'false', '0', 'pendiente', 'sin_dato', 'sin', 'no_aplica', 'na', 'ninguno'}
    if text in negativos:
        return False
    if any(marker in text for marker in ['no_tiene', 'sin_', 'pendiente', 'faltante', 'vencido']):
        return False
    return True


def parse_fecha(value: Any) -> datetime | None:
    text = clean_text(value)
    if not text:
        return None
    # pandas maneja Excel serial, ISO, dd/mm/yyyy y varios formatos regionales.
    try:
        dt = pd.to_datetime(text, errors='coerce', dayfirst=True)
        if pd.isna(dt):
            return None
        return dt.to_pydatetime()
    except Exception:
        return None


def calcular_edad_meses_segura(row: dict[str, Any], referencia: datetime | None = None) -> int | None:
    edad = to_int(row.get('edad_meses'))
    if edad is not None and edad >= 0:
        return edad
    fecha = parse_fecha(row.get('fecha_nacimiento'))
    if not fecha:
        return None
    ref = referencia or datetime.now()
    meses = (ref.year - fecha.year) * 12 + (ref.month - fecha.month)
    if ref.day < fecha.day:
        meses -= 1
    return max(0, meses)


def clasificar_grupo_etario_operativo(row: dict[str, Any]) -> str:
    grupo = norm_key(row.get('grupo_etario') or '')
    estado = norm_key(row.get('estado') or '')
    tipo = norm_key(row.get('tipo_beneficiario') or row.get('datos_json') or '')
    texto = f'{grupo} {estado} {tipo}'
    if 'gestante' in texto:
        return 'rpp_0_6_gestantes'
    if '0_a_6' in texto or '0_6' in texto or 'menor_de_seis' in texto or '0_a_5' in texto:
        return 'rpp_0_6_gestantes'
    if '6_a_11' in texto or '6_11' in texto:
        return 'rpp_6_11'
    if '1_a_2' in texto or '1_2' in texto or 'uno_a_dos' in texto:
        return 'rpp_1_2'
    if '3_a_5' in texto or '3_5' in texto or 'tres_a_cinco' in texto:
        return 'rpp_3_5'
    meses = calcular_edad_meses_segura(row)
    if meses is None:
        return 'inconsistente'
    # Evita solapamientos cuando no existe grupo textual confiable.
    if 0 <= meses <= 5:
        return 'rpp_0_6_gestantes'
    if 6 <= meses <= 11:
        return 'rpp_6_11'
    if 12 <= meses <= 35:
        return 'rpp_1_2'
    if 36 <= meses <= 71:
        return 'rpp_3_5'
    return 'inconsistente'


def es_nino_activo_operativo(row: dict[str, Any]) -> bool:
    estado = norm_key(row.get('estado') or '')
    if not estado:
        return True
    return not any(token in estado for token in ['retir', 'inactiv', 'egres', 'desvincul', 'cancelad'])


def indicadores_faltantes_nino(row: dict[str, Any]) -> dict[str, bool]:
    raw = parse_json_safe(row.get('datos_json'))
    carne_salud = row.get('carne_salud') or raw_pick(raw, DOCUMENTAL_ALIASES['carne_salud'])
    vacunas = row.get('vacunas') or raw_pick(raw, DOCUMENTAL_ALIASES['vacunas'])
    crecimiento = row.get('control_crecimiento') or raw_pick(raw, DOCUMENTAL_ALIASES['crecimiento_desarrollo'])
    registro_civil = raw_pick(raw, DOCUMENTAL_ALIASES['registro_civil']) or row.get('documento')
    documento_acudiente = raw_pick(raw, DOCUMENTAL_ALIASES['documento_acudiente'])
    afiliacion = raw_pick(raw, DOCUMENTAL_ALIASES['afiliacion_salud'])
    peso = row.get('peso')
    talla = row.get('talla')
    perimetro = row.get('perimetro_braquial')
    diagnostico = row.get('diagnostico_nutricional') or row.get('estado_nutricional')
    return {
        'sin_registro_civil': not valor_presente_si(registro_civil),
        'sin_documento_acudiente': not valor_presente_si(documento_acudiente),
        'sin_afiliacion_salud': not valor_presente_si(afiliacion),
        'sin_carne_salud': not valor_presente_si(carne_salud),
        'sin_vacunas': not valor_presente_si(vacunas),
        'sin_crecimiento_desarrollo': not valor_presente_si(crecimiento),
        'sin_peso': peso in {None, ''},
        'sin_talla': talla in {None, ''},
        'sin_peso_talla': peso in {None, ''} and talla in {None, ''},
        'sin_perimetro_braquial': perimetro in {None, ''},
        'sin_diagnostico_nutricional': not clean_text(diagnostico),
    }


def fila_nino_panel(row: dict[str, Any]) -> dict[str, Any]:
    raw = parse_json_safe(row.get('datos_json'))
    grupo_codigo = clasificar_grupo_etario_operativo(row)
    edad_meses = calcular_edad_meses_segura(row)
    nombre = row.get('nombre_completo') or clean_text(f"{row.get('nombres') or ''} {row.get('apellidos') or ''}")
    acudiente = raw_pick(raw, ['acudiente', 'nombre_acudiente', 'madre', 'padre', 'cuidador', 'responsable'])
    parentesco = raw_pick(raw, ['parentesco', 'parentesco_acudiente'])
    faltantes = indicadores_faltantes_nino(row)
    alertas = []
    try:
        alertas = json.loads(row.get('alertas_json') or '[]')
        if not isinstance(alertas, list):
            alertas = []
    except Exception:
        alertas = []
    alertas.extend([k.replace('_', ' ').upper() for k, faltante in faltantes.items() if faltante and k in {'sin_peso_talla', 'sin_vacunas', 'sin_crecimiento_desarrollo', 'sin_carne_salud'}])
    return {
        'Nombre': nombre,
        'Documento': row.get('documento'),
        'NUI': row.get('documento'),
        'TipoDocumento': row.get('tipo_documento'),
        'EdadMeses': edad_meses,
        'EdadCompleta': 'Gestante' if grupo_codigo == 'rpp_0_6_gestantes' and 'gestante' in norm_key(row.get('grupo_etario')) else '',
        'GrupoEdad': GRUPO_RPP_LABELS.get(grupo_codigo, 'SIN CLASIFICAR'),
        'GrupoRpp': grupo_codigo,
        'Sexo': row.get('sexo'),
        'Estado': row.get('estado'),
        'Unidad': row.get('unidad_servicio'),
        'Coordinador': row.get('coordinador'),
        'Docente': row.get('docente'),
        'Peso': row.get('peso'),
        'Talla': row.get('talla'),
        'PerimetroBraquial': row.get('perimetro_braquial'),
        'DiagnosticoNutricional': row.get('diagnostico_nutricional') or row.get('estado_nutricional'),
        'Vacunas': row.get('vacunas'),
        'CarneSalud': row.get('carne_salud'),
        'CrecimientoDesarrollo': row.get('control_crecimiento'),
        'Acudiente': acudiente,
        'Parentesco': parentesco,
        'faltantes': faltantes,
        'alertas': sorted(set(clean_text(a) for a in alertas if clean_text(a))),
    }


def fuente_estado_base_maestra(database_path: str, ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    ctx = {**get_user_context(), **(ctx or {})}
    fundacion_id = int(ctx.get('fundacion_id') or 1)
    repo = BaseMaestraRepository(database_path)
    repo.init_schema()
    fuentes = []
    for tipo in ['cuentame', 'talento_humano', 'salud_nutricion']:
        carga = repo.fetch_one(
            """
            SELECT * FROM cargas_archivos
            WHERE tipo_fuente = ? AND fundacion_id = ?
            ORDER BY fecha_carga DESC, id DESC LIMIT 1
            """,
            (tipo, fundacion_id),
        )
        fuentes.append({
            'tipo_fuente': tipo,
            'carga': carga,
            'cargada': bool(carga),
            'estado': carga.get('estado') if carga else 'sin_cargar',
            'total_registros': int(carga.get('total_registros') or 0) if carga else 0,
            'fecha_carga': carga.get('fecha_carga') if carga else None,
        })
    version = repo.version_activa(fundacion_id)
    return {'fuentes': fuentes, 'version_activa': version}


def dashboard_operativo_base_maestra(database_path: str, ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    """Devuelve el mismo contrato que usa el Panel Principal histórico.

    Fuente única: master_ninos/master_talento_humano/master_unidades activos.
    Si no hay versión publicada, devuelve estructura vacía sin tocar el flujo anterior.
    """
    ctx = {**get_user_context(), **(ctx or {})}
    fundacion_id = int(ctx.get('fundacion_id') or 1)
    repo = BaseMaestraRepository(database_path)
    repo.init_schema()
    version = repo.version_activa(fundacion_id)
    if not version:
        return {
            'fuente': 'base_maestra',
            'fuente_activa': False,
            'version_activa': None,
            'message': 'No hay Base Maestra publicada todavía.',
            'unidades': {},
            'stats': {
                'total_usuarios': 0,
                'alertas_cobertura': 0,
                'unidades_sin_cobertura': [],
                'proximos_retiros': 0,
                'proximos_retiros_lista': [],
                'falta_nutricion': 0,
                'grupos_edad_totales': {},
                'documentos_faltantes': {},
            },
        }

    rows = repo.fetch_all(
        """
        SELECT * FROM master_ninos
        WHERE fundacion_id = ? AND activo = 1
        ORDER BY unidad_servicio, nombre_completo, documento
        """,
        (fundacion_id,),
    )
    talento = repo.fetch_all(
        """
        SELECT * FROM master_talento_humano
        WHERE fundacion_id = ? AND activo = 1
        ORDER BY unidad_servicio, rol_normalizado, nombre_completo
        """,
        (fundacion_id,),
    )
    docente_por_unidad: dict[str, str] = {}
    talento_por_unidad: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for th in talento:
        unidad = normalize_name(th.get('unidad_servicio'))
        if not unidad:
            continue
        talento_por_unidad[unidad].append(th)
        rol = norm_key(th.get('rol_normalizado') or th.get('cargo'))
        nombre = th.get('nombre_completo') or th.get('nombres') or th.get('documento') or ''
        if unidad not in docente_por_unidad and ('docente' in rol or 'agente' in rol):
            docente_por_unidad[unidad] = nombre
    for unidad, items in talento_por_unidad.items():
        if unidad not in docente_por_unidad and items:
            docente_por_unidad[unidad] = items[0].get('nombre_completo') or items[0].get('nombres') or ''

    unidades: dict[str, dict[str, Any]] = {}
    grupos_totales: Counter[str] = Counter()
    faltantes_totales: Counter[str] = Counter()
    proximos_retiros = []
    total_activos = 0
    falta_nutricion = 0

    for row in rows:
        if not es_nino_activo_operativo(row):
            # Se conserva para movimientos, pero el panel operativo muestra atendidos activos.
            continue
        total_activos += 1
        unidad = normalize_name(row.get('unidad_servicio')) or 'SIN UNIDAD'
        unidad_data = unidades.setdefault(unidad, {
            'total_usuarios': 0,
            'alerta_cobertura': False,
            'usuarios_criticos': [],
            'nutricion_pendiente': 0,
            'documentos_faltantes': {},
            'grupos_edad': {},
            'datos_completos': [],
            'docente_asignado': docente_por_unidad.get(unidad) or '',
            'coordinador': row.get('coordinador') or '',
            'fuente': 'base_maestra',
        })
        item = fila_nino_panel(row)
        unidad_data['datos_completos'].append(item)
        unidad_data['total_usuarios'] += 1
        grupo_label = item.get('GrupoEdad') or 'SIN CLASIFICAR'
        unidad_data['grupos_edad'][grupo_label] = int(unidad_data['grupos_edad'].get(grupo_label, 0)) + 1
        grupos_totales[grupo_label] += 1
        faltantes = item.get('faltantes') or {}
        for key, missing in faltantes.items():
            if missing:
                faltantes_totales[key] += 1
                unidad_data['documentos_faltantes'][key] = int(unidad_data['documentos_faltantes'].get(key, 0)) + 1
        if faltantes.get('sin_peso') or faltantes.get('sin_talla'):
            unidad_data['nutricion_pendiente'] += 1
            falta_nutricion += 1
        edad_meses = item.get('EdadMeses')
        estado = norm_key(row.get('estado'))
        if (edad_meses is not None and edad_meses >= 60) or 'retir' in estado:
            proximos_retiros.append({
                'nombre': item.get('Nombre'),
                'documento': item.get('Documento'),
                'unidad': unidad,
                'edad_meses': edad_meses,
                'edad_completa': item.get('EdadCompleta'),
            })
        if item.get('alertas'):
            unidad_data['usuarios_criticos'].append({
                'nombre': item.get('Nombre'),
                'documento': item.get('Documento'),
                'motivo': '; '.join(item.get('alertas')[:4]),
            })

    unidades_sin_cobertura = []
    unidades_sin_agente = []
    for unidad, data in unidades.items():
        total = int(data.get('total_usuarios') or 0)
        data['alerta_cobertura'] = total > 0 and total < 20
        if data['alerta_cobertura']:
            unidades_sin_cobertura.append({'unidad': unidad, 'total': total, 'meta': 20})
        if not clean_text(data.get('docente_asignado')):
            data['docente_asignado'] = 'Sin agente educativo asignado'
            unidades_sin_agente.append(unidad)
        data['usuarios_criticos'] = data['usuarios_criticos'][:5]

    stats = {
        'total_usuarios': total_activos,
        'total_unidades': len(unidades),
        'total_coordinadores': len({normalize_name(r.get('coordinador')) for r in rows if normalize_name(r.get('coordinador'))}),
        'alertas_cobertura': len(unidades_sin_cobertura),
        'unidades_sin_cobertura': unidades_sin_cobertura,
        'unidades_sin_agente': unidades_sin_agente,
        'proximos_retiros': len(proximos_retiros),
        'proximos_retiros_lista': proximos_retiros[:20],
        'falta_nutricion': falta_nutricion,
        'grupos_edad_totales': dict(grupos_totales),
        'documentos_faltantes': dict(faltantes_totales),
        'base_maestra_version_id': version.get('id'),
        'base_maestra_version_numero': version.get('version_numero'),
    }
    return {
        'fuente': 'base_maestra',
        'fuente_activa': True,
        'version_activa': version,
        'unidades': unidades,
        'stats': stats,
    }


def diagnostico_unidades_base_maestra(database_path: str, ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    dashboard = dashboard_operativo_base_maestra(database_path, ctx)
    unidades = dashboard.get('unidades') or {}
    lista = []
    for nombre, data in unidades.items():
        lista.append({
            'unidad': nombre,
            'usuarios_detectados': data.get('total_usuarios') or 0,
            'agente_educativo': data.get('docente_asignado') or 'Sin agente educativo asignado',
            'alertas_criticas': data.get('usuarios_criticos') or [],
            'pendientes_salud_nutricion': data.get('nutricion_pendiente') or 0,
            'grupos_edad': data.get('grupos_edad') or {},
            'documentos_faltantes': data.get('documentos_faltantes') or {},
        })
    return {'version_activa': dashboard.get('version_activa'), 'unidades': lista, 'stats': dashboard.get('stats') or {}}


def detalle_unidad_base_maestra(database_path: str, unidad: str, ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    dashboard = dashboard_operativo_base_maestra(database_path, ctx)
    unidades = dashboard.get('unidades') or {}
    normalizada = normalize_name(unidad)
    data = unidades.get(normalizada)
    if not data:
        # búsqueda tolerante por normalización de tildes/espacios
        for nombre, info in unidades.items():
            if norm_key(nombre) == norm_key(unidad):
                normalizada, data = nombre, info
                break
    if not data:
        return {'unidad': unidad, 'encontrada': False, 'usuarios': [], 'grupos_edad': {}, 'pendientes': {}}
    return {
        'unidad': normalizada,
        'encontrada': True,
        'usuarios': data.get('datos_completos') or [],
        'grupos_edad': data.get('grupos_edad') or {},
        'pendientes': data.get('documentos_faltantes') or {},
        'nutricion_pendiente': data.get('nutricion_pendiente') or 0,
        'agente_educativo': data.get('docente_asignado'),
    }

def publicar_base_maestra(database_path: str, version_id: int, ctx: dict[str, Any] | None = None, observaciones: str = '') -> dict[str, Any]:
    ctx = {**get_user_context(), **(ctx or {})}
    repo = BaseMaestraRepository(database_path)
    repo.init_schema()
    if ctx.get('rol') not in {'SUPERADMIN', 'GERENTE', 'AUXILIAR_ADMINISTRATIVO'}:
        raise PermissionError('No tienes permiso para publicar la Base Maestra.')
    result = repo.publicar_version(version_id, ctx, observaciones=observaciones)
    result['message'] = 'Base Maestra publicada correctamente. La versión anterior quedó archivada.'
    return result


def dashboard_base_maestra(database_path: str, ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    ctx = {**get_user_context(), **(ctx or {})}
    fundacion_id = int(ctx.get('fundacion_id') or 1)
    repo = BaseMaestraRepository(database_path)
    repo.init_schema()
    version = repo.version_activa(fundacion_id)
    if version:
        resumen = resumen_de_version(repo, int(version['id']), fundacion_id)
        try:
            version['resumen'] = json.loads(version.get('resumen_json') or '{}')
        except Exception:
            version['resumen'] = {}
    else:
        resumen = resumen_de_version(repo, None, fundacion_id)
    cargas_todas = repo.fetch_all("SELECT * FROM cargas_archivos WHERE fundacion_id = ? ORDER BY fecha_carga DESC, id DESC", (fundacion_id,))
    cargas = cargas_todas[:20]
    nombres_fuente = {
        'cuentame': 'Base Cuéntame / Niños',
        'talento_humano': 'Talento Humano',
        'salud_nutricion': 'Salud y Nutrición',
    }
    resumen_fuentes = []
    for tipo, nombre in nombres_fuente.items():
        cargas_fuente = [carga for carga in cargas_todas if normalize_tipo_fuente(carga.get('tipo_fuente')) == tipo]
        ultima = cargas_fuente[0] if cargas_fuente else None
        resumen_fuentes.append({
            'tipo_fuente': tipo,
            'nombre_fuente': nombre,
            'identificador': tipo.upper(),
            'total_cargas': len(cargas_fuente),
            'total_registros': sum(int(carga.get('total_registros') or 0) for carga in cargas_fuente),
            'ultima_carga': ultima,
            'estado': ultima.get('estado') if ultima else 'sin_cargar',
        })
    unidades_por_fuente: dict[str, dict[str, Any]] = {}
    cargas_matriz: dict[str, int | None] = {}
    for tipo in nombres_fuente:
        filas, carga_fuente = latest_rows_for_type(repo, tipo, fundacion_id)
        cargas_matriz[tipo] = int(carga_fuente['id']) if carga_fuente else None
        documentos_contados: set[tuple[str, str]] = set()
        for indice, fila in enumerate(filas):
            unidad_original = clean_text(fila.get('unidad_servicio')) or 'SIN UNIDAD IDENTIFICADA'
            unidad_clave = normalize_name(unidad_original) or 'SIN UNIDAD IDENTIFICADA'
            documento = normalize_doc(fila.get('documento')) or f'FILA_{indice}'
            llave = (unidad_clave, documento)
            if llave in documentos_contados:
                continue
            documentos_contados.add(llave)
            item = unidades_por_fuente.setdefault(unidad_clave, {
                'unidad': unidad_original,
                'cuentame': 0,
                'talento_humano': 0,
                'salud_nutricion': 0,
            })
            item[tipo] += 1
    resumen_unidades_fuentes = {
        'criterio': 'usuarios_unicos_por_documento_y_unidad',
        'cargas_fuente': cargas_matriz,
        'unidades': sorted(unidades_por_fuente.values(), key=lambda item: normalize_name(item['unidad'])),
    }
    talento_filas, talento_carga = latest_rows_for_type(repo, 'talento_humano', fundacion_id)
    equipos: dict[str, dict[str, Any]] = {}
    personal_unico: dict[str, dict[str, Any]] = {}
    duplicados_talento = 0
    for indice, fila in enumerate(talento_filas):
        nombre = clean_text(fila.get('nombre_completo')) or clean_text(fila.get('nombres')) or normalize_doc(fila.get('documento')) or 'SIN NOMBRE'
        rol = normalizar_rol_talento(fila.get('cargo') or fila.get('rol_normalizado') or '')
        documento = normalize_doc(fila.get('documento'))
        clave_persona = documento or f"{norm_key(nombre)}|{norm_key(rol)}"
        if clave_persona in personal_unico:
            duplicados_talento += 1
            anterior = personal_unico[clave_persona]
            for campo in ('coordinador', 'unidad_servicio', 'telefono', 'correo', 'cargo'):
                if not clean_text(anterior.get(campo)) and clean_text(fila.get(campo)):
                    anterior[campo] = fila.get(campo)
            continue
        personal_unico[clave_persona] = dict(fila)
    for fila in personal_unico.values():
        nombre = clean_text(fila.get('nombre_completo')) or clean_text(fila.get('nombres')) or normalize_doc(fila.get('documento')) or 'SIN NOMBRE'
        rol = normalizar_rol_talento(fila.get('cargo') or fila.get('rol_normalizado') or '')
        coordinador = clean_text(fila.get('coordinador'))
        if rol == 'COORDINADOR':
            coordinador = nombre
        coordinador = normalize_name(coordinador) or 'SIN COORDINADOR ASIGNADO'
        equipo = equipos.setdefault(coordinador, {'coordinador': coordinador, 'total_personas': 0, 'cargos': {}, 'integrantes': []})
        equipo['total_personas'] += 1
        equipo['cargos'][rol] = int(equipo['cargos'].get(rol, 0)) + 1
        equipo['integrantes'].append({
            'nombre': nombre,
            'documento': fila.get('documento'),
            'cargo': fila.get('cargo') or '',
            'rol_normalizado': rol,
            'unidad_servicio': fila.get('unidad_servicio') or '',
            'telefono': fila.get('telefono') or '',
            'correo': fila.get('correo') or '',
        })
    estructura_talento = {
        'carga_id': talento_carga.get('id') if talento_carga else None,
        'total_filas_origen': len(talento_filas),
        'total_personas': len(personal_unico),
        'duplicados_omitidos': duplicados_talento,
        'sin_cargo': sum(1 for fila in personal_unico.values() if not clean_text(fila.get('cargo'))),
        'equipos': sorted(equipos.values(), key=lambda item: item['coordinador']),
    }
    borradores = repo.fetch_all("SELECT * FROM master_versiones WHERE fundacion_id = ? AND estado = 'BORRADOR' ORDER BY id DESC LIMIT 10", (fundacion_id,))
    return {'version_activa': version, 'resumen': resumen, 'resumen_fuentes': resumen_fuentes, 'resumen_unidades_fuentes': resumen_unidades_fuentes, 'estructura_talento': estructura_talento, 'cargas': cargas, 'borradores': borradores}


def listar_unidades(database_path: str, ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    ctx = {**get_user_context(), **(ctx or {})}
    repo = BaseMaestraRepository(database_path)
    repo.init_schema()
    return {'unidades': repo.fetch_all("SELECT * FROM master_unidades WHERE fundacion_id = ? AND activo = 1 ORDER BY nombre", (ctx.get('fundacion_id') or 1,))}


def listar_coordinadores(database_path: str, ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    ctx = {**get_user_context(), **(ctx or {})}
    repo = BaseMaestraRepository(database_path)
    repo.init_schema()
    return {'coordinadores': repo.fetch_all("SELECT DISTINCT coordinador FROM master_ninos WHERE fundacion_id = ? AND activo = 1 AND COALESCE(coordinador,'') <> '' ORDER BY coordinador", (ctx.get('fundacion_id') or 1,))}


def listar_inconsistencias(database_path: str, ctx: dict[str, Any] | None = None, limit: int = 500) -> dict[str, Any]:
    ctx = {**get_user_context(), **(ctx or {})}
    repo = BaseMaestraRepository(database_path)
    repo.init_schema()
    return {'inconsistencias': repo.fetch_all("SELECT * FROM master_inconsistencias WHERE fundacion_id = ? ORDER BY fecha_creacion DESC, id DESC LIMIT ?", (ctx.get('fundacion_id') or 1, limit))}


def listar_historial(database_path: str, ctx: dict[str, Any] | None = None, limit: int = 500) -> dict[str, Any]:
    ctx = {**get_user_context(), **(ctx or {})}
    repo = BaseMaestraRepository(database_path)
    repo.init_schema()
    return {'historial': repo.fetch_all("SELECT * FROM master_historial_cambios WHERE fundacion_id = ? ORDER BY fecha_cambio DESC, id DESC LIMIT ?", (ctx.get('fundacion_id') or 1, limit))}


def listar_movimientos(database_path: str, ctx: dict[str, Any] | None = None, limit: int = 500) -> dict[str, Any]:
    ctx = {**get_user_context(), **(ctx or {})}
    repo = BaseMaestraRepository(database_path)
    repo.init_schema()
    return {'movimientos': repo.fetch_all("SELECT * FROM master_movimientos WHERE fundacion_id = ? ORDER BY fecha_movimiento DESC, id DESC LIMIT ?", (ctx.get('fundacion_id') or 1, limit))}


def listar_corporaciones(database_path: str, ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    ctx = {**get_user_context(), **(ctx or {})}
    repo = BaseMaestraRepository(database_path)
    repo.init_schema()
    if ctx.get('rol') == 'SUPERADMIN':
        rows = repo.fetch_all("SELECT * FROM corporaciones ORDER BY nombre")
    else:
        rows = repo.fetch_all("SELECT * FROM corporaciones WHERE fundacion_id = ? ORDER BY nombre", (ctx.get('fundacion_id') or 1,))
    return {'corporaciones': rows}


def exportar_inconsistencias_excel(database_path: str, output_folder: str, ctx: dict[str, Any] | None = None) -> str:
    ctx = {**get_user_context(), **(ctx or {})}
    repo = BaseMaestraRepository(database_path)
    repo.init_schema()
    rows = repo.fetch_all("SELECT * FROM master_inconsistencias WHERE fundacion_id = ? ORDER BY fecha_creacion DESC", (ctx.get('fundacion_id') or 1,))
    os.makedirs(output_folder, exist_ok=True)
    filename = f"BASE_MAESTRA_INCONSISTENCIAS_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    path = os.path.join(output_folder, filename)
    pd.DataFrame(rows).to_excel(path, index=False)
    return path


def exportar_unidad_fuentes_excel(database_path: str, output_folder: str, unidad: str, ctx: dict[str, Any] | None = None) -> str:
    ctx = {**get_user_context(), **(ctx or {})}
    fundacion_id = int(ctx.get('fundacion_id') or 1)
    unidad_buscada = normalize_name(unidad)
    if not unidad_buscada:
        raise ValueError('La unidad de atención es requerida.')
    repo = BaseMaestraRepository(database_path)
    repo.init_schema()
    fuentes = {
        'cuentame': 'Cuéntame',
        'talento_humano': 'Talento Humano',
        'salud_nutricion': 'Salud y Nutrición',
    }
    detalle: dict[str, list[dict[str, Any]]] = {}
    resumen = []
    for tipo, nombre in fuentes.items():
        filas, carga = latest_rows_for_type(repo, tipo, fundacion_id)
        filtradas = [fila for fila in filas if normalize_name(fila.get('unidad_servicio')) == unidad_buscada]
        unicas = []
        vistos = set()
        for indice, fila in enumerate(filtradas):
            documento = normalize_doc(fila.get('documento')) or f'FILA_{indice}'
            if documento in vistos:
                continue
            vistos.add(documento)
            unicas.append(fila)
        detalle[tipo] = unicas
        resumen.append({
            'Unidad de atención': unidad,
            'Fuente': nombre,
            'Usuarios únicos': len(unicas),
            'ID carga utilizada': carga.get('id') if carga else None,
            'Archivo de origen': carga.get('nombre_archivo_original') if carga else 'Sin carga temporal',
        })
    os.makedirs(output_folder, exist_ok=True)
    nombre_seguro = secure_filename(unidad)[:80] or 'UNIDAD'
    filename = f"REGISTROS_UNIDAD_{nombre_seguro}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    path = os.path.join(output_folder, filename)
    with pd.ExcelWriter(path, engine='openpyxl') as writer:
        pd.DataFrame(resumen).to_excel(writer, sheet_name='Resumen', index=False)
        pd.DataFrame(detalle['cuentame']).to_excel(writer, sheet_name='Cuentame', index=False)
        pd.DataFrame(detalle['talento_humano']).to_excel(writer, sheet_name='Talento Humano', index=False)
        pd.DataFrame(detalle['salud_nutricion']).to_excel(writer, sheet_name='Salud y Nutricion', index=False)
    return path


def exportar_validacion_excel(database_path: str, output_folder: str, validacion_id: int, ctx: dict[str, Any] | None = None) -> str:
    ctx = {**get_user_context(), **(ctx or {})}
    repo = BaseMaestraRepository(database_path)
    repo.init_schema()
    val = repo.fetch_one("SELECT * FROM validaciones_cargas WHERE id = ?", (validacion_id,))
    if not val:
        raise ValueError('Validación no encontrada.')
    if ctx.get('rol') != 'SUPERADMIN' and int(val.get('fundacion_id') or 1) != int(ctx.get('fundacion_id') or 1):
        raise PermissionError('No tienes permiso para descargar esta validación.')
    issues = repo.fetch_all("SELECT * FROM master_inconsistencias WHERE carga_id = ? ORDER BY severidad, tipo", (val.get('carga_id'),))
    os.makedirs(output_folder, exist_ok=True)
    filename = f"BASE_MAESTRA_VALIDACION_{validacion_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    path = os.path.join(output_folder, filename)
    with pd.ExcelWriter(path, engine='openpyxl') as writer:
        pd.DataFrame([val]).to_excel(writer, sheet_name='Resumen', index=False)
        pd.DataFrame(issues).to_excel(writer, sheet_name='Inconsistencias', index=False)
    return path
