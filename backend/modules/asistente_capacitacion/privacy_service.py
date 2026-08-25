"""Redacción mínima de datos sensibles antes de auditoría o respuesta."""
from __future__ import annotations
import re

PATTERNS = (
    (re.compile(r'\b\d{7,12}\b'), '[IDENTIFICADOR]'),
    (re.compile(r'\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b'), '[CORREO]'),
    (re.compile(r'(?i)\b(?:token|password|contraseña|secret|api[_ -]?key)\s*[:=]\s*\S+'), '[SECRETO REDACTADO]'),
)

def redact(text: str) -> str:
    value = str(text or '')
    for pattern, replacement in PATTERNS:
        value = pattern.sub(replacement, value)
    return value
