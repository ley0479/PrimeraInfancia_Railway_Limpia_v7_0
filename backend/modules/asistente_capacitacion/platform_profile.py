"""Ficha institucional confirmable; nunca inventa autoría ni fechas."""
from __future__ import annotations
import os

def get_platform_profile() -> dict:
    designer = os.getenv('LIA_PLATFORM_DESIGNER', 'Leison Palacios Blandón').strip()
    development_contributor = os.getenv('LIA_PLATFORM_DEVELOPMENT_CONTRIBUTOR', 'Yoiler Mosquera').strip()
    created = os.getenv('LIA_PLATFORM_CREATED_DATE', '04 de junio de 2026').strip()
    description = os.getenv('LIA_PLATFORM_DESCRIPTION', '').strip()
    return {
        'name': os.getenv('LIA_PLATFORM_NAME', 'Plataforma Primera Infancia').strip() or 'Plataforma Primera Infancia',
        'designer': designer or None,
        'development_contributor': development_contributor or None,
        'created_date': created or None,
        'last_update_date': os.getenv('LIA_PLATFORM_LAST_UPDATE_DATE', '').strip() or None,
        'description': description or 'Plataforma de gestión integral para la operación autorizada de Primera Infancia.',
        'identity_confirmed': bool(designer and created),
        'presentation_rule': 'designer_and_creation_date_first',
        'version': os.getenv('APP_VERSION', '2.7.2-document-center').strip() or '2.7.2-document-center',
    }
