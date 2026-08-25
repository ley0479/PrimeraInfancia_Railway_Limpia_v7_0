"""Registro cerrado y ordenado para el recorrido institucional de ELIAN."""
from __future__ import annotations

from .guides import GUIDES


_MODULES = (
    (10, 'dashboard', 'Centro de Control', 'Inicio, indicadores, alertas y accesos principales.'),
    (20, 'base-maestra', 'Base Maestra y Cuéntame', 'Carga, valida y consolida las fuentes maestras autorizadas.'),
    (30, 'talento', 'Talento Humano', 'Relaciona personal, cargos, coordinadores, equipos y unidades.'),
    (40, 'salud-nutricion', 'Salud y Nutrición', 'Organiza seguimientos, alertas y reportes nutricionales autorizados.'),
    (50, 'calendario-inteligente', 'Calendario', 'Presenta actividades, entregables, evidencias y vencimientos.'),
    (60, 'motor-documental', 'Motor Documental', 'Lee, valida y propone mapeos documentales revisables.'),
    (70, 'planeacion-pedagogica', 'Planeación Pedagógica', 'Gestiona planeaciones, ejecución y evidencias pedagógicas.'),
    (80, 'gestion-pedagogica', 'Gestión Pedagógica', 'Consolida entregables, revisión y seguimiento pedagógico.'),
    (90, 'componente-psicosocial', 'Gestión Psicosocial', 'Organiza expedientes y seguimientos con validación profesional.'),
    (100, 'familias-redes', 'Familias y Redes', 'Gestiona acompañamientos, compromisos y redes de apoyo.'),
    (110, 'formatos', 'Formatos', 'Genera formatos autorizados con información confirmada.'),
    (120, 'reportes-gerenciales', 'Reportes', 'Consulta indicadores, cobertura, cumplimiento y exportaciones.'),
    (130, 'relacion-mes', 'Relación del Mes', 'Consolida usuarios, rangos y entregas mensuales.'),
    (140, 'expediente-operativo-uca', 'Expediente Operativo UCA', 'Consulta el estado integral de cada unidad sin duplicar fuentes.'),
    (150, 'administracion', 'Administración', 'Gestiona fundaciones, usuarios, roles y configuraciones autorizadas.'),
    (160, 'facturacion', 'Créditos y Licencias', 'Consulta plan, consumo, vigencia y alertas de la suscripción.'),
    (170, 'integrity-stability', 'Auditoría e Integridad', 'Consulta trazabilidad, calidad y controles de integridad.'),
    (180, 'manual-operativo', 'Ayuda y Soporte', 'Accede a manuales, recorridos y orientación institucional.'),
)


def _detail(module_id: str, title: str, purpose: str) -> dict:
    guide = GUIDES.get(module_id, {})
    inputs = list(guide.get('necesitas') or ['Sesión, fundación y permisos vigentes.'])
    validations = list(guide.get('validaciones') or [
        'Sesión, rol y fundación autorizados.',
        'Periodo, unidad, archivo o registro requerido por la pantalla.',
        'Confirmación del resultado antes de continuar.',
    ])
    return {
        'module_id': module_id,
        'route': module_id,
        'title': title,
        'purpose': guide.get('proposito') or guide.get('resumen') or purpose,
        'authorized_users': 'Se determina con los permisos reales de la sesión.',
        'inputs': inputs,
        'data_source': guide.get('origen_datos') or 'Servicios y fuentes institucionales autorizadas para la fundación activa.',
        'validations': validations,
        'outputs': guide.get('resultado') or 'Resultado confirmado por el sistema con trazabilidad.',
        'downstream_use': guide.get('uso_resultado') or 'Paneles, seguimientos, formatos o reportes autorizados relacionados.',
        'frequent_errors': list(guide.get('errores_frecuentes') or []),
        'next_step': (guide.get('pasos') or ['Revisar el resultado confirmado.'])[-1],
        'controls_registered': module_id in {
            'dashboard', 'base-maestra', 'talento', 'salud-nutricion',
            'calendario-inteligente', 'motor-documental', 'planeacion-pedagogica',
            'gestion-pedagogica', 'componente-psicosocial', 'familias-redes',
            'formatos', 'expediente-operativo-uca', 'administracion',
        },
    }


ELIAN_MODULE_REGISTRY = tuple(
    {'order': order, **_detail(module_id, title, purpose)}
    for order, module_id, title, purpose in _MODULES
)


def authorized_modules(allowed_module_ids) -> list[dict]:
    allowed = set(allowed_module_ids or [])
    return [dict(item) for item in ELIAN_MODULE_REGISTRY if item['module_id'] in allowed]

