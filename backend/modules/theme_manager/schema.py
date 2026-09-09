from __future__ import annotations

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS tm_temas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL UNIQUE,
    nombre TEXT NOT NULL,
    descripcion TEXT,
    categoria TEXT DEFAULT 'institucional',
    activo INTEGER DEFAULT 1,
    es_sistema INTEGER DEFAULT 0,
    css_path TEXT,
    icono TEXT DEFAULT 'palette',
    configuracion_json TEXT NOT NULL,
    preview_json TEXT,
    fecha_creacion TEXT NOT NULL,
    fecha_actualizacion TEXT NOT NULL,
    usuario_creador_id INTEGER,
    fundacion_id INTEGER
);

CREATE INDEX IF NOT EXISTS idx_tm_temas_activo ON tm_temas(activo, categoria);
CREATE INDEX IF NOT EXISTS idx_tm_temas_fundacion ON tm_temas(fundacion_id);

CREATE TABLE IF NOT EXISTS tm_config_corporacion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER NOT NULL DEFAULT 1,
    corporacion_id INTEGER,
    tema_default_codigo TEXT NOT NULL DEFAULT 'ocean-deep',
    permitir_usuario_cambiar INTEGER DEFAULT 1,
    modo_default TEXT DEFAULT 'oscuro',
    contraste_default TEXT DEFAULT 'normal',
    font_scale_default INTEGER DEFAULT 100,
    layout_default TEXT DEFAULT 'normal',
    densidad_default TEXT DEFAULT 'comfortable',
    radio_default INTEGER DEFAULT 16,
    fecha_creacion TEXT NOT NULL,
    fecha_actualizacion TEXT NOT NULL,
    usuario_actualizacion_id INTEGER
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_tm_config_fundacion_default
ON tm_config_corporacion(fundacion_id, IFNULL(corporacion_id, 0));

CREATE TABLE IF NOT EXISTS tm_usuario_preferencias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    fundacion_id INTEGER NOT NULL DEFAULT 1,
    tema_codigo TEXT NOT NULL DEFAULT 'ocean-deep',
    modo TEXT DEFAULT 'oscuro',
    contraste TEXT DEFAULT 'normal',
    font_scale INTEGER DEFAULT 100,
    layout TEXT DEFAULT 'normal',
    densidad TEXT DEFAULT 'comfortable',
    radio INTEGER DEFAULT 16,
    custom_json TEXT,
    fecha_creacion TEXT NOT NULL,
    fecha_actualizacion TEXT NOT NULL,
    UNIQUE(usuario_id, fundacion_id)
);

CREATE TABLE IF NOT EXISTS tm_auditoria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER DEFAULT 1,
    corporacion_id INTEGER,
    usuario_id INTEGER,
    username TEXT,
    accion TEXT NOT NULL,
    entidad TEXT,
    entidad_id TEXT,
    datos_anteriores TEXT,
    datos_nuevos TEXT,
    ip TEXT,
    fecha TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tm_auditoria_fecha ON tm_auditoria(fundacion_id, fecha);
"""

DEFAULT_THEME_CONFIG = {
    'version': 1,
    'base': 'dashboard-actual',
    'colors': {
        'primary': '#4f46e5',
        'primaryHover': '#4338ca',
        'accent': '#06b6d4',
        'background': '#020617',
        'surface': '#0f172a',
        'surfaceSoft': '#1e293b',
        'border': '#334155',
        'text': '#f8fafc',
        'muted': '#94a3b8',
        'success': '#10b981',
        'warning': '#f59e0b',
        'danger': '#ef4444',
    },
    'modes': {
        'oscuro': {},
        'claro': {
            'background': '#f8fafc',
            'surface': '#ffffff',
            'surfaceSoft': '#e2e8f0',
            'border': '#cbd5e1',
            'text': '#0f172a',
            'muted': '#475569',
        }
    },
    'typography': {
        'fontFamily': 'Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
        'fontScale': 100,
    },
    'layout': {
        'density': 'comfortable',
        'radius': 16,
        'sidebar': 'normal',
        'cards': 'rounded',
    },
    'icons': {
        'style': 'lucide',
        'accent': '#06b6d4',
    },
    'accessibility': {
        'contrast': 'normal',
        'reduceMotion': False,
    }
}

SYSTEM_THEMES = [
    {
        'codigo': 'base-actual',
        'nombre': 'Dashboard actual institucional',
        'descripcion': 'Tema base que conserva la apariencia actual de la plataforma. Es el punto de partida seguro.',
        'categoria': 'sistema',
        'activo': 1,
        'es_sistema': 1,
        'css_path': '',
        'icono': 'layout-dashboard',
        'configuracion': DEFAULT_THEME_CONFIG,
    },
    {
        'codigo': 'claro-institucional',
        'nombre': 'Claro institucional',
        'descripcion': 'Variante clara para oficinas con alta iluminación, manteniendo colores institucionales.',
        'categoria': 'sistema',
        'activo': 1,
        'es_sistema': 1,
        'css_path': 'css/themes/theme-claro-institucional.css',
        'icono': 'sun',
        'configuracion': {
            **DEFAULT_THEME_CONFIG,
            'colors': {
                **DEFAULT_THEME_CONFIG['colors'],
                'primary': '#2563eb',
                'primaryHover': '#1d4ed8',
                'accent': '#0891b2',
                'background': '#f8fafc',
                'surface': '#ffffff',
                'surfaceSoft': '#e2e8f0',
                'border': '#cbd5e1',
                'text': '#0f172a',
                'muted': '#475569',
            },
            'modes': {
                'oscuro': DEFAULT_THEME_CONFIG['colors'],
                'claro': {},
            },
        },
    },
    {
        'codigo': 'verde-primera-infancia',
        'nombre': 'Verde primera infancia',
        'descripcion': 'Tema institucional con énfasis en salud, nutrición y operación territorial.',
        'categoria': 'sistema',
        'activo': 1,
        'es_sistema': 1,
        'css_path': '',
        'icono': 'sprout',
        'configuracion': {
            **DEFAULT_THEME_CONFIG,
            'colors': {
                **DEFAULT_THEME_CONFIG['colors'],
                'primary': '#059669',
                'primaryHover': '#047857',
                'accent': '#84cc16',
                'success': '#22c55e',
                'warning': '#f97316',
            },
        },
    },
    {
        'codigo': 'alto-contraste',
        'nombre': 'Alto contraste',
        'descripcion': 'Tema de accesibilidad para mejorar lectura, contraste y seguimiento operativo.',
        'categoria': 'accesibilidad',
        'activo': 1,
        'es_sistema': 1,
        'css_path': 'css/themes/theme-alto-contraste.css',
        'icono': 'contrast',
        'configuracion': {
            **DEFAULT_THEME_CONFIG,
            'colors': {
                **DEFAULT_THEME_CONFIG['colors'],
                'primary': '#facc15',
                'primaryHover': '#eab308',
                'accent': '#22d3ee',
                'background': '#000000',
                'surface': '#0a0a0a',
                'surfaceSoft': '#171717',
                'border': '#facc15',
                'text': '#ffffff',
                'muted': '#e5e7eb',
                'danger': '#fb7185',
            },
            'accessibility': {
                'contrast': 'alto',
                'reduceMotion': False,
            },
        },
    },
]

# El registro profesional sustituye el catálogo heredado sin duplicar módulos.
from .theme_registry import build_system_themes
SYSTEM_THEMES = build_system_themes(DEFAULT_THEME_CONFIG)
