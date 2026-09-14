"""Catálogo declarativo de capacidades de LIAM, sin autoridad de ejecución."""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Capability:
    name: str
    engine: str
    source: str
    tenant_scoped: bool = True
    read_only: bool = True


CAPABILITIES = {
    item.name: item for item in (
        Capability('get_foundation_data_summary','consulta','Base Maestra'),
        Capability('get_monthly_relation_summary','analiza','Base Maestra'),
        Capability('list_foundation_profiles','consulta','Usuarios'),
        Capability('search_foundation_beneficiaries','consulta','Base Maestra'),
        Capability('universal_search','consulta','Índice institucional'),
        Capability('get_platform_module_summary','consulta','Módulo autorizado'),
        Capability('get_monthly_health_indicators','analiza','Salud y Nutrición'),
        Capability('compare_periods','analiza','Cruce de Bases'),
        Capability('build_custom_report_preview','analiza','Base Maestra'),
        Capability('supervise_deliverables','analiza','Calendario y Entregables'),
        Capability('get_system_health','admin','Diagnóstico interno'),
        Capability('get_foundation_portfolio','admin','Fundaciones y Suscripciones',False),
        Capability('analyze_master_data_quality','analiza','Base Maestra'),
        Capability('get_early_warnings','analiza','Entregables y Base Maestra'),
        Capability('get_incident_center','admin','Centro de Incidencias'),
        Capability('get_notification_center','consulta','Centro de Notificaciones'),
        Capability('get_pending_activities_summary','analiza','Calendario y Entregables'),
        Capability('get_document_processing_status','consulta','Motor Documental'),
        Capability('get_format_generation_status','consulta','Motor de Formatos'),
        Capability('get_structured_error','guia','Catálogo de errores',False),
        Capability('propose_platform_action','ejecuta','Registro de acciones',True,False),
    )
}


def describe(name: str) -> dict:
    item=CAPABILITIES.get(str(name or ''))
    return asdict(item) if item else {}
