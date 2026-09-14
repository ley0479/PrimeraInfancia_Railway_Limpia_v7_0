"""Redacción mínima de datos sensibles antes de auditoría o respuesta."""
from __future__ import annotations
import re

PATTERNS = (
    (re.compile(r'\b\d{7,12}\b'), '[IDENTIFICADOR]'),
    (re.compile(r'\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b'), '[CORREO]'),
    (re.compile(r'(?i)\b(?:token|password|contraseña|secret|api[_ -]?key)\s*[:=]\s*\S+'), '[SECRETO REDACTADO]'),
)

CREDENTIAL_PATTERN=re.compile(r'(?i)\b(?:token|password|contraseña|secret|api[_ -]?key|authorization)\s*[:=]\s*\S+')

def redact(text: str) -> str:
    value = str(text or '')
    for pattern, replacement in PATTERNS:
        value = pattern.sub(replacement, value)
    return value


def redact_credentials(text: str) -> str:
    """Protege credenciales conservando referencias operativas que el usuario decidió guardar."""
    return CREDENTIAL_PATTERN.sub('[SECRETO REDACTADO]',str(text or ''))


def redact_data(value, depth: int = 0):
    """Redacta estructuras destinadas a persistencia sin ejecutar ni interpretar su contenido."""
    if depth>6:return '[CONTENIDO OMITIDO]'
    if isinstance(value,dict):
        result={}
        for key,item in list(value.items())[:100]:
            safe_key=str(key)[:80]
            if re.search(r'(?i)(password|contraseña|secret|token|api[_ -]?key|authorization)',safe_key):result[safe_key]='[SECRETO REDACTADO]'
            else:result[safe_key]=redact_data(item,depth+1)
        return result
    if isinstance(value,(list,tuple)):return [redact_data(item,depth+1) for item in list(value)[:200]]
    if isinstance(value,str):return redact(value)[:2000]
    if value is None or isinstance(value,(bool,int,float)):return value
    return redact(str(value))[:2000]
