"""ALPHA41: configuración institucional y base del Motor Normativo.

Módulo independiente y no destructivo. No modifica Base Maestra, formatos oficiales,
login, jobs ni rutas existentes. Registra tablas nuevas con IF NOT EXISTS y carga el
manual operativo bajo demanda.
"""
from __future__ import annotations

import os
import json
import hashlib
from modules.dbapi_compat import sqlite3
import io
import re
import zipfile
import uuid
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

from flask import Blueprint, jsonify, request, g, send_from_directory, send_file
from werkzeug.utils import secure_filename

from modules.seguridad.tenant_context import tenant_storage_root

try:
    from modules.seguridad.services import require_roles
except Exception:  # pragma: no cover - fallback si seguridad no está inicializada
    def require_roles(*roles):
        def deco(fn):
            return fn
        return deco

ALLOWED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.svg', '.ico'}
ALLOWED_GLOBAL_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.ico'}
ALLOWED_MANUAL_EXTENSIONS = {'.pdf'}
MAX_IMAGE_MB = 10
MAX_MANUAL_MB = 60

SECCIONES_MANUAL_BASE = [
    ('Introducción', '0', 6, 7),
    ('Contextualización', '1', 8, 47),
    ('Descripción de la modalidad', '2', 48, 71),
    ('Objetivo de la modalidad', '2.1', 50, 51),
    ('Población participante', '2.2', 51, 52),
    ('Criterios de focalización', '2.3', 52, 56),
    ('Componentes de la modalidad', '2.4', 56, 70),
    ('Familia, Comunidad y Redes Sociales', '2.4.1', 57, 59),
    ('Salud y Nutrición', '2.4.2', 59, 65),
    ('Proceso Pedagógico', '2.4.3', 65, 67),
    ('Talento Humano', '2.4.4', 67, 68),
    ('Ambientes Educativos y Protectores', '2.4.5', 68, 70),
    ('Administrativo y de Gestión', '2.4.6', 70, 70),
    ('Servicios de la modalidad', '2.5', 70, 72),
    ('Proceso de atención', '2.6', 72, 84),
    ('Fase I: Preparatoria', '2.6.1.1', 73, 79),
    ('Fase II: Implementación del servicio', '2.6.1.2', 79, 81),
    ('Fase III: Cierre', '2.6.1.3', 81, 82),
    ('Monitoreo y seguimiento', '3', 84, 87),
    ('Articulación con el SNBF', '4', 87, 88),
    ('Sistema Integrado de Gestión', '5', 88, 90),
    ('Sistema de información', '6', 90, 92),
    ('Documentos de referencia', '7', 92, 92),
    ('Control de cambios', '9', 96, 96),
]


def _connect(database_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('PRAGMA busy_timeout=30000')
    except Exception:
        pass
    return conn


def _now() -> str:
    return datetime.now().isoformat(timespec='seconds')


def _user() -> dict[str, Any]:
    user = getattr(g, 'current_user', None) or {}
    return {
        'id': user.get('id'),
        'username': user.get('username') or user.get('email') or 'sistema',
        'rol': user.get('rol') or 'SUPERADMIN',
        'fundacion_id': int(user.get('fundacion_id') or 1),
        'corporacion_id': int(user.get('fundacion_id') or 1),
    }


def _public_path(
    absolute_path: str | None,
    base_dir: str,
    tenant_root: str | os.PathLike[str] | None = None,
) -> str | None:
    """Convierte una ruta local válida en URL pública de Flask.

    Nunca devuelve una URL para un archivo inexistente: así se evita que el
    frontend renderice imágenes rotas y genere bucles de errores 404.
    """
    if not absolute_path:
        return None
    try:
        abs_path = os.path.abspath(str(absolute_path))
        if not os.path.isfile(abs_path):
            return None
        static_dir = os.path.abspath(os.path.join(base_dir, 'static'))
        if os.path.commonpath([abs_path, static_dir]) == static_dir:
            return '/static/' + os.path.relpath(abs_path, static_dir).replace(os.sep, '/')
        if tenant_root:
            tenant_abs = os.path.abspath(os.fspath(tenant_root))
            if os.path.commonpath([abs_path, tenant_abs]) == tenant_abs:
                relative = os.path.relpath(abs_path, tenant_abs).replace(os.sep, '/')
                return '/api/institucional-archivos/' + quote(relative, safe='/')
    except (OSError, ValueError):
        pass
    return None


def _active_asset_path(branding_root: Path, tipo: str, source: Path, token: str) -> Path:
    """Devuelve una ubicación estable para el recurso activo.

    Los lotes permanecen en ``historial`` como respaldo, mientras la plataforma
    consume copias versionadas fuera de esa carpeta. De esta forma una limpieza
    del historial no rompe el logo o favicon activo.
    """
    folders = {
        'logo_principal': branding_root / 'logos' / 'principal',
        'logo_horizontal': branding_root / 'logos' / 'header',
        'logo_reportes': branding_root / 'logos' / 'documentos',
        'logo_formatos': branding_root / 'logos' / 'documentos',
        'logo_documentos': branding_root / 'logos' / 'documentos',
        'logo_impresion': branding_root / 'logos' / 'impresion',
        'favicon_ico': branding_root / 'favicon',
        'favicon_png': branding_root / 'favicon',
    }
    folder = folders.get(tipo, branding_root / 'activos')
    folder.mkdir(parents=True, exist_ok=True)
    safe_token = re.sub(r'[^a-zA-Z0-9_-]', '', token or '')[:40] or uuid.uuid4().hex[:12]
    return folder / f'activo_{safe_token}_{secure_filename(source.name)}'


def _copy_to_active_storage(source_path: str, branding_root: Path, tipo: str, token: str) -> Path:
    source = Path(str(source_path)).resolve()
    if not source.is_file():
        raise FileNotFoundError(f'El recurso original no existe en disco: {source.name}')
    destination = _active_asset_path(branding_root, tipo, source, token)
    shutil.copy2(source, destination)
    return destination.resolve()


def _repair_missing_branding_references(database_path: str, fundacion_id: int) -> None:
    """Limpia referencias antiguas o absolutas que apuntan a archivos ausentes.

    No borra registros: únicamente desactiva recursos inexistentes y deja en NULL
    las rutas de configuración rotas para que la interfaz use su fallback.
    """
    conn = _connect(database_path)
    now = _now()
    try:
        rows = conn.execute(
            'SELECT id, archivo_path, activo FROM identidad_visual_archivos WHERE fundacion_id=?',
            (int(fundacion_id),),
        ).fetchall()
        for row in rows:
            if row['archivo_path'] and not os.path.isfile(str(row['archivo_path'])) and int(row['activo'] or 0) == 1:
                conn.execute('UPDATE identidad_visual_archivos SET activo=0, updated_at=? WHERE id=?', (now, row['id']))
        columns = (
            'logo_principal_path', 'logo_horizontal_path', 'logo_reportes_path',
            'logo_formatos_path', 'logo_documentos_path', 'favicon_path',
            'favicon_png_path', 'foto_admin_path', 'firma_path'
        )
        configs = conn.execute(
            'SELECT * FROM configuracion_institucional WHERE fundacion_id=?',
            (int(fundacion_id),),
        ).fetchall()
        for cfg in configs:
            broken = [col for col in columns if col in cfg.keys() and cfg[col] and not os.path.isfile(str(cfg[col]))]
            if broken:
                assignments = ', '.join(f'{col}=NULL' for col in broken)
                conn.execute(f'UPDATE configuracion_institucional SET {assignments}, updated_at=? WHERE id=?', (now, cfg['id']))
        conn.commit()
    finally:
        conn.close()


def _row_to_dict(
    row: sqlite3.Row | None,
    base_dir: str | None = None,
    tenant_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any] | None:
    if row is None:
        return None
    data = dict(row)
    if base_dir:
        for key in ('logo_principal_path', 'logo_horizontal_path', 'logo_reportes_path', 'logo_formatos_path', 'logo_documentos_path', 'foto_admin_path', 'favicon_path', 'favicon_png_path', 'firma_path'):
            data[key.replace('_path', '_url')] = _public_path(data.get(key), base_dir, tenant_root)
        if data.get('archivo_path'):
            data['archivo_nombre'] = os.path.basename(str(data.get('archivo_path')))
    return data


GLOBAL_FALLBACK = {
    'nombre_plataforma': 'Primera Infancia',
    'sigla': 'PI',
    'nombre_admin': 'Administrador General',
    'cargo_admin': 'Administrador Plataforma',
    'color_primario': '#2563eb',
    'color_secundario': '#06b6d4',
}


def _global_asset_url(tipo: str, version: int | str | None) -> str:
    return f'/api/branding/global/{tipo}?v={version or 1}'


def resolver_identidad_efectiva(
    database_path: str,
    base_dir: str,
    fundacion_id: int | None,
    data_dir: str | os.PathLike[str],
) -> dict[str, Any]:
    """Resuelve fundación -> global -> fallback, campo por campo."""
    conn = _connect(database_path)
    try:
        global_row = conn.execute(
            'SELECT * FROM configuracion_global_plataforma WHERE id=1 AND activo=1'
        ).fetchone()
        tenant_row = None
        if fundacion_id:
            tenant_row = conn.execute(
                '''SELECT * FROM configuracion_institucional
                   WHERE fundacion_id=? AND COALESCE(activo,1)=1
                   ORDER BY id DESC LIMIT 1''',
                (int(fundacion_id),),
            ).fetchone()
    finally:
        conn.close()

    global_cfg = dict(global_row) if global_row else {}
    tenant_root = tenant_storage_root(data_dir, fundacion_id) / 'institutional' if fundacion_id else None
    tenant_cfg = _row_to_dict(tenant_row, base_dir, tenant_root) or {}
    version = max(int(global_cfg.get('identity_version') or 1), 1)

    def choose(tenant_key: str, global_key: str, fallback_key: str | None = None):
        value = tenant_cfg.get(tenant_key)
        # Los valores demostrativos creados por versiones antiguas no deben
        # impedir que una fundación herede la identidad global real.
        if value not in (None, '', 'Organización de prueba', 'ORGDEMO'):
            return value
        value = global_cfg.get(global_key)
        if value not in (None, ''):
            return value
        return GLOBAL_FALLBACK.get(fallback_key or tenant_key)

    def asset(tenant_url: str, global_key: str, tipo: str):
        if tenant_cfg.get(tenant_url):
            return tenant_cfg[tenant_url]
        return _global_asset_url(tipo, version) if global_cfg.get(global_key) else None

    effective = dict(tenant_cfg)
    effective.update({
        'scope': 'FUNDACION' if fundacion_id else 'GLOBAL',
        'fundacion_id': int(fundacion_id) if fundacion_id else None,
        'nombre_plataforma': choose('nombre_plataforma', 'nombre_plataforma'),
        'nombre_corporacion': choose('nombre_corporacion', 'nombre_plataforma'),
        'sigla': choose('sigla', 'sigla_plataforma'),
        # El administrador general pertenece a la identidad global. Los datos
        # locales se conservan en ``administrador_fundacion``, pero no deben
        # reemplazarlo en el encabezado común de las demás sesiones.
        'nombre_admin': global_cfg.get('nombre_administrador_general') or GLOBAL_FALLBACK['nombre_admin'],
        'cargo_admin': global_cfg.get('cargo_administrador_general') or GLOBAL_FALLBACK['cargo_admin'],
        'color_primario': choose('color_primario', 'color_primario_global'),
        'color_secundario': choose('color_secundario', 'color_secundario_global'),
        'logo_principal_url': asset('logo_principal_url', 'logo_global_key', 'logo'),
        'logo_reportes_url': asset('logo_reportes_url', 'logo_reportes_global_key', 'logo-reportes'),
        'logo_formatos_url': asset('logo_formatos_url', 'logo_formatos_global_key', 'logo-formatos'),
        'favicon_url': asset('favicon_url', 'favicon_global_key', 'favicon'),
        'foto_admin_url': _global_asset_url('foto-admin', version) if global_cfg.get('foto_administrador_general_key') else None,
        'identity_version': version,
        'updated_at': max(str(tenant_cfg.get('updated_at') or ''), str(global_cfg.get('updated_at') or '')),
        'administrador_general': {
            'nombre': global_cfg.get('nombre_administrador_general') or GLOBAL_FALLBACK['nombre_admin'],
            'cargo': global_cfg.get('cargo_administrador_general') or GLOBAL_FALLBACK['cargo_admin'],
            'foto_url': _global_asset_url('foto-admin', version) if global_cfg.get('foto_administrador_general_key') else None,
        },
        'administrador_fundacion': {
            'nombre': tenant_cfg.get('nombre_admin'),
            'cargo': tenant_cfg.get('cargo_admin'),
            'foto_url': tenant_cfg.get('foto_admin_url'),
        },
    })
    return effective


def _safe_ext(filename: str) -> str:
    return os.path.splitext((filename or '').lower())[1]


def _safe_filename(prefix: str, filename: str) -> str:
    original = secure_filename(filename or 'archivo')
    if not original:
        original = 'archivo'
    return f"{prefix}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{original}"


def _require_file(field: str, allowed: set[str], max_mb: int):
    if field not in request.files:
        raise ValueError('No se recibió archivo.')
    file = request.files[field]
    if not file or not file.filename:
        raise ValueError('No se seleccionó ningún archivo.')
    ext = _safe_ext(file.filename)
    if ext not in allowed:
        raise ValueError(f'Extensión no permitida. Usa: {", ".join(sorted(allowed))}.')
    try:
        pos = file.stream.tell()
        file.stream.seek(0, os.SEEK_END)
        size = file.stream.tell()
        file.stream.seek(pos)
        if size > max_mb * 1024 * 1024:
            raise ValueError(f'El archivo supera el máximo permitido de {max_mb} MB.')
    except ValueError:
        raise
    except Exception:
        pass
    return file


def _sanitize_svg_bytes(raw: bytes) -> bytes:
    text = raw.decode('utf-8', errors='strict')
    lowered = text.lower()
    forbidden = ('<script', 'javascript:', 'onload=', 'onerror=', '<foreignobject', '<iframe', '<object', '<embed')
    if any(token in lowered for token in forbidden):
        raise ValueError('El SVG contiene scripts o elementos inseguros.')
    return raw


def _load_source_image(file):
    raw = file.read()
    file.stream.seek(0)
    ext = _safe_ext(file.filename)
    if ext == '.svg':
        _sanitize_svg_bytes(raw)
        try:
            import cairosvg
        except Exception as exc:
            raise ValueError('Para procesar SVG instala CairoSVG. También puedes subir PNG, JPG o WEBP.') from exc
        raw = cairosvg.svg2png(bytestring=raw, output_width=2400, output_height=2400)
    try:
        from PIL import Image, ImageOps
        image = Image.open(io.BytesIO(raw))
        image.verify()
        image = Image.open(io.BytesIO(raw))
        image = ImageOps.exif_transpose(image)
        if image.width < 16 or image.height < 16:
            raise ValueError('La imagen es demasiado pequeña para generar recursos.')
        return image.convert('RGBA'), raw
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError('El archivo no contiene una imagen válida o está dañado.') from exc


def _remove_near_white(image, tolerance: int = 18):
    rgba = image.convert('RGBA')
    pixels = []
    threshold = 255 - max(1, min(60, tolerance))
    for r, g, b, a in rgba.getdata():
        pixels.append((r, g, b, 0) if r >= threshold and g >= threshold and b >= threshold else (r, g, b, a))
    rgba.putdata(pixels)
    return rgba


def _fit_canvas(image, size: tuple[int, int], margin_ratio: float = 0.06, allow_upscale: bool = True):
    from PIL import Image, ImageOps
    target_w, target_h = size
    margin = int(min(target_w, target_h) * margin_ratio)
    inner = (max(1, target_w - margin * 2), max(1, target_h - margin * 2))
    work = image.copy()
    if not allow_upscale and work.width <= inner[0] and work.height <= inner[1]:
        resized = work
    else:
        resized = ImageOps.contain(work, inner, method=Image.Resampling.LANCZOS)
    canvas = Image.new('RGBA', size, (255, 255, 255, 0))
    canvas.alpha_composite(resized, ((target_w - resized.width)//2, (target_h - resized.height)//2))
    return canvas


def _save_png(image, path: Path, dpi=(96, 96)):
    from PIL import ImageFilter
    path.parent.mkdir(parents=True, exist_ok=True)
    prepared = image.filter(ImageFilter.UnsharpMask(radius=1.2, percent=105, threshold=3))
    prepared.save(path, 'PNG', optimize=True, dpi=dpi)


def _asset_record(conn, *, fundacion_id, tipo, original, path: Path, user, batch_id, width, height, version):
    now = _now()
    mime = 'image/x-icon' if path.suffix.lower() == '.ico' else ('image/webp' if path.suffix.lower() == '.webp' else 'image/png')
    sql = ('INSERT INTO identidad_visual_archivos '
           '(fundacion_id,tipo,nombre_original,nombre_archivo,archivo_path,mime_type,tamano_bytes,activo,cargado_por,created_at,updated_at,ancho,alto,version,lote_id,fecha_aplicacion) '
           'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL)')
    conn.execute(sql, (fundacion_id,tipo,original,path.name,str(path),mime,path.stat().st_size,0,user,now,now,width,height,version,batch_id))


def _branding_version(now: datetime | None = None) -> int:
    """Return an ordered version that fits PostgreSQL's 32-bit INTEGER.

    The former YYYYMMDDHHMMSS representation has 14 digits and therefore
    overflowed the INTEGER column used by ``identidad_visual_archivos``.
    Minute precision is sufficient because each generation also has a unique
    ``lote_id``.
    """
    current = now or datetime.now()
    return current.toordinal() * 1440 + current.hour * 60 + current.minute


def _generate_branding_assets(image, root: Path, remove_white: bool):
    from PIL import Image
    if remove_white:
        image = _remove_near_white(image)
    generated = []
    dirs = {'principal': root/'logos'/'principal', 'header': root/'logos'/'header', 'documentos': root/'logos'/'documentos', 'impresion': root/'logos'/'impresion', 'favicon': root/'favicon'}
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    principal = _fit_canvas(image, (1600, 1600), .06, allow_upscale=False)
    path = dirs['principal']/'logo_principal.png'; _save_png(principal, path); generated.append(('logo_principal',path,*principal.size))
    path = dirs['principal']/'logo_principal.webp'; principal.save(path,'WEBP',lossless=True,quality=95,method=6); generated.append(('logo_principal',path,*principal.size))
    path = dirs['impresion']/'logo_principal_300dpi.png'; _save_png(principal,path,dpi=(300,300)); generated.append(('logo_impresion',path,*principal.size))
    header = _fit_canvas(image, (1200, 300), .05, allow_upscale=False)
    path = dirs['header']/'logo_header.png'; _save_png(header,path); generated.append(('logo_horizontal',path,*header.size))
    path = dirs['header']/'logo_header.webp'; header.save(path,'WEBP',lossless=True,quality=95,method=6); generated.append(('logo_horizontal',path,*header.size))
    doc_sizes={'logo_word.png':(1600,1600),'logo_excel.png':(1600,1600),'logo_powerpoint.png':(1920,1080),'logo_pdf.png':(1600,1600),'logo_impresion_300dpi.png':(2400,2400)}
    for name,size in doc_sizes.items():
        canvas=_fit_canvas(image,size,.07,allow_upscale=False); path=dirs['documentos']/name
        _save_png(canvas,path,dpi=(300,300) if '300dpi' in name else (96,96))
        generated.append(('logo_reportes' if name=='logo_pdf.png' else 'logo_documentos',path,*canvas.size))
    icon_base=_fit_canvas(image,(512,512),.08,allow_upscale=False)
    icons={}
    for sz in [16,32,48,64,96,180,192,256,512]:
        icon=icon_base.resize((sz,sz),Image.Resampling.LANCZOS); path=dirs['favicon']/f'favicon-{sz}x{sz}.png'; _save_png(icon,path)
        generated.append(('favicon_png',path,sz,sz)); icons[sz]=icon
    path=dirs['favicon']/'apple-touch-icon.png'; _save_png(icons[180],path); generated.append(('favicon_png',path,180,180))
    path=dirs['favicon']/'favicon.ico'; icons[256].save(path,format='ICO',sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)]); generated.append(('favicon_ico',path,256,256))
    return generated

def init_schema(database_path: str) -> None:
    conn = _connect(database_path)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS configuracion_institucional (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            corporacion_id INTEGER DEFAULT 1,
            fundacion_id INTEGER DEFAULT 1,
            nombre_plataforma TEXT,
            nombre_corporacion TEXT,
            sigla TEXT,
            nit TEXT,
            representante_legal TEXT,
            direccion TEXT,
            telefono TEXT,
            correo TEXT,
            logo_principal_path TEXT,
            logo_reportes_path TEXT,
            logo_formatos_path TEXT,
            foto_admin_path TEXT,
            favicon_path TEXT,
            nombre_admin TEXT,
            cargo_admin TEXT,
            color_primario TEXT,
            color_secundario TEXT,
            firma_path TEXT,
            activo INTEGER DEFAULT 1,
            creado_por TEXT,
            actualizado_por TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS manuales_operativos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            corporacion_id INTEGER DEFAULT 1,
            fundacion_id INTEGER DEFAULT 1,
            codigo TEXT,
            nombre TEXT,
            version TEXT,
            fecha_documento TEXT,
            estado TEXT DEFAULT 'borrador',
            archivo_path TEXT,
            total_paginas INTEGER,
            observacion TEXT,
            cargado_por TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS manuales_operativos_secciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            manual_id INTEGER,
            titulo TEXT,
            numero TEXT,
            pagina_inicio INTEGER,
            pagina_fin INTEGER,
            orden INTEGER,
            resumen TEXT,
            created_at TEXT,
            FOREIGN KEY (manual_id) REFERENCES manuales_operativos(id)
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS auditoria_institucional_alpha41 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            accion TEXT NOT NULL,
            entidad TEXT,
            entidad_id INTEGER,
            detalle_json TEXT,
            usuario TEXT,
            fundacion_id INTEGER DEFAULT 1,
            fecha TEXT NOT NULL
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS identidad_visual_archivos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fundacion_id INTEGER DEFAULT 1,
            tipo TEXT NOT NULL,
            nombre_original TEXT,
            nombre_archivo TEXT NOT NULL,
            archivo_path TEXT NOT NULL,
            mime_type TEXT,
            tamano_bytes INTEGER DEFAULT 0,
            activo INTEGER DEFAULT 1,
            cargado_por TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    # ALPHA44: columnas de marca blanca añadidas de forma idempotente para bases existentes.
    existentes = {row[1] for row in cur.execute('PRAGMA table_info(configuracion_institucional)').fetchall()}
    columnas_extra = {
        'nombre_plataforma': 'TEXT',
        'favicon_path': 'TEXT',
        'logo_horizontal_path': 'TEXT',
        'logo_documentos_path': 'TEXT',
        'favicon_png_path': 'TEXT',
    }
    for columna, tipo in columnas_extra.items():
        if columna not in existentes:
            cur.execute(f'ALTER TABLE configuracion_institucional ADD COLUMN {columna} {tipo}')
    identidad_cols = {row[1] for row in cur.execute('PRAGMA table_info(identidad_visual_archivos)').fetchall()}
    identidad_extra = {'ancho':'INTEGER','alto':'INTEGER','version':'INTEGER DEFAULT 1','lote_id':'TEXT','fecha_aplicacion':'TEXT'}
    for columna, tipo in identidad_extra.items():
        if columna not in identidad_cols:
            cur.execute(f'ALTER TABLE identidad_visual_archivos ADD COLUMN {columna} {tipo}')
    for stmt in [
        'CREATE INDEX IF NOT EXISTS idx_config_inst_fund ON configuracion_institucional(fundacion_id, activo)',
        'CREATE INDEX IF NOT EXISTS idx_manuales_fund_estado ON manuales_operativos(fundacion_id, estado)',
        'CREATE INDEX IF NOT EXISTS idx_manuales_secciones_manual ON manuales_operativos_secciones(manual_id, orden)',
        'CREATE INDEX IF NOT EXISTS idx_identidad_visual_fund_tipo ON identidad_visual_archivos(fundacion_id, tipo, activo)',
    ]:
        cur.execute(stmt)
    conn.commit()
    conn.close()


def _audit(database_path: str, accion: str, entidad: str, entidad_id: int | None, detalle: dict[str, Any] | None = None) -> None:
    try:
        user = _user()
        conn = _connect(database_path)
        conn.execute('''
            INSERT INTO auditoria_institucional_alpha41
            (accion, entidad, entidad_id, detalle_json, usuario, fundacion_id, fecha)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (accion, entidad, entidad_id, json.dumps(detalle or {}, ensure_ascii=False), user['username'], user['fundacion_id'], _now()))
        conn.commit()
        conn.close()
    except Exception:
        pass


def _get_or_create_config(
    database_path: str,
    base_dir: str,
    fundacion_id: int,
    tenant_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    if tenant_root is None:
        tenant_root = tenant_storage_root(Path(database_path).resolve().parent, fundacion_id) / 'institutional'
    conn = _connect(database_path)
    row = conn.execute('''
        SELECT * FROM configuracion_institucional
        WHERE fundacion_id=? AND COALESCE(activo, 1)=1
        ORDER BY id DESC LIMIT 1
    ''', (fundacion_id,)).fetchone()
    if not row:
        now = _now()
        insert_cursor = conn.execute('''
            INSERT INTO configuracion_institucional
            (corporacion_id, fundacion_id, nombre_plataforma, nombre_corporacion, sigla, nombre_admin, cargo_admin, color_primario, color_secundario, activo, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
        ''', (
            fundacion_id,
            fundacion_id,
            'Primera Infancia',
            'Organización de prueba',
            'ORGDEMO',
            'Administrador General',
            'Administrador Plataforma',
            '#2563eb',
            '#06b6d4',
            now,
            now
        ))
        conn.commit()
        row = conn.execute(
            'SELECT * FROM configuracion_institucional WHERE id=?',
            (insert_cursor.lastrowid,),
        ).fetchone()
    data = _row_to_dict(row, base_dir, tenant_root) or {}
    conn.close()
    return data


def _manual_to_dict(
    row: sqlite3.Row,
    base_dir: str,
    database_path: str,
    tenant_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    if tenant_root is None:
        fundacion_id = int(row['fundacion_id'] or _user()['fundacion_id']) if 'fundacion_id' in row.keys() else _user()['fundacion_id']
        tenant_root = tenant_storage_root(Path(database_path).resolve().parent, fundacion_id) / 'institutional'
    data = _row_to_dict(row, base_dir, tenant_root) or {}
    conn = _connect(database_path)
    secs = conn.execute('''
        SELECT id, titulo, numero, pagina_inicio, pagina_fin, orden, resumen
        FROM manuales_operativos_secciones
        WHERE manual_id=? ORDER BY orden ASC, id ASC
    ''', (data.get('id'),)).fetchall()
    conn.close()
    data['secciones'] = [dict(s) for s in secs]
    return data


def _count_pdf_pages(path: str) -> int | None:
    try:
        from pypdf import PdfReader
        return len(PdfReader(path).pages)
    except Exception:
        return None


def register_institucional_normativo(app, database_path: str, base_dir: str) -> None:
    data_dir = Path(str(app.config.get('DATA_DIR') or (Path(base_dir).parent / 'data'))).resolve()
    global_branding_root = (data_dir / 'global' / 'branding').resolve()
    for folder in ('logo', 'admin', 'favicon'):
        (global_branding_root / folder).mkdir(parents=True, exist_ok=True)

    def _build_tenant_dirs(fundacion_id: int) -> dict[str, Path]:
        root = (tenant_storage_root(data_dir, fundacion_id) / 'institutional').resolve()
        uploads_root = root / 'uploads'
        branding_root = root / 'branding'
        directories = {
            'root': root,
            'uploads_root': uploads_root,
            'logos_dir': uploads_root / 'logos',
            'fotos_dir': uploads_root / 'fotos_admin',
            'favicons_dir': uploads_root / 'favicons',
            'manuales_dir': uploads_root / 'manuales_operativos',
            'branding_root': branding_root,
            'originales_dir': branding_root / 'originales',
            'backups_branding_dir': branding_root / 'backups',
            'historial_dir': branding_root / 'historial',
        }
        for folder in directories.values():
            folder.mkdir(parents=True, exist_ok=True)
        return directories

    def _tenant_dirs() -> dict[str, Path]:
        cached = getattr(g, 'institutional_tenant_dirs', None)
        if cached:
            return cached
        directories = _build_tenant_dirs(_user()['fundacion_id'])
        g.institutional_tenant_dirs = directories
        return directories

    def _serialize_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
        return _row_to_dict(row, base_dir, _tenant_dirs()['root'])

    def _institutional_config(fundacion_id: int) -> dict[str, Any]:
        return _get_or_create_config(database_path, base_dir, fundacion_id, _tenant_dirs()['root'])

    def _serialize_manual(row: sqlite3.Row) -> dict[str, Any]:
        return _manual_to_dict(row, base_dir, database_path, _tenant_dirs()['root'])

    bp = Blueprint('institucional_normativo', __name__)

    def _global_row():
        conn = _connect(database_path)
        try:
            return conn.execute('SELECT * FROM configuracion_global_plataforma WHERE id=1').fetchone()
        finally:
            conn.close()

    def _save_global_asset(tipo: str, column: str):
        file = _require_file('file', ALLOWED_GLOBAL_IMAGE_EXTENSIONS, MAX_IMAGE_MB)
        _, raw = _load_source_image(file)
        extension = _safe_ext(file.filename)
        token = uuid.uuid4().hex
        folder = {'logo': 'logo', 'logo-reportes': 'logo', 'logo-formatos': 'logo', 'foto-admin': 'admin', 'favicon': 'favicon'}[tipo]
        filename = f'{tipo.replace("-", "_")}_{token}{extension}'
        destination = (global_branding_root / folder / filename).resolve()
        if os.path.commonpath([str(destination), str(global_branding_root)]) != str(global_branding_root):
            raise ValueError('Ruta global de identidad no autorizada.')
        destination.write_bytes(raw)
        storage_key = destination.relative_to(data_dir).as_posix()
        digest = hashlib.sha256(raw).hexdigest()
        mime = {'.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp','.ico':'image/x-icon'}[extension]
        user = _user()
        conn = _connect(database_path)
        now = _now()
        try:
            current = conn.execute('SELECT identity_version FROM configuracion_global_plataforma WHERE id=1').fetchone()
            version = int(current[0] or 1) + 1
            conn.execute('UPDATE identidad_global_archivos SET activo=0, updated_at=? WHERE tipo=?', (now, tipo))
            conn.execute(
                '''INSERT INTO identidad_global_archivos
                   (tipo,storage_key,nombre_original,mime_type,tamano_bytes,sha256,version,activo,cargado_por,created_at,updated_at)
                   VALUES (?,?,?,?,?,?,?,1,?,?,?)''',
                (tipo, storage_key, secure_filename(file.filename), mime, len(raw), digest, version, user['username'], now, now),
            )
            conn.execute(
                f'''UPDATE configuracion_global_plataforma
                    SET {column}=?, identity_version=?, updated_by=?, updated_at=? WHERE id=1''',
                (storage_key, version, user['username'], now),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            destination.unlink(missing_ok=True)
            raise
        finally:
            conn.close()
        return resolver_identidad_efectiva(database_path, base_dir, None, data_dir)

    @bp.before_request
    def _ensure_schema():
        if request.endpoint in {
            'institucional_normativo.configuracion_publica',
            'institucional_normativo.servir_branding_global',
        }:
            return None
        directories = _tenant_dirs()
        _repair_missing_branding_references(database_path, _user()['fundacion_id'])
        g.institutional_tenant_dirs = directories

    @bp.route('/api/configuracion-publica', methods=['GET'])
    def configuracion_publica():
        cfg = resolver_identidad_efectiva(database_path, base_dir, None, data_dir)
        response = jsonify({'configuracion': {
            'nombre_plataforma': cfg['nombre_plataforma'],
            'sigla_plataforma': cfg['sigla'],
            'logo_global_url': cfg['logo_principal_url'],
            'favicon_global_url': cfg['favicon_url'],
            'color_primario': cfg['color_primario'],
            'color_secundario': cfg['color_secundario'],
            'nombre_admin': cfg['nombre_admin'],
            'cargo_admin': cfg['cargo_admin'],
            'foto_admin_url': cfg['foto_admin_url'],
            'identity_version': cfg['identity_version'],
            'updated_at': cfg['updated_at'],
        }})
        response.headers['Cache-Control'] = 'no-cache, must-revalidate'
        return response, 200

    @bp.route('/api/configuracion-institucional/efectiva', methods=['GET'])
    def configuracion_institucional_efectiva():
        user = _user()
        response = jsonify({'configuracion': resolver_identidad_efectiva(
            database_path, base_dir, user['fundacion_id'], data_dir
        )})
        response.headers['Cache-Control'] = 'no-cache, must-revalidate'
        return response, 200

    @bp.route('/api/configuracion-global', methods=['GET'])
    @require_roles('SUPERADMIN', 'GERENTE')
    def obtener_configuracion_global():
        row = _global_row()
        return jsonify({'configuracion': dict(row) if row else None,
                        'efectiva': resolver_identidad_efectiva(database_path, base_dir, None, data_dir)}), 200

    @bp.route('/api/configuracion-global', methods=['POST'])
    @require_roles('SUPERADMIN', 'GERENTE')
    def guardar_configuracion_global():
        data = request.get_json(silent=True) or request.form.to_dict() or {}
        allowed = {
            'nombre_plataforma', 'sigla_plataforma', 'nombre_administrador_general',
            'cargo_administrador_general', 'color_primario_global', 'color_secundario_global',
        }
        values = {key: str(data.get(key) or '').strip()[:240] for key in allowed if key in data}
        for color_key in ('color_primario_global', 'color_secundario_global'):
            if color_key in values and values[color_key] and not re.fullmatch(r'#[0-9a-fA-F]{6}', values[color_key]):
                return jsonify({'error': f'{color_key} debe usar formato hexadecimal #RRGGBB.'}), 422
        user = _user()
        conn = _connect(database_path)
        now = _now()
        try:
            if values:
                assignments = ', '.join(f'{key}=?' for key in values)
                conn.execute(
                    f'''UPDATE configuracion_global_plataforma SET {assignments},
                        identity_version=identity_version+1, updated_by=?, updated_at=? WHERE id=1''',
                    [*values.values(), user['username'], now],
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return jsonify({'message': 'Configuración global guardada correctamente.',
                        'configuracion': resolver_identidad_efectiva(database_path, base_dir, None, data_dir)}), 200

    @bp.route('/api/configuracion-global/logo', methods=['POST'])
    @require_roles('SUPERADMIN', 'GERENTE')
    def subir_logo_global():
        tipo = (request.form.get('tipo') or 'principal').strip().lower()
        mapping = {
            'principal': ('logo', 'logo_global_key'),
            # La tabla global conserva tres fuentes maestras. Horizontal usa
            # el principal y documentos usa el de formatos como equivalencias
            # explícitas, en vez de rechazar opciones visibles en la interfaz.
            'horizontal': ('logo', 'logo_global_key'),
            'reportes': ('logo-reportes', 'logo_reportes_global_key'),
            'formatos': ('logo-formatos', 'logo_formatos_global_key'),
            'documentos': ('logo-formatos', 'logo_formatos_global_key'),
        }
        if tipo not in mapping:
            return jsonify({'error': 'Tipo de logo global no admitido.'}), 422
        try:
            asset_type, column = mapping[tipo]
            cfg = _save_global_asset(asset_type, column)
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 422
        return jsonify({'message': 'Logo global actualizado correctamente.', 'configuracion': cfg}), 200

    @bp.route('/api/configuracion-global/foto-admin', methods=['POST'])
    @require_roles('SUPERADMIN', 'GERENTE')
    def subir_foto_admin_global():
        try:
            cfg = _save_global_asset('foto-admin', 'foto_administrador_general_key')
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 422
        return jsonify({'message': 'Foto del administrador general actualizada correctamente.', 'configuracion': cfg}), 200

    @bp.route('/api/configuracion-global/favicon', methods=['POST'])
    @require_roles('SUPERADMIN', 'GERENTE')
    def subir_favicon_global():
        try:
            cfg = _save_global_asset('favicon', 'favicon_global_key')
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 422
        return jsonify({'message': 'Favicon global actualizado correctamente.', 'configuracion': cfg}), 200

    @bp.route('/api/branding/global/<tipo>', methods=['GET'])
    def servir_branding_global(tipo: str):
        mapping = {
            'logo': 'logo_global_key', 'logo-reportes': 'logo_reportes_global_key',
            'logo-formatos': 'logo_formatos_global_key', 'foto-admin': 'foto_administrador_general_key',
            'favicon': 'favicon_global_key',
        }
        column = mapping.get(tipo)
        if not column:
            return jsonify({'error': 'Recurso global no encontrado.'}), 404
        row = _global_row()
        storage_key = row[column] if row and column in row.keys() else None
        if not storage_key:
            return jsonify({'error': 'Recurso global no configurado.'}), 404
        candidate = (data_dir / str(storage_key)).resolve()
        try:
            if os.path.commonpath([str(candidate), str(global_branding_root)]) != str(global_branding_root):
                return jsonify({'error': 'Ruta global no autorizada.'}), 403
        except ValueError:
            return jsonify({'error': 'Ruta global no autorizada.'}), 403
        if not candidate.is_file():
            return jsonify({'error': 'Recurso global no disponible.'}), 404
        response = send_file(candidate, conditional=True)
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        return response

    @bp.route('/api/institucional-archivos/<path:relative_path>', methods=['GET'])
    def servir_archivo_institucional(relative_path: str):
        directories = _tenant_dirs()
        root = directories['root'].resolve()
        candidate = (root / relative_path).resolve()
        try:
            if os.path.commonpath([str(candidate), str(root)]) != str(root):
                return jsonify({'error': 'Ruta institucional no autorizada.'}), 403
        except ValueError:
            return jsonify({'error': 'Ruta institucional no autorizada.'}), 403
        if not candidate.is_file():
            return jsonify({'error': 'Archivo institucional no encontrado.'}), 404
        # ``send_from_directory`` usa rutas URL (separador ``/``). En Windows,
        # ``str(Path.relative_to(...))`` produce barras invertidas y Werkzeug
        # termina buscando un nombre inexistente, aunque el archivo esté en disco.
        relative_file = candidate.relative_to(root).as_posix()
        return send_from_directory(str(root), relative_file, as_attachment=False)

    @bp.route('/api/configuracion-institucional', methods=['GET'])
    def obtener_configuracion():
        user = _user()
        return jsonify({'configuracion': _institutional_config(user['fundacion_id'])}), 200

    @bp.route('/api/configuracion-institucional', methods=['POST'])
    @require_roles('SUPERADMIN', 'ADMINISTRADOR', 'GERENTE')
    def guardar_configuracion():
        user = _user()
        data = request.get_json(silent=True) or request.form.to_dict() or {}
        allowed = [
            'nombre_plataforma', 'nombre_corporacion', 'sigla', 'nit', 'representante_legal', 'direccion', 'telefono', 'correo',
            'nombre_admin', 'cargo_admin', 'color_primario', 'color_secundario'
        ]
        values = {k: str(data.get(k) or '').strip() for k in allowed if k in data}
        conn = _connect(database_path)
        row = conn.execute('SELECT * FROM configuracion_institucional WHERE fundacion_id=? AND COALESCE(activo,1)=1 ORDER BY id DESC LIMIT 1', (user['fundacion_id'],)).fetchone()
        now = _now()
        if row:
            if values:
                set_sql = ', '.join([f'{k}=?' for k in values])
                params = list(values.values()) + [user['username'], now, row['id']]
                conn.execute(f'UPDATE configuracion_institucional SET {set_sql}, actualizado_por=?, updated_at=? WHERE id=?', params)
                cfg_id = row['id']
            else:
                cfg_id = row['id']
        else:
            payload = {k: values.get(k) for k in allowed}
            payload.setdefault('nombre_plataforma', 'Primera Infancia')
            payload.setdefault('nombre_corporacion', 'Organización de prueba')
            payload.setdefault('sigla', 'ORGDEMO')
            cols = ['corporacion_id', 'fundacion_id'] + allowed + ['activo', 'creado_por', 'actualizado_por', 'created_at', 'updated_at']
            params = [user['corporacion_id'], user['fundacion_id']] + [payload.get(k) for k in allowed] + [1, user['username'], user['username'], now, now]
            insert_cursor = conn.execute(f"INSERT INTO configuracion_institucional ({', '.join(cols)}) VALUES ({', '.join(['?'] * len(cols))})", params)
            cfg_id = insert_cursor.lastrowid
        conn.commit()
        cfg = conn.execute('SELECT * FROM configuracion_institucional WHERE id=?', (cfg_id,)).fetchone()
        conn.close()
        _audit(database_path, 'GUARDAR_CONFIGURACION_INSTITUCIONAL', 'configuracion_institucional', cfg_id, values)
        return jsonify({'message': 'Configuración institucional guardada correctamente.', 'configuracion': _serialize_row(cfg)}), 200

    @bp.route('/api/configuracion-institucional/logo', methods=['POST'])
    @require_roles('SUPERADMIN', 'ADMINISTRADOR', 'GERENTE')
    def subir_logo():
        try:
            file = _require_file('file', ALLOWED_IMAGE_EXTENSIONS, MAX_IMAGE_MB)
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 400
        tipo = (request.form.get('tipo') or 'principal').strip().lower()
        mapping = {
            'principal': ('logo_principal_path', 'logo_principal'),
            'horizontal': ('logo_horizontal_path', 'logo_horizontal'),
            'reportes': ('logo_reportes_path', 'logo_reportes'),
            'formatos': ('logo_formatos_path', 'logo_formatos'),
            'documentos': ('logo_documentos_path', 'logo_documentos'),
        }
        col, asset_type = mapping.get(tipo, mapping['principal'])
        user = _user()
        directories = _tenant_dirs()
        cfg = _institutional_config(user['fundacion_id'])
        nombre = _safe_filename(f'LOGO_{tipo.upper()}_{user["fundacion_id"]}', file.filename)
        path = (directories['logos_dir'] / nombre).resolve()
        file.save(str(path))
        if not path.is_file() or path.stat().st_size <= 0:
            return jsonify({'error': 'El servidor recibió el logo, pero no pudo guardarlo en disco.'}), 500
        conn = _connect(database_path)
        now = _now()
        conn.execute(f'UPDATE configuracion_institucional SET {col}=?, actualizado_por=?, updated_at=? WHERE id=?', (str(path), user['username'], now, cfg['id']))
        conn.execute('UPDATE identidad_visual_archivos SET activo=0, updated_at=? WHERE fundacion_id=? AND tipo=?', (now, user['fundacion_id'], asset_type))
        conn.execute('INSERT INTO identidad_visual_archivos (fundacion_id,tipo,nombre_original,nombre_archivo,archivo_path,mime_type,tamano_bytes,activo,cargado_por,created_at,updated_at) VALUES (?,?,?,?,?,?,?,1,?,?,?)', (user['fundacion_id'],asset_type,file.filename,nombre,str(path),file.mimetype or '',path.stat().st_size,user['username'],now,now))
        # El logo principal es también la fuente de encabezados para los
        # generadores históricos que consultan fundaciones/corporaciones.
        if tipo == 'principal':
            fund_cols = {r['name'] for r in conn.execute('PRAGMA table_info(fundaciones)').fetchall()}
            if 'logo_path' in fund_cols:
                if 'fecha_actualizacion' in fund_cols:
                    conn.execute('UPDATE fundaciones SET logo_path=?, fecha_actualizacion=? WHERE id=?', (str(path), now, user['fundacion_id']))
                else:
                    conn.execute('UPDATE fundaciones SET logo_path=? WHERE id=?', (str(path), user['fundacion_id']))
            corp_cols = {r['name'] for r in conn.execute('PRAGMA table_info(corporaciones)').fetchall()}
            if 'logo_path' in corp_cols:
                if 'fecha_actualizacion' in corp_cols:
                    conn.execute('UPDATE corporaciones SET logo_path=?, fecha_actualizacion=? WHERE fundacion_id=?', (str(path), now, user['fundacion_id']))
                else:
                    conn.execute('UPDATE corporaciones SET logo_path=? WHERE fundacion_id=?', (str(path), user['fundacion_id']))
        conn.commit()
        row = conn.execute('SELECT * FROM configuracion_institucional WHERE id=?', (cfg['id'],)).fetchone()
        conn.close()
        _audit(database_path, 'SUBIR_LOGO_INSTITUCIONAL', 'configuracion_institucional', cfg['id'], {'tipo': tipo, 'archivo': nombre})
        return jsonify({'message': 'Logo institucional cargado correctamente.', 'configuracion': _serialize_row(row)}), 200

    @bp.route('/api/configuracion-institucional/foto-admin', methods=['POST'])
    @require_roles('SUPERADMIN', 'ADMINISTRADOR', 'GERENTE')
    def subir_foto_admin():
        try:
            file = _require_file('file', ALLOWED_IMAGE_EXTENSIONS, MAX_IMAGE_MB)
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 400
        user = _user()
        directories = _tenant_dirs()
        cfg = _institutional_config(user['fundacion_id'])
        nombre = _safe_filename(f'FOTO_ADMIN_{user["fundacion_id"]}', file.filename)
        path = (directories['fotos_dir'] / nombre).resolve()
        file.save(str(path))
        if not path.is_file() or path.stat().st_size <= 0:
            return jsonify({'error': 'El servidor recibió la foto, pero no pudo guardarla en disco.'}), 500
        conn = _connect(database_path)
        now = _now()
        conn.execute('UPDATE configuracion_institucional SET foto_admin_path=?, actualizado_por=?, updated_at=? WHERE id=?', (str(path), user['username'], now, cfg['id']))
        conn.execute('UPDATE identidad_visual_archivos SET activo=0, updated_at=? WHERE fundacion_id=? AND tipo=?', (now, user['fundacion_id'], 'foto_admin'))
        conn.execute('INSERT INTO identidad_visual_archivos (fundacion_id,tipo,nombre_original,nombre_archivo,archivo_path,mime_type,tamano_bytes,activo,cargado_por,created_at,updated_at) VALUES (?,?,?,?,?,?,?,1,?,?,?)', (user['fundacion_id'],'foto_admin',file.filename,nombre,str(path),file.mimetype or '',path.stat().st_size,user['username'],now,now))
        conn.commit()
        row = conn.execute('SELECT * FROM configuracion_institucional WHERE id=?', (cfg['id'],)).fetchone()
        conn.close()
        _audit(database_path, 'SUBIR_FOTO_ADMIN', 'configuracion_institucional', cfg['id'], {'archivo': nombre})
        return jsonify({'message': 'Foto del administrador cargada correctamente.', 'configuracion': _serialize_row(row)}), 200

    @bp.route('/api/configuracion-institucional/favicon', methods=['POST'])
    @require_roles('SUPERADMIN', 'ADMINISTRADOR', 'GERENTE')
    def subir_favicon():
        try:
            file = _require_file('file', ALLOWED_IMAGE_EXTENSIONS, MAX_IMAGE_MB)
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 400
        user = _user()
        directories = _tenant_dirs()
        cfg = _institutional_config(user['fundacion_id'])
        nombre = _safe_filename(f'FAVICON_{user["fundacion_id"]}', file.filename)
        path = (directories['favicons_dir'] / nombre).resolve()
        file.save(str(path))
        if not path.is_file() or path.stat().st_size <= 0:
            return jsonify({'error': 'El servidor recibió el favicon, pero no pudo guardarlo en disco.'}), 500
        ext = _safe_ext(file.filename)
        col = 'favicon_path' if ext == '.ico' else 'favicon_png_path'
        asset_type = 'favicon_ico' if ext == '.ico' else 'favicon_png'
        conn = _connect(database_path)
        now = _now()
        conn.execute(f'UPDATE configuracion_institucional SET {col}=?, actualizado_por=?, updated_at=? WHERE id=?', (str(path), user['username'], now, cfg['id']))
        conn.execute('UPDATE identidad_visual_archivos SET activo=0, updated_at=? WHERE fundacion_id=? AND tipo=?', (now, user['fundacion_id'], asset_type))
        conn.execute('INSERT INTO identidad_visual_archivos (fundacion_id,tipo,nombre_original,nombre_archivo,archivo_path,mime_type,tamano_bytes,activo,cargado_por,created_at,updated_at) VALUES (?,?,?,?,?,?,?,1,?,?,?)', (user['fundacion_id'],asset_type,file.filename,nombre,str(path),file.mimetype or '',path.stat().st_size,user['username'],now,now))
        conn.commit()
        row = conn.execute('SELECT * FROM configuracion_institucional WHERE id=?', (cfg['id'],)).fetchone()
        conn.close()
        _audit(database_path, 'SUBIR_FAVICON_INSTITUCIONAL', 'configuracion_institucional', cfg['id'], {'archivo': nombre, 'tipo': asset_type})
        return jsonify({'message': 'Favicon institucional cargado correctamente.', 'configuracion': _serialize_row(row)}), 200


    @bp.route('/api/identidad-visual/generar', methods=['POST'])
    @require_roles('SUPERADMIN', 'ADMINISTRADOR', 'GERENTE')
    def generar_identidad_visual():
        try:
            file = _require_file('file', ALLOWED_IMAGE_EXTENSIONS, MAX_IMAGE_MB)
            image, raw = _load_source_image(file)
            user = _user()
            directories = _tenant_dirs()
            batch_id = uuid.uuid4().hex[:16]
            version = _branding_version()
            original_name = _safe_filename(f'ORIGINAL_{user["fundacion_id"]}', file.filename)
            (directories['originales_dir'] / original_name).write_bytes(raw)
            remove_white = str(request.form.get('remove_white') or '').lower() in {'1','true','yes','on'}
            warning = None
            if image.width < 512 or image.height < 512:
                warning = f'La imagen original es de {image.width}×{image.height}px; algunas versiones grandes pueden perder nitidez.'
            batch_root = directories['historial_dir'] / batch_id
            generated = _generate_branding_assets(image, batch_root, remove_white)
            zip_path = directories['historial_dir'] / f'identidad_visual_{batch_id}.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                for _, path, _, _ in generated:
                    archive.write(path, path.relative_to(batch_root))
            conn = _connect(database_path)
            for tipo, path, width, height in generated:
                _asset_record(conn, fundacion_id=user['fundacion_id'], tipo=tipo, original=file.filename, path=path, user=user['username'], batch_id=batch_id, width=width, height=height, version=version)
            conn.commit(); conn.close()
            _audit(database_path, 'GENERAR_IDENTIDAD_VISUAL', 'identidad_visual_archivos', None, {'lote_id': batch_id, 'archivos': len(generated)})
            return jsonify({'message': f'Se generaron {len(generated)} recursos correctamente.', 'lote_id': batch_id, 'warning': warning, 'zip_url': f'/api/identidad-visual/lote/{batch_id}/descargar'}), 201
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 400
        except Exception as exc:
            app.logger.exception('Error generando recursos de identidad visual')
            return jsonify({'error': f'No fue posible generar los recursos: {exc}'}), 500

    @bp.route('/api/identidad-visual/lote/<lote_id>/descargar', methods=['GET'])
    def descargar_lote_identidad(lote_id: str):
        if not re.fullmatch(r'[a-f0-9]{16}', lote_id or ''):
            return jsonify({'error': 'Identificador de lote inválido.'}), 400
        path = _tenant_dirs()['historial_dir'] / f'identidad_visual_{lote_id}.zip'
        if not path.exists():
            return jsonify({'error': 'Paquete ZIP no encontrado.'}), 404
        return send_file(path, as_attachment=True, download_name=f'identidad_visual_{lote_id}.zip')

    @bp.route('/api/identidad-visual/lote/<lote_id>/aplicar', methods=['POST'])
    @require_roles('SUPERADMIN', 'ADMINISTRADOR', 'GERENTE')
    def aplicar_lote_identidad(lote_id: str):
        user = _user(); directories = _tenant_dirs(); conn = _connect(database_path)
        rows = conn.execute('SELECT * FROM identidad_visual_archivos WHERE fundacion_id=? AND lote_id=? ORDER BY id', (user['fundacion_id'], lote_id)).fetchall()
        if not rows:
            conn.close(); return jsonify({'error': 'No se encontró el lote solicitado.'}), 404
        preferred = {'logo_principal':'logo_principal.png','logo_horizontal':'logo_header.png','logo_reportes':'logo_pdf.png','logo_documentos':'logo_word.png','favicon_ico':'favicon.ico','favicon_png':'favicon-192x192.png'}
        mapping = {'logo_principal':'logo_principal_path','logo_horizontal':'logo_horizontal_path','logo_reportes':'logo_reportes_path','logo_documentos':'logo_documentos_path','favicon_ico':'favicon_path','favicon_png':'favicon_png_path'}
        chosen = {}
        for row in rows:
            if row['tipo'] in preferred and row['nombre_archivo'] == preferred[row['tipo']]:
                chosen[row['tipo']] = row
        cfg = _institutional_config(user['fundacion_id']); now=_now()
        if not chosen:
            conn.close()
            return jsonify({'error': 'El lote no contiene recursos aplicables.'}), 400
        copied = []
        try:
            for tipo,row in chosen.items():
                active_path = _copy_to_active_storage(row['archivo_path'], directories['branding_root'], tipo, lote_id)
                copied.append(active_path)
                conn.execute('UPDATE identidad_visual_archivos SET activo=0, updated_at=? WHERE fundacion_id=? AND tipo=?', (now,user['fundacion_id'],tipo))
                conn.execute('UPDATE identidad_visual_archivos SET activo=1, archivo_path=?, fecha_aplicacion=?, updated_at=? WHERE id=?', (str(active_path),now,now,row['id']))
                conn.execute(f'UPDATE configuracion_institucional SET {mapping[tipo]}=?, actualizado_por=?, updated_at=? WHERE id=?', (str(active_path),user['username'],now,cfg['id']))
        except FileNotFoundError as exc:
            conn.rollback(); conn.close()
            for path in copied:
                try: path.unlink(missing_ok=True)
                except OSError: pass
            return jsonify({'error': str(exc)}), 404
        conn.commit(); cfg_row=conn.execute('SELECT * FROM configuracion_institucional WHERE id=?',(cfg['id'],)).fetchone(); conn.close()
        _audit(database_path,'APLICAR_LOTE_IDENTIDAD_VISUAL','identidad_visual_archivos',None,{'lote_id':lote_id})
        return jsonify({'message':'Recursos aplicados a toda la plataforma. Recarga el navegador para verlos.', 'configuracion':_serialize_row(cfg_row)}),200

    @bp.route('/api/identidad-visual', methods=['GET'])
    def listar_identidad_visual():
        user = _user()
        conn = _connect(database_path)
        if str(request.args.get('scope') or '').upper() == 'GLOBAL':
            rows = conn.execute('SELECT * FROM identidad_global_archivos ORDER BY tipo ASC, activo DESC, created_at DESC, id DESC').fetchall()
            conn.close()
            archivos = []
            for row in rows:
                item = dict(row)
                item.update({
                    'scope': 'GLOBAL',
                    'nombre_archivo': os.path.basename(str(item.get('storage_key') or '')),
                    'url': _global_asset_url(str(item.get('tipo') or ''), item.get('version')),
                })
                archivos.append(item)
            return jsonify({'scope': 'GLOBAL', 'archivos': archivos}), 200
        rows = conn.execute('SELECT * FROM identidad_visual_archivos WHERE fundacion_id=? ORDER BY tipo ASC, activo DESC, created_at DESC, id DESC', (user['fundacion_id'],)).fetchall()
        conn.close()
        archivos = []
        tenant_root = _tenant_dirs()['root']
        for row in rows:
            item = dict(row)
            item['scope'] = 'FUNDACION'
            item['url'] = _public_path(item.get('archivo_path'), base_dir, tenant_root)
            archivos.append(item)
        return jsonify({'archivos': archivos}), 200

    @bp.route('/api/identidad-visual/<int:archivo_id>/descargar', methods=['GET'])
    def descargar_identidad_visual(archivo_id: int):
        user = _user()
        directories = _tenant_dirs()
        conn = _connect(database_path)
        row = conn.execute('SELECT * FROM identidad_visual_archivos WHERE id=? AND fundacion_id=?', (archivo_id, user['fundacion_id'])).fetchone()
        conn.close()
        if not row:
            return jsonify({'error': 'Archivo de identidad visual no encontrado.'}), 404
        path = os.path.abspath(str(row['archivo_path'] or ''))
        allowed_roots = [
            os.path.abspath(str(directories['logos_dir'])),
            os.path.abspath(str(directories['favicons_dir'])),
            os.path.abspath(str(directories['fotos_dir'])),
            os.path.abspath(str(directories['branding_root'])),
        ]
        if not any(path.startswith(root + os.sep) for root in allowed_roots):
            return jsonify({'error': 'Ruta no autorizada.'}), 403
        if not os.path.exists(path):
            return jsonify({'error': 'El archivo ya no existe en disco.'}), 404
        return send_from_directory(os.path.dirname(path), os.path.basename(path), as_attachment=True, download_name=row['nombre_original'] or row['nombre_archivo'])

    @bp.route('/api/identidad-visual/<int:archivo_id>/activar', methods=['POST'])
    @require_roles('SUPERADMIN', 'ADMINISTRADOR', 'GERENTE')
    def activar_identidad_visual(archivo_id: int):
        user = _user()
        directories = _tenant_dirs()
        conn = _connect(database_path)
        row = conn.execute('SELECT * FROM identidad_visual_archivos WHERE id=? AND fundacion_id=?', (archivo_id, user['fundacion_id'])).fetchone()
        if not row:
            conn.close()
            return jsonify({'error': 'Archivo de identidad visual no encontrado.'}), 404
        mapping = {'logo_principal':'logo_principal_path','logo_horizontal':'logo_horizontal_path','logo_reportes':'logo_reportes_path','logo_formatos':'logo_formatos_path','logo_documentos':'logo_documentos_path','favicon_ico':'favicon_path','favicon_png':'favicon_png_path','foto_admin':'foto_admin_path'}
        col = mapping.get(row['tipo'])
        if not col:
            conn.close()
            return jsonify({'error': 'Tipo de archivo no compatible.'}), 400
        cfg = _institutional_config(user['fundacion_id'])
        now = _now()
        try:
            active_path = _copy_to_active_storage(
                row['archivo_path'],
                directories['branding_root'],
                row['tipo'],
                f'restore-{archivo_id}-{int(datetime.now().timestamp())}',
            )
        except FileNotFoundError as exc:
            conn.close()
            return jsonify({'error': str(exc)}), 404
        conn.execute('UPDATE identidad_visual_archivos SET activo=0, updated_at=? WHERE fundacion_id=? AND tipo=?', (now, user['fundacion_id'], row['tipo']))
        conn.execute('UPDATE identidad_visual_archivos SET activo=1, archivo_path=?, fecha_aplicacion=?, updated_at=? WHERE id=?', (str(active_path), now, now, archivo_id))
        conn.execute(f'UPDATE configuracion_institucional SET {col}=?, actualizado_por=?, updated_at=? WHERE id=?', (str(active_path), user['username'], now, cfg['id']))
        conn.commit()
        cfg_row = conn.execute('SELECT * FROM configuracion_institucional WHERE id=?', (cfg['id'],)).fetchone()
        conn.close()
        _audit(database_path, 'ACTIVAR_IDENTIDAD_VISUAL', 'identidad_visual_archivos', archivo_id, {'tipo': row['tipo']})
        return jsonify({'message': 'Archivo activado correctamente.', 'configuracion': _serialize_row(cfg_row)}), 200

    @bp.route('/api/manual-operativo', methods=['GET'])
    def listar_manuales():
        user = _user()
        conn = _connect(database_path)
        rows = conn.execute('''
            SELECT * FROM manuales_operativos WHERE fundacion_id=? ORDER BY created_at DESC, id DESC
        ''', (user['fundacion_id'],)).fetchall()
        conn.close()
        return jsonify({'manuales': [_serialize_row(row) for row in rows]}), 200

    @bp.route('/api/manual-operativo/vigente', methods=['GET'])
    def manual_vigente():
        user = _user()
        conn = _connect(database_path)
        row = conn.execute('''
            SELECT * FROM manuales_operativos
            WHERE fundacion_id=? AND estado='vigente'
            ORDER BY updated_at DESC, id DESC LIMIT 1
        ''', (user['fundacion_id'],)).fetchone()
        conn.close()
        if not row:
            return jsonify({'manual': None, 'message': 'No hay manual operativo vigente.'}), 200
        return jsonify({'manual': _serialize_manual(row)}), 200

    @bp.route('/api/manual-operativo/cargar', methods=['POST'])
    @require_roles('SUPERADMIN', 'ADMINISTRADOR', 'GERENTE', 'COORDINADOR')
    def cargar_manual():
        try:
            file = _require_file('file', ALLOWED_MANUAL_EXTENSIONS, MAX_MANUAL_MB)
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 400
        user = _user()
        directories = _tenant_dirs()
        codigo = (request.form.get('codigo') or 'MT3.PP').strip()[:80]
        nombre_doc = (request.form.get('nombre') or 'Manual Técnico Modalidad Propia e Intercultural para la Atención a la Primera Infancia').strip()[:240]
        version = (request.form.get('version') or '2').strip()[:40]
        fecha_documento = (request.form.get('fecha_documento') or '2025-12-26').strip()[:30]
        estado = (request.form.get('estado') or 'borrador').strip().lower()
        if estado not in {'vigente', 'borrador', 'historico', 'histórico'}:
            estado = 'borrador'
        if estado == 'histórico':
            estado = 'historico'
        nombre = _safe_filename(f'MANUAL_{codigo.replace(".", "_")}_{user["fundacion_id"]}', file.filename)
        path = directories['manuales_dir'] / nombre
        file.save(path)
        total_paginas = _count_pdf_pages(str(path))
        conn = _connect(database_path)
        now = _now()
        if estado == 'vigente':
            conn.execute("UPDATE manuales_operativos SET estado='historico', updated_at=? WHERE fundacion_id=? AND estado='vigente'", (now, user['fundacion_id']))
        insert_cursor = conn.execute('''
            INSERT INTO manuales_operativos
            (corporacion_id, fundacion_id, codigo, nombre, version, fecha_documento, estado, archivo_path, total_paginas, observacion, cargado_por, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user['corporacion_id'], user['fundacion_id'], codigo, nombre_doc, version, fecha_documento, estado, str(path), total_paginas, request.form.get('observacion') or '', user['username'], now, now))
        manual_id = insert_cursor.lastrowid
        for order, (titulo, numero, inicio, fin) in enumerate(SECCIONES_MANUAL_BASE, start=1):
            conn.execute('''
                INSERT INTO manuales_operativos_secciones
                (manual_id, titulo, numero, pagina_inicio, pagina_fin, orden, resumen, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (manual_id, titulo, numero, inicio, fin, order, f'Sección base identificada para {titulo}.', now))
        conn.commit()
        row = conn.execute('SELECT * FROM manuales_operativos WHERE id=?', (manual_id,)).fetchone()
        conn.close()
        _audit(database_path, 'CARGAR_MANUAL_OPERATIVO', 'manuales_operativos', manual_id, {'codigo': codigo, 'version': version, 'estado': estado, 'archivo': nombre})
        return jsonify({'message': 'Manual operativo cargado correctamente.', 'manual': _serialize_manual(row)}), 201

    @bp.route('/api/manual-operativo/<int:manual_id>', methods=['GET'])
    def obtener_manual(manual_id: int):
        user = _user()
        conn = _connect(database_path)
        row = conn.execute('SELECT * FROM manuales_operativos WHERE id=? AND fundacion_id=?', (manual_id, user['fundacion_id'])).fetchone()
        conn.close()
        if not row:
            return jsonify({'error': 'Manual operativo no encontrado.'}), 404
        return jsonify({'manual': _serialize_manual(row)}), 200

    @bp.route('/api/manual-operativo/<int:manual_id>/vigente', methods=['POST'])
    @require_roles('SUPERADMIN', 'ADMINISTRADOR', 'GERENTE')
    def marcar_vigente(manual_id: int):
        user = _user()
        conn = _connect(database_path)
        row = conn.execute('SELECT * FROM manuales_operativos WHERE id=? AND fundacion_id=?', (manual_id, user['fundacion_id'])).fetchone()
        if not row:
            conn.close()
            return jsonify({'error': 'Manual operativo no encontrado.'}), 404
        now = _now()
        conn.execute("UPDATE manuales_operativos SET estado='historico', updated_at=? WHERE fundacion_id=? AND estado='vigente' AND id<>?", (now, user['fundacion_id'], manual_id))
        conn.execute("UPDATE manuales_operativos SET estado='vigente', updated_at=? WHERE id=?", (now, manual_id))
        conn.commit()
        row = conn.execute('SELECT * FROM manuales_operativos WHERE id=?', (manual_id,)).fetchone()
        conn.close()
        _audit(database_path, 'MARCAR_MANUAL_VIGENTE', 'manuales_operativos', manual_id, {'codigo': row['codigo'], 'version': row['version']})
        return jsonify({'message': 'Manual operativo marcado como vigente.', 'manual': _serialize_manual(row)}), 200

    @bp.route('/api/manual-operativo/<int:manual_id>/descargar', methods=['GET'])
    def descargar_manual(manual_id: int):
        user = _user()
        directories = _tenant_dirs()
        conn = _connect(database_path)
        row = conn.execute('SELECT * FROM manuales_operativos WHERE id=? AND fundacion_id=?', (manual_id, user['fundacion_id'])).fetchone()
        conn.close()
        if not row:
            return jsonify({'error': 'Manual operativo no encontrado.'}), 404
        path = os.path.abspath(str(row['archivo_path'] or ''))
        allowed_root = os.path.abspath(str(directories['manuales_dir']))
        if not path.startswith(allowed_root + os.sep):
            return jsonify({'error': 'Ruta de manual no autorizada.'}), 403
        if not os.path.exists(path):
            return jsonify({'error': 'El archivo del manual ya no existe en disco.'}), 404
        return send_from_directory(os.path.dirname(path), os.path.basename(path), as_attachment=True)

    app.register_blueprint(bp)
