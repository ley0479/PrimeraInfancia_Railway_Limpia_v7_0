"""Deteccion conservadora de acciones solicitadas a LIAM.

Las acciones mutables nunca se ejecutan desde el modelo: se convierten en una
propuesta cerrada que el usuario debe confirmar en la interfaz.
"""
from __future__ import annotations

import re
import unicodedata

MONTHS = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
    'julio': 7, 'agosto': 8, 'septiembre': 9, 'setiembre': 9, 'octubre': 10,
    'noviembre': 11, 'diciembre': 12,
}
GROUPS = (
    (('0 a 6', '0-6', 'gestante'), '0_6_GESTANTES', '0 a 6 meses y gestantes'),
    (('6 a 11', '6-11'), '6_11_MESES', '6 a 11 meses'),
    (('1 a 2', '1-2'), '1_2_ANOS', '1 a 2 años'),
    (('3 a 5', '3-5'), '3_5_ANOS', '3 a 5 años'),
)


def _plain(value: object) -> str:
    value = unicodedata.normalize('NFKD', str(value or '').casefold())
    return ''.join(char for char in value if not unicodedata.combining(char))


def _clean_unit(value: object) -> str:
    value = re.sub(r'\s+', ' ', str(value or '')).strip(' .,;:-')
    return value[:120]


def propose_action(question: str, *, screen_context: dict | None = None) -> dict | None:
    """Devuelve una propuesta estructurada; nunca ejecuta la accion."""
    q = _plain(question)
    if 'rpp' not in q or not any(word in q for word in ('genera', 'generar', 'descarga', 'descargar')):
        return None
    context = screen_context if isinstance(screen_context, dict) else {}
    month = next((number for name, number in MONTHS.items() if re.search(rf'\b{name}\b', q)), None)
    try:
        year = int(re.search(r'\b(20\d{2}|2100)\b', q).group(1))
    except AttributeError:
        year = None
    group = group_label = None
    for aliases, code, label in GROUPS:
        if any(alias in q for alias in aliases):
            group, group_label = code, label
            break
    unit = _clean_unit(context.get('selected_unit'))
    match = re.search(r'\b(?:de|para la (?:uds|unidad))\s+(.+?)(?=\s+(?:para|del|de)\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre|20\d{2})\b|$)', question, re.I)
    if not unit and match:
        unit = _clean_unit(match.group(1))
    month = month or context.get('selected_month')
    year = year or context.get('selected_year')
    missing = [name for name, value in (('unidad', unit), ('mes', month), ('año', year), ('grupo etario', group)) if not value]
    summary = f"Generar y descargar el RPP de {unit or 'la UDS indicada'}"
    if group_label:
        summary += f", grupo {group_label}"
    if month and year:
        summary += f", periodo {int(month):02d}/{int(year)}"
    return {
        'id': 'download_rpp', 'label': 'Confirmar y generar RPP', 'summary': summary + '.',
        'arguments': {'unit': unit or None, 'month': month, 'year': year, 'group': group},
        'missing': missing, 'confirmation_required': True, 'client_handler': 'download_rpp',
    }
