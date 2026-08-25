"""Reglas únicas para consolidar la relación mensual por grupo etario."""

from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter
from datetime import date, datetime
from typing import Any, Iterable


GRUPOS = ('gestantes', 'menores_6', 'seis_11', 'uno_2', 'tres_5')


def _texto(value: Any) -> str:
    raw = unicodedata.normalize('NFKD', str(value or ''))
    return re.sub(r'[^a-z0-9]+', ' ', ''.join(c for c in raw if not unicodedata.combining(c)).lower()).strip()


def _entero(value: Any) -> int | None:
    if value is None or str(value).strip() == '':
        return None
    try:
        result = int(float(str(value).replace(',', '.')))
        return result if result >= 0 else None
    except (TypeError, ValueError):
        return None


def _datos_json(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(value or '{}')
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def _buscar_dato(data: dict[str, Any], aliases: Iterable[str]) -> Any:
    wanted = tuple(_texto(alias) for alias in aliases)
    for key, value in data.items():
        key_norm = _texto(key)
        if any(alias == key_norm or alias in key_norm for alias in wanted):
            return value
        if isinstance(value, dict):
            nested = _buscar_dato(value, aliases)
            if nested not in (None, ''):
                return nested
    return None


def edad_meses_en_periodo(fecha_nacimiento: Any, anio: int, mes: int) -> int | None:
    raw = str(fecha_nacimiento or '').strip()
    if not raw:
        return None
    nacimiento = None
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d'):
        try:
            nacimiento = datetime.strptime(raw[:10], fmt).date()
            break
        except ValueError:
            continue
    if nacimiento is None:
        return None
    referencia = date(int(anio), int(mes), 1)
    meses = (referencia.year - nacimiento.year) * 12 + referencia.month - nacimiento.month
    if referencia.day < nacimiento.day:
        meses -= 1
    return max(0, meses)


def clasificar_participante(row: dict[str, Any], anio: int | None = None, mes: int | None = None) -> str | None:
    """Clasifica sin convertir edades ausentes en cero meses."""
    extra = _datos_json(row.get('datos_json'))
    grupo = row.get('grupo_etario') or row.get('tipo_beneficiario') or _buscar_dato(
        extra, ('grupo etario', 'tipo beneficiario', 'poblacion')
    )
    texto = _texto(grupo)
    combinado_gestantes = 'gestante' in texto and any(token in texto for token in ('0 a 6', 'menor 6', 'menores 6'))
    if 'gestante' in texto and not combinado_gestantes:
        return 'gestantes'

    edad = _entero(row.get('edad_meses'))
    if edad is None:
        edad = _entero(_buscar_dato(extra, ('edad meses', 'meses cumplidos', 'edad en meses')))
    if edad is None and anio and mes:
        fecha = row.get('fecha_nacimiento') or _buscar_dato(extra, ('fecha nacimiento', 'fecha de nacimiento'))
        edad = edad_meses_en_periodo(fecha, anio, mes)

    if edad is not None:
        if edad < 6:
            return 'menores_6'
        if edad <= 11:
            return 'seis_11'
        if edad <= 35:
            return 'uno_2'
        if edad <= 71:
            return 'tres_5'
        return None

    if any(token in texto for token in ('6 a 11', '6 11')):
        return 'seis_11'
    if any(token in texto for token in ('1 a 2', '1 2 anos', '12 a 35', '12 35')):
        return 'uno_2'
    if any(token in texto for token in ('3 a 5', '3 5 anos', '36 a 71', '36 71')):
        return 'tres_5'
    if combinado_gestantes:
        # Sin edad ni indicador individual no es posible separar las dos poblaciones.
        # El registro queda como gestante, que es la interpretación histórica de esta etiqueta.
        return 'gestantes'
    if any(token in texto for token in ('menor 6', 'menores 6', '0 a 5')):
        return 'menores_6'
    return None


def consolidar_por_unidad(rows: Iterable[dict[str, Any]], anio: int | None = None, mes: int | None = None) -> dict[str, dict[str, Any]]:
    resumen: dict[str, dict[str, Any]] = {}
    for raw in rows:
        row = dict(raw)
        estado = _texto(row.get('estado'))
        if estado and estado not in {'activo', 'activa'}:
            continue
        unidad = str(row.get('unidad') or row.get('unidad_servicio') or '').strip() or 'SIN UNIDAD'
        item = resumen.setdefault(unidad, {
            **{grupo: 0 for grupo in GRUPOS}, '_docentes': Counter(),
            'sin_clasificar': 0, 'verduras_dobles': 0,
        })
        grupo = clasificar_participante(row, anio, mes)
        if grupo:
            item[grupo] += 1
        else:
            item['sin_clasificar'] += 1
        extra = _datos_json(row.get('datos_json'))
        poblacion = _texto(' '.join(str(value or '') for value in (
            row.get('grupo_etario'), row.get('tipo_beneficiario'),
            _buscar_dato(extra, ('grupo etario', 'tipo beneficiario', 'poblacion', 'lactante')),
        )))
        if grupo == 'gestantes' or 'lactante' in poblacion:
            item['verduras_dobles'] += 1
        docente = str(row.get('docente') or '').strip()
        if docente:
            item['_docentes'][docente] += 1
    return resumen


def docente_mas_frecuente(item: dict[str, Any]) -> str:
    docentes = item.get('_docentes') or Counter()
    return docentes.most_common(1)[0][0] if docentes else ''


def cantidades(item: dict[str, Any]) -> dict[str, int]:
    total = sum(int(item.get(grupo) or 0) for grupo in GRUPOS) + int(item.get('sin_clasificar') or 0)
    usuarios_30 = total - int(item.get('seis_11') or 0)
    huevos_30 = usuarios_30 * 30
    huevos_15 = int(item.get('seis_11') or 0) * 15
    total_huevos = huevos_30 + huevos_15
    cubetas = int(math.ceil(total_huevos / 30)) if total_huevos else 0
    return {
        'total': total,
        'huevos_30': huevos_30,
        'huevos_15': huevos_15,
        'total_huevos': total_huevos,
        'cubetas_30': cubetas,
        'panales_7': int(math.ceil(cubetas / 7)) if cubetas else 0,
        'cubetas_excedentes': ((int(math.ceil(cubetas / 7)) * 7) - cubetas) if cubetas else 0,
        # Cada usuario recibe una unidad; gestantes y lactantes reciben una
        # unidad adicional, para un total de dos.
        'verduras': total + int(item.get('verduras_dobles') or 0),
        'olla_comunitaria': 1 if total else 0,
        'bienestarina': total,
    }
