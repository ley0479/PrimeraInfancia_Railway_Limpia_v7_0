"""Ficha institucional confirmable; nunca inventa autoría ni fechas."""
from __future__ import annotations
import os

def get_platform_profile() -> dict:
    designer = os.getenv('LIA_PLATFORM_DESIGNER', '').strip()
    created = os.getenv('LIA_PLATFORM_CREATED_DATE', '').strip()
    description = os.getenv('LIA_PLATFORM_DESCRIPTION', '').strip()
    return {
        'designer': designer or None,
        'created_date': created or None,
        'description': description or 'Plataforma de gestión integral para la operación autorizada de Primera Infancia.',
        'identity_confirmed': bool(designer and created),
    }
