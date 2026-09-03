from __future__ import annotations

import copy
import json
import re
from modules.dbapi_compat import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .schema import DEFAULT_THEME_CONFIG, SCHEMA_SQL, SYSTEM_THEMES

HEX_RE = re.compile(r'^#[0-9A-Fa-f]{6}$')
CODE_RE = re.compile(r'^[a-z0-9][a-z0-9_-]{2,48}$')
ALLOWED_MODES = {'oscuro', 'claro', 'auto'}
ALLOWED_CONTRAST = {'normal', 'alto'}
ALLOWED_LAYOUTS = {'normal', 'compacto', 'amplio'}
ALLOWED_DENSITY = {'compact', 'comfortable', 'spacious'}


def now_iso() -> str:
    return datetime.now().isoformat(timespec='seconds')


def connect(database_path: str) -> sqlite3.Connection:
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    return conn


def safe_json_loads(value: Any, default: Any = None) -> Any:
    if value is None:
        return copy.deepcopy(default)
    if isinstance(value, (dict, list)):
        return copy.deepcopy(value)
    try:
        return json.loads(str(value or ''))
    except Exception:
        return copy.deepcopy(default)


def safe_json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def sanitize_hex(value: Any, fallback: str) -> str:
    text = str(value or '').strip()
    return text if HEX_RE.match(text) else fallback


def sanitize_code(value: Any, fallback: str = 'tema-personalizado') -> str:
    text = str(value or '').strip().lower()
    text = re.sub(r'[^a-z0-9_-]+', '-', text).strip('-_')
    if not text:
        text = fallback
    if not CODE_RE.match(text):
        text = re.sub(r'[^a-z0-9_-]', '', text)[:40] or fallback
    return text


def normalize_int(value: Any, fallback: int, min_value: int, max_value: int) -> int:
    try:
        number = int(float(value))
    except Exception:
        number = fallback
    return max(min_value, min(max_value, number))


def sanitize_theme_config(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload or {}
    config = deep_merge(DEFAULT_THEME_CONFIG, payload)
    defaults = DEFAULT_THEME_CONFIG

    colors = config.setdefault('colors', {})
    for key, fallback_key in {
        'primary': 'primary', 'primaryHover': 'primaryHover', 'accent': 'accent',
        'background': 'background', 'surface': 'surface', 'surfaceSoft': 'surfaceSoft',
        'border': 'border', 'text': 'text', 'muted': 'muted', 'success': 'success',
        'warning': 'warning', 'danger': 'danger'
    }.items():
        colors[key] = sanitize_hex(colors.get(key), defaults['colors'][fallback_key])

    modes = config.setdefault('modes', {})
    for mode in ('oscuro', 'claro'):
        mode_payload = modes.get(mode) or {}
        cleaned: dict[str, str] = {}
        for key, value in mode_payload.items():
            if key in colors:
                cleaned[key] = sanitize_hex(value, colors[key])
        modes[mode] = cleaned

    typography = config.setdefault('typography', {})
    typography['fontFamily'] = str(typography.get('fontFamily') or defaults['typography']['fontFamily']).strip()[:180]
    typography['fontScale'] = normalize_int(typography.get('fontScale'), defaults['typography']['fontScale'], 85, 125)

    layout = config.setdefault('layout', {})
    layout['density'] = str(layout.get('density') or defaults['layout']['density'])
    if layout['density'] not in ALLOWED_DENSITY:
        layout['density'] = defaults['layout']['density']
    layout['radius'] = normalize_int(layout.get('radius'), defaults['layout']['radius'], 4, 32)
    layout['sidebar'] = str(layout.get('sidebar') or defaults['layout']['sidebar'])
    if layout['sidebar'] not in {'normal', 'compact'}:
        layout['sidebar'] = defaults['layout']['sidebar']
    layout['cards'] = str(layout.get('cards') or defaults['layout']['cards'])[:40]

    icons = config.setdefault('icons', {})
    icons['style'] = str(icons.get('style') or 'lucide')[:40]
    icons['accent'] = sanitize_hex(icons.get('accent'), colors['accent'])

    accessibility = config.setdefault('accessibility', {})
    accessibility['contrast'] = str(accessibility.get('contrast') or 'normal')
    if accessibility['contrast'] not in ALLOWED_CONTRAST:
        accessibility['contrast'] = 'normal'
    accessibility['reduceMotion'] = bool(accessibility.get('reduceMotion'))
    return config


def seed_system_themes(conn: sqlite3.Connection) -> None:
    now = now_iso()
    for theme in SYSTEM_THEMES:
        config = sanitize_theme_config(theme['configuracion'])
        row = conn.execute('SELECT id, es_sistema FROM tm_temas WHERE codigo=?', (theme['codigo'],)).fetchone()
        if row:
            # Actualiza únicamente metadatos seguros de temas de sistema; no borra temas personalizados.
            conn.execute(
                """
                UPDATE tm_temas
                SET nombre=?, descripcion=?, categoria=?, es_sistema=1, css_path=?, icono=?,
                    configuracion_json=?, fecha_actualizacion=?
                WHERE codigo=? AND es_sistema=1
                """,
                (
                    theme['nombre'], theme['descripcion'], theme['categoria'], theme.get('css_path') or '',
                    theme.get('icono') or 'palette', safe_json_dumps(config), now, theme['codigo']
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO tm_temas
                (codigo, nombre, descripcion, categoria, activo, es_sistema, css_path, icono,
                 configuracion_json, preview_json, fecha_creacion, fecha_actualizacion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    theme['codigo'], theme['nombre'], theme['descripcion'], theme['categoria'],
                    int(theme.get('activo', 1)), int(theme.get('es_sistema', 1)), theme.get('css_path') or '',
                    theme.get('icono') or 'palette', safe_json_dumps(config), safe_json_dumps({}), now, now,
                ),
            )


def init_schema(database_path: str) -> None:
    conn = connect(database_path)
    conn.executescript(SCHEMA_SQL)
    seed_system_themes(conn)
    legacy_codes = ('base-actual', 'claro-institucional', 'verde-primera-infancia')
    conn.execute(
        "UPDATE tm_temas SET activo=0, categoria='legacy', fecha_actualizacion=? WHERE es_sistema=1 AND codigo IN (?, ?, ?)",
        (now_iso(), *legacy_codes),
    )
    conn.execute(
        "UPDATE tm_config_corporacion SET tema_default_codigo='ocean-deep' WHERE tema_default_codigo IN (?, ?, ?)",
        legacy_codes,
    )
    conn.execute(
        "UPDATE tm_usuario_preferencias SET tema_codigo='ocean-deep' WHERE tema_codigo IN (?, ?, ?)",
        legacy_codes,
    )
    now = now_iso()
    conn.execute(
        """
        INSERT INTO tm_config_corporacion
        (fundacion_id, corporacion_id, tema_default_codigo, permitir_usuario_cambiar,
         modo_default, contraste_default, font_scale_default, layout_default, densidad_default,
         radio_default, fecha_creacion, fecha_actualizacion)
        VALUES (1, NULL, 'ocean-deep', 1, 'oscuro', 'normal', 100, 'normal', 'comfortable', 16, ?, ?)
        ON CONFLICT DO NOTHING
        """,
        (now, now),
    )
    conn.commit()
    conn.close()


def audit(database_path: str, accion: str, user: dict[str, Any] | None = None, entidad: str | None = None,
          entidad_id: Any = None, antes: Any = None, despues: Any = None, ip: str | None = None,
          corporacion_id: int | None = None) -> None:
    try:
        user = user or {}
        conn = connect(database_path)
        conn.execute(
            """
            INSERT INTO tm_auditoria
            (fundacion_id, corporacion_id, usuario_id, username, accion, entidad, entidad_id,
             datos_anteriores, datos_nuevos, ip, fecha)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user.get('fundacion_id') or 1, corporacion_id, user.get('id'), user.get('username'), accion,
                entidad, str(entidad_id) if entidad_id is not None else None,
                safe_json_dumps(antes) if antes is not None else None,
                safe_json_dumps(despues) if despues is not None else None,
                ip, now_iso(),
            ),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def row_to_theme(row: sqlite3.Row | dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    data = dict(row)
    data['activo'] = bool(data.get('activo'))
    data['es_sistema'] = bool(data.get('es_sistema'))
    data['configuracion'] = sanitize_theme_config(safe_json_loads(data.pop('configuracion_json', '{}'), {}))
    data['preview'] = safe_json_loads(data.pop('preview_json', '{}'), {}) or {}
    return data


def get_theme(database_path: str, codigo: str) -> dict[str, Any] | None:
    conn = connect(database_path)
    row = conn.execute('SELECT * FROM tm_temas WHERE codigo=?', (codigo,)).fetchone()
    conn.close()
    return row_to_theme(row)


def list_themes(database_path: str, include_inactive: bool = False, fundacion_id: int | None = None) -> list[dict[str, Any]]:
    where = ["categoria <> 'legacy'"]
    if not include_inactive:
        where.append('activo=1')
    params: list[Any] = []
    # Los temas de sistema son globales; los personalizados pueden quedar asociados a una fundación.
    if fundacion_id:
        where.append('(fundacion_id IS NULL OR fundacion_id=?)')
        params.append(fundacion_id)
    sql = 'SELECT * FROM tm_temas'
    if where:
        sql += ' WHERE ' + ' AND '.join(where)
    sql += ' ORDER BY es_sistema DESC, nombre COLLATE NOCASE'
    conn = connect(database_path)
    rows = conn.execute(sql, tuple(params)).fetchall()
    conn.close()
    return [row_to_theme(row) for row in rows]


def get_corporation_config(database_path: str, fundacion_id: int, corporacion_id: int | None = None) -> dict[str, Any]:
    conn = connect(database_path)
    row = conn.execute(
        """
        SELECT * FROM tm_config_corporacion
        WHERE fundacion_id=? AND IFNULL(corporacion_id, 0)=IFNULL(?, 0)
        """,
        (fundacion_id or 1, corporacion_id),
    ).fetchone()
    if not row and corporacion_id is not None:
        row = conn.execute(
            "SELECT * FROM tm_config_corporacion WHERE fundacion_id=? AND corporacion_id IS NULL",
            (fundacion_id or 1,),
        ).fetchone()
    if not row:
        now = now_iso()
        conn.execute(
            """
            INSERT INTO tm_config_corporacion
            (fundacion_id, corporacion_id, tema_default_codigo, permitir_usuario_cambiar, modo_default,
             contraste_default, font_scale_default, layout_default, densidad_default, radio_default,
             fecha_creacion, fecha_actualizacion)
            VALUES (?, ?, 'ocean-deep', 1, 'oscuro', 'normal', 100, 'normal', 'comfortable', 16, ?, ?)
            """,
            (fundacion_id or 1, corporacion_id, now, now),
        )
        conn.commit()
        row = conn.execute(
            """
            SELECT * FROM tm_config_corporacion
            WHERE fundacion_id=? AND IFNULL(corporacion_id, 0)=IFNULL(?, 0)
            """,
            (fundacion_id or 1, corporacion_id),
        ).fetchone()
    conn.close()
    return dict(row)


def sanitize_preference(payload: dict[str, Any] | None, fallback: dict[str, Any]) -> dict[str, Any]:
    payload = payload or {}
    pref = dict(fallback or {})
    codigo = sanitize_code(payload.get('tema_codigo') or payload.get('codigo') or pref.get('tema_codigo') or 'ocean-deep', 'ocean-deep')
    pref['tema_codigo'] = codigo
    mode = str(payload.get('modo') or pref.get('modo') or pref.get('modo_default') or 'oscuro')
    pref['modo'] = mode if mode in ALLOWED_MODES else 'oscuro'
    contrast = str(payload.get('contraste') or pref.get('contraste') or pref.get('contraste_default') or 'normal')
    pref['contraste'] = contrast if contrast in ALLOWED_CONTRAST else 'normal'
    pref['font_scale'] = normalize_int(payload.get('font_scale') or payload.get('fontScale') or pref.get('font_scale') or pref.get('font_scale_default'), 100, 85, 125)
    layout = str(payload.get('layout') or pref.get('layout') or pref.get('layout_default') or 'normal')
    pref['layout'] = layout if layout in ALLOWED_LAYOUTS else 'normal'
    density = str(payload.get('densidad') or payload.get('density') or pref.get('densidad') or pref.get('densidad_default') or 'comfortable')
    pref['densidad'] = density if density in ALLOWED_DENSITY else 'comfortable'
    pref['radio'] = normalize_int(payload.get('radio') or payload.get('radius') or pref.get('radio') or pref.get('radio_default'), 16, 4, 32)
    pref['custom_json'] = payload.get('custom_json') or payload.get('custom') or pref.get('custom_json')
    return pref


def get_user_preference(database_path: str, usuario_id: int | None, fundacion_id: int) -> dict[str, Any] | None:
    if not usuario_id:
        return None
    conn = connect(database_path)
    row = conn.execute(
        'SELECT * FROM tm_usuario_preferencias WHERE usuario_id=? AND fundacion_id=?',
        (usuario_id, fundacion_id or 1),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def compute_variables(theme: dict[str, Any], pref: dict[str, Any]) -> dict[str, str]:
    config = sanitize_theme_config(theme.get('configuracion') or {})
    colors = dict(config.get('colors') or {})
    mode = pref.get('modo') or 'oscuro'
    if mode == 'auto':
        mode = 'oscuro'
    mode_override = (config.get('modes') or {}).get(mode) or {}
    colors.update({k: v for k, v in mode_override.items() if HEX_RE.match(str(v))})
    if pref.get('contraste') == 'alto':
        colors['border'] = colors.get('accent') or colors.get('border')
        colors['muted'] = colors.get('text') or colors.get('muted')
    return {
        '--pi-bg': colors.get('background', '#020617'),
        '--pi-surface': colors.get('surface', '#0f172a'),
        '--pi-surface-soft': colors.get('surfaceSoft', '#1e293b'),
        '--pi-border': colors.get('border', '#334155'),
        '--pi-text': colors.get('text', '#f8fafc'),
        '--pi-muted': colors.get('muted', '#94a3b8'),
        '--pi-primary': colors.get('primary', '#4f46e5'),
        '--pi-primary-hover': colors.get('primaryHover', '#4338ca'),
        '--pi-accent': colors.get('accent', '#06b6d4'),
        '--pi-success': colors.get('success', '#10b981'),
        '--pi-warning': colors.get('warning', '#f59e0b'),
        '--pi-danger': colors.get('danger', '#ef4444'),
        '--pi-radius': f"{normalize_int(pref.get('radio'), 16, 4, 32)}px",
        '--pi-font-scale': f"{normalize_int(pref.get('font_scale'), 100, 85, 125)}%",
        '--pi-font-family': (config.get('typography') or {}).get('fontFamily') or DEFAULT_THEME_CONFIG['typography']['fontFamily'],
    }


def current_context(database_path: str, user: dict[str, Any] | None = None) -> dict[str, Any]:
    user = user or {}
    fundacion_id = int(user.get('fundacion_id') or 1)
    usuario_id = user.get('id')
    rol = user.get('rol') or 'DOCENTE'
    corp_config = get_corporation_config(database_path, fundacion_id, None)
    can_admin = rol in {'SUPERADMIN', 'GERENTE'}
    can_change = bool(corp_config.get('permitir_usuario_cambiar')) or can_admin
    user_pref = get_user_preference(database_path, usuario_id, fundacion_id) if can_change else None
    fallback = {
        'tema_codigo': corp_config.get('tema_default_codigo') or 'ocean-deep',
        'modo': corp_config.get('modo_default') or 'oscuro',
        'contraste': corp_config.get('contraste_default') or 'normal',
        'font_scale': corp_config.get('font_scale_default') or 100,
        'layout': corp_config.get('layout_default') or 'normal',
        'densidad': corp_config.get('densidad_default') or 'comfortable',
        'radio': corp_config.get('radio_default') or 16,
        'custom_json': None,
    }
    pref = sanitize_preference(user_pref or {}, fallback) if user_pref else sanitize_preference({}, fallback)
    theme = get_theme(database_path, pref['tema_codigo']) or get_theme(database_path, corp_config.get('tema_default_codigo') or 'ocean-deep') or get_theme(database_path, 'ocean-deep')
    if not theme or not theme.get('activo'):
        theme = get_theme(database_path, 'ocean-deep')
        pref['tema_codigo'] = 'ocean-deep'
    variables = compute_variables(theme, pref)
    return {
        'tema': theme,
        'preferencia': pref,
        'configuracion_corporacion': dict(corp_config),
        'variables': variables,
        'temas': list_themes(database_path, include_inactive=can_admin, fundacion_id=fundacion_id),
        'permisos': {
            'puede_administrar': can_admin,
            'puede_cambiar_tema': can_change,
            'rol': rol,
        },
        'fundacion_id': fundacion_id,
    }


def save_user_preference(database_path: str, user: dict[str, Any], payload: dict[str, Any], ip: str | None = None) -> dict[str, Any]:
    fundacion_id = int(user.get('fundacion_id') or 1)
    usuario_id = int(user.get('id') or 0)
    if not usuario_id:
        raise ValueError('Usuario no identificado.')
    corp_config = get_corporation_config(database_path, fundacion_id, None)
    if not bool(corp_config.get('permitir_usuario_cambiar')) and user.get('rol') not in {'SUPERADMIN', 'GERENTE'}:
        raise PermissionError('El cambio de diseño por usuario no está habilitado para esta corporación.')
    fallback = {
        'tema_codigo': corp_config.get('tema_default_codigo') or 'ocean-deep',
        'modo': corp_config.get('modo_default') or 'oscuro',
        'contraste': corp_config.get('contraste_default') or 'normal',
        'font_scale': corp_config.get('font_scale_default') or 100,
        'layout': corp_config.get('layout_default') or 'normal',
        'densidad': corp_config.get('densidad_default') or 'comfortable',
        'radio': corp_config.get('radio_default') or 16,
    }
    pref = sanitize_preference(payload, fallback)
    theme = get_theme(database_path, pref['tema_codigo'])
    if not theme or not theme.get('activo'):
        raise ValueError('El tema seleccionado no existe o está inactivo.')
    now = now_iso()
    conn = connect(database_path)
    old = conn.execute('SELECT * FROM tm_usuario_preferencias WHERE usuario_id=? AND fundacion_id=?', (usuario_id, fundacion_id)).fetchone()
    conn.execute(
        """
        INSERT INTO tm_usuario_preferencias
        (usuario_id, fundacion_id, tema_codigo, modo, contraste, font_scale, layout, densidad, radio,
         custom_json, fecha_creacion, fecha_actualizacion)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(usuario_id, fundacion_id) DO UPDATE SET
            tema_codigo=excluded.tema_codigo,
            modo=excluded.modo,
            contraste=excluded.contraste,
            font_scale=excluded.font_scale,
            layout=excluded.layout,
            densidad=excluded.densidad,
            radio=excluded.radio,
            custom_json=excluded.custom_json,
            fecha_actualizacion=excluded.fecha_actualizacion
        """,
        (
            usuario_id, fundacion_id, pref['tema_codigo'], pref['modo'], pref['contraste'], pref['font_scale'],
            pref['layout'], pref['densidad'], pref['radio'],
            safe_json_dumps(pref.get('custom_json')) if pref.get('custom_json') is not None else None,
            now, now,
        ),
    )
    conn.commit()
    conn.close()
    audit(database_path, 'GUARDAR_PREFERENCIA_USUARIO', user, 'tm_usuario_preferencias', usuario_id,
          antes=dict(old) if old else None, despues=pref, ip=ip)
    return current_context(database_path, user)


def save_corporation_config(database_path: str, user: dict[str, Any], payload: dict[str, Any], ip: str | None = None) -> dict[str, Any]:
    fundacion_id = int(payload.get('fundacion_id') or user.get('fundacion_id') or 1)
    if user.get('rol') != 'SUPERADMIN':
        fundacion_id = int(user.get('fundacion_id') or 1)
    corporacion_id = payload.get('corporacion_id')
    if corporacion_id in {'', 'null', 'None'}:
        corporacion_id = None
    theme_code = sanitize_code(payload.get('tema_default_codigo') or payload.get('tema_codigo') or 'ocean-deep', 'ocean-deep')
    theme = get_theme(database_path, theme_code)
    if not theme or not theme.get('activo'):
        raise ValueError('El tema predeterminado seleccionado no existe o está inactivo.')
    modo = str(payload.get('modo_default') or payload.get('modo') or 'oscuro')
    if modo not in ALLOWED_MODES:
        modo = 'oscuro'
    contraste = str(payload.get('contraste_default') or payload.get('contraste') or 'normal')
    if contraste not in ALLOWED_CONTRAST:
        contraste = 'normal'
    font_scale = normalize_int(payload.get('font_scale_default') or payload.get('font_scale'), 100, 85, 125)
    layout = str(payload.get('layout_default') or payload.get('layout') or 'normal')
    if layout not in ALLOWED_LAYOUTS:
        layout = 'normal'
    densidad = str(payload.get('densidad_default') or payload.get('densidad') or 'comfortable')
    if densidad not in ALLOWED_DENSITY:
        densidad = 'comfortable'
    radio = normalize_int(payload.get('radio_default') or payload.get('radio'), 16, 4, 32)
    permitir = 1 if payload.get('permitir_usuario_cambiar') in {True, 1, '1', 'true', 'TRUE', 'on', 'si', 'sí'} else 0
    now = now_iso()
    conn = connect(database_path)
    old = conn.execute(
        'SELECT * FROM tm_config_corporacion WHERE fundacion_id=? AND IFNULL(corporacion_id,0)=IFNULL(?,0)',
        (fundacion_id, corporacion_id),
    ).fetchone()
    if old:
        conn.execute(
            """
            UPDATE tm_config_corporacion
            SET tema_default_codigo=?, permitir_usuario_cambiar=?, modo_default=?, contraste_default=?,
                font_scale_default=?, layout_default=?, densidad_default=?, radio_default=?,
                fecha_actualizacion=?, usuario_actualizacion_id=?
            WHERE id=?
            """,
            (
                theme_code, permitir, modo, contraste, font_scale, layout, densidad, radio,
                now, user.get('id'), old['id'],
            ),
        )
    else:
        conn.execute(
            """
            INSERT INTO tm_config_corporacion
            (fundacion_id, corporacion_id, tema_default_codigo, permitir_usuario_cambiar, modo_default,
             contraste_default, font_scale_default, layout_default, densidad_default, radio_default,
             fecha_creacion, fecha_actualizacion, usuario_actualizacion_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fundacion_id, corporacion_id, theme_code, permitir, modo, contraste, font_scale, layout,
                densidad, radio, now, now, user.get('id'),
            ),
        )
    conn.commit()
    conn.close()
    nuevo = get_corporation_config(database_path, fundacion_id, corporacion_id)
    audit(database_path, 'GUARDAR_CONFIG_CORPORACION', user, 'tm_config_corporacion', fundacion_id,
          antes=dict(old) if old else None, despues=nuevo, ip=ip, corporacion_id=corporacion_id)
    return current_context(database_path, user)


def create_theme(database_path: str, user: dict[str, Any], payload: dict[str, Any], ip: str | None = None) -> dict[str, Any]:
    name = str(payload.get('nombre') or payload.get('name') or '').strip()
    if not name:
        raise ValueError('El nombre del tema es obligatorio.')
    code = sanitize_code(payload.get('codigo') or name)
    config_payload = payload.get('configuracion') or payload.get('config') or {}
    # Permite construir desde formulario simple sin enviar JSON completo.
    if not config_payload:
        config_payload = {
            'colors': {
                'primary': payload.get('primary'),
                'primaryHover': payload.get('primaryHover') or payload.get('primary_hover'),
                'accent': payload.get('accent'),
                'background': payload.get('background'),
                'surface': payload.get('surface'),
                'surfaceSoft': payload.get('surfaceSoft') or payload.get('surface_soft'),
                'border': payload.get('border'),
                'text': payload.get('text'),
                'muted': payload.get('muted'),
                'success': payload.get('success'),
                'warning': payload.get('warning'),
                'danger': payload.get('danger'),
            },
            'typography': {
                'fontFamily': payload.get('fontFamily') or payload.get('font_family'),
                'fontScale': payload.get('fontScale') or payload.get('font_scale'),
            },
            'layout': {
                'density': payload.get('density') or payload.get('densidad'),
                'radius': payload.get('radius') or payload.get('radio'),
                'sidebar': payload.get('sidebar'),
                'cards': payload.get('cards'),
            },
            'icons': {
                'style': payload.get('iconStyle') or payload.get('icon_style') or 'lucide',
                'accent': payload.get('iconAccent') or payload.get('accent'),
            },
            'accessibility': {
                'contrast': payload.get('contrast') or payload.get('contraste') or 'normal',
                'reduceMotion': bool(payload.get('reduceMotion')),
            },
        }
    config = sanitize_theme_config(config_payload)
    now = now_iso()
    fundacion_id = int(user.get('fundacion_id') or 1)
    if user.get('rol') == 'SUPERADMIN' and payload.get('global'):
        fundacion_id_for_theme = None
    else:
        fundacion_id_for_theme = fundacion_id
    conn = connect(database_path)
    existing = conn.execute('SELECT * FROM tm_temas WHERE codigo=?', (code,)).fetchone()
    if existing:
        conn.close()
        raise ValueError('Ya existe un tema con ese código.')
    cur = conn.execute(
        """
        INSERT INTO tm_temas
        (codigo, nombre, descripcion, categoria, activo, es_sistema, css_path, icono,
         configuracion_json, preview_json, fecha_creacion, fecha_actualizacion, usuario_creador_id, fundacion_id)
        VALUES (?, ?, ?, ?, 1, 0, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            code, name, str(payload.get('descripcion') or '').strip(), str(payload.get('categoria') or 'personalizado'),
            str(payload.get('css_path') or '').strip(), str(payload.get('icono') or 'palette'),
            safe_json_dumps(config), safe_json_dumps(payload.get('preview') or {}), now, now,
            user.get('id'), fundacion_id_for_theme,
        ),
    )
    conn.commit()
    theme_id = cur.lastrowid
    row = conn.execute('SELECT * FROM tm_temas WHERE id=?', (theme_id,)).fetchone()
    conn.close()
    theme = row_to_theme(row)
    audit(database_path, 'CREAR_TEMA', user, 'tm_temas', code, despues=theme, ip=ip)
    return theme


def update_theme(database_path: str, user: dict[str, Any], codigo: str, payload: dict[str, Any], ip: str | None = None) -> dict[str, Any]:
    code = sanitize_code(codigo)
    conn = connect(database_path)
    old = conn.execute('SELECT * FROM tm_temas WHERE codigo=?', (code,)).fetchone()
    if not old:
        conn.close()
        raise ValueError('Tema no encontrado.')
    old_dict = row_to_theme(old)
    activo = int(payload.get('activo')) if 'activo' in payload else int(old['activo'])
    if int(old['es_sistema']) == 1 and payload.get('eliminar'):
        conn.close()
        raise ValueError('Los temas del sistema no se eliminan; puedes desactivarlos.')
    config = old_dict['configuracion']
    if payload.get('configuracion'):
        config = sanitize_theme_config(payload.get('configuracion'))
    nombre = str(payload.get('nombre') or old['nombre']).strip()
    descripcion = str(payload.get('descripcion') if payload.get('descripcion') is not None else old['descripcion'] or '').strip()
    categoria = str(payload.get('categoria') or old['categoria'] or 'institucional')
    icono = str(payload.get('icono') or old['icono'] or 'palette')
    css_path = str(payload.get('css_path') if payload.get('css_path') is not None else old['css_path'] or '').strip()
    now = now_iso()
    conn.execute(
        """
        UPDATE tm_temas
        SET nombre=?, descripcion=?, categoria=?, activo=?, css_path=?, icono=?, configuracion_json=?, fecha_actualizacion=?
        WHERE codigo=?
        """,
        (nombre, descripcion, categoria, activo, css_path, icono, safe_json_dumps(config), now, code),
    )
    conn.commit()
    row = conn.execute('SELECT * FROM tm_temas WHERE codigo=?', (code,)).fetchone()
    conn.close()
    theme = row_to_theme(row)
    audit(database_path, 'ACTUALIZAR_TEMA', user, 'tm_temas', code, antes=old_dict, despues=theme, ip=ip)
    return theme
