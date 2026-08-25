from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

from services.uds_catalog import aliases_lower as catalog_aliases_lower, normalize_unit as catalog_normalize_unit

try:
    from flask import g
except Exception:  # pragma: no cover
    g = None

from .repository import TalentoHumanoRepository, safe_json


def limpiar_valor(value: Any, default: str = '') -> str:
    if value is None:
        return default
    text = str(value).strip()
    if text.lower() in {'nan', 'nat', 'none', 'null'}:
        return default
    return text


def limpiar_documento(value: Any, default: str = '') -> str:
    text = limpiar_valor(value, default)
    if re.fullmatch(r'\d+\.0+', text):
        return text.split('.')[0]
    return text


def unir_valores(*values: Any) -> str:
    return ' '.join([limpiar_valor(v) for v in values if limpiar_valor(v)]).strip()


def normalizar_texto(value: Any) -> str:
    text = str(value or '').strip().lower()
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r'[^a-z0-9]+', ' ', text)
    return ' '.join(text.split())


UNIDAD_ALIASES = catalog_aliases_lower()


def normalizar_unidad(value: Any) -> str:
    return catalog_normalize_unit(value, preserve_unknown=True)


def dividir_nombre(nombre: str) -> tuple[str, str]:
    partes = [p for p in limpiar_valor(nombre).split() if p]
    if not partes:
        return '', ''
    if len(partes) == 1:
        return partes[0], ''
    mitad = max(1, len(partes) // 2)
    return ' '.join(partes[:mitad]), ' '.join(partes[mitad:])


def normalizar_rol(row: dict[str, Any]) -> str:
    texto = normalizar_texto(' '.join([
        limpiar_valor(row.get('tipo_equipo')),
        limpiar_valor(row.get('cargo')),
        limpiar_valor(row.get('perfil')),
        limpiar_valor(row.get('rol')),
    ]))
    if 'coordin' in texto:
        return 'COORDINADOR'
    if 'psicosocial' in texto or 'psicolog' in texto or 'trabajador social' in texto:
        return 'PSICOSOCIAL'
    if 'nutricion' in texto or 'nutricionista' in texto:
        return 'NUTRICIONISTA'
    if 'enfermer' in texto or 'salud' in texto:
        return 'ENFERMERIA'
    if 'pedagog' in texto:
        return 'PEDAGOGIA'
    if 'administr' in texto or 'auxiliar' in texto:
        return 'ADMINISTRATIVO'
    if 'docente' in texto or 'agente educativo' in texto or 'agente' in texto:
        return 'DOCENTE'
    return 'APOYO'


def normalizar_registro(data: dict[str, Any], archivo: str = 'manual') -> dict[str, Any]:
    nombre = limpiar_valor(
        data.get('nombre') or data.get('nombres_y_apellidos') or data.get('NOMBRES Y APELLIDOS')
        or data.get('funcionario') or data.get('talento_humano')
        or unir_valores(
            data.get('primer_nombre') or data.get('Primer Nombre'),
            data.get('segundo_nombre') or data.get('Segundo Nombre'),
            data.get('primer_apellido') or data.get('Primer Apellido'),
            data.get('segundo_apellido') or data.get('Segundo Apellido'),
        )
    ).upper()
    documento = limpiar_documento(
        data.get('documento') or data.get('cedula') or data.get('cédula') or data.get('CEDULA')
        or data.get('numero_documento') or data.get('Número de Documento') or data.get('Numero de Documento')
        or data.get('identificacion') or data.get('identificación') or data.get('no_documento')
    )
    cargo = limpiar_valor(data.get('cargo') or data.get('CARGO') or data.get('Cargo') or data.get('perfil') or data.get('rol') or 'AGENTE EDUCATIVO').upper()
    unidad = normalizar_unidad(
        data.get('unidad') or data.get('Nombre UDS') or data.get('nombre_uds')
        or data.get('comunidad') or data.get('COMUNIDAD') or data.get('uca')
        or data.get('unidad_servicio') or data.get('direccion')
    )
    direccion = limpiar_valor(data.get('direccion') or data.get('Dirección de Residencia') or data.get('DIRECCION') or data.get('ubicacion') or unidad)
    telefono = limpiar_documento(data.get('telefono') or data.get('Número de Teléfono') or data.get('Numero de Telefono') or data.get('TELEFONO') or data.get('celular') or data.get('contacto'))
    coordinador = limpiar_valor(data.get('coordinador') or data.get('coordinador_responsable') or data.get('jefe_inmediato') or data.get('responsable')).upper()
    tipo_equipo = limpiar_valor(data.get('tipo_equipo') or data.get('tipo') or data.get('equipo') or data.get('TIPO EQUIPO')).upper()
    contrato = limpiar_valor(data.get('contrato') or data.get('CONTRATO') or data.get('numero_contrato') or data.get('Número Contrato') or data.get('Numero Contrato'))
    perfil = limpiar_valor(data.get('perfil') or data.get('PERFIL') or data.get('profesion') or data.get('PROFESION') or data.get('Título Obtenido de Educación Superior') or data.get('Titulo Obtenido de Educacion Superior'))
    estado = limpiar_valor(data.get('estado') or data.get('Estado de vinculación') or data.get('Estado de vinculacion') or 'activo').lower() or 'activo'
    nombres, apellidos = dividir_nombre(nombre)
    if not tipo_equipo:
        tipo_equipo = normalizar_rol({'cargo': cargo, 'perfil': perfil})
    return {
        'documento': documento,
        'nombre': nombre,
        'nombres': nombres,
        'apellidos': apellidos,
        'cargo': cargo,
        'unidad': unidad,
        'unidades': json.dumps([unidad], ensure_ascii=False) if unidad else json.dumps([], ensure_ascii=False),
        'direccion': direccion,
        'telefono': telefono,
        'coordinador': coordinador,
        'tipo_equipo': tipo_equipo,
        'contrato': contrato,
        'perfil': perfil,
        'estado': estado,
        'activo': 0 if estado in {'inactivo', 'eliminado', 'retirado'} else 1,
        'archivo': archivo,
    }


def unidades_de_row(row: dict[str, Any]) -> list[str]:
    unidades = set()
    unidad = normalizar_unidad(row.get('unidad'))
    if unidad:
        unidades.add(unidad)
    raw = limpiar_valor(row.get('unidades'))
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                unidades.update(normalizar_unidad(x) for x in parsed if normalizar_unidad(x))
            elif isinstance(parsed, str):
                unidades.add(normalizar_unidad(parsed))
        except Exception:
            unidades.update(normalizar_unidad(x) for x in re.split(r'[,;/|]+', raw) if normalizar_unidad(x))
    return sorted(unidades)


class TalentoHumanoService:
    def __init__(self, repository: TalentoHumanoRepository | None = None):
        self.repo = repository or TalentoHumanoRepository()

    def context(self) -> dict[str, Any]:
        user = {}
        try:
            user = getattr(g, 'current_user', None) or {}
        except Exception:
            user = {}
        return {
            'usuario_id': user.get('id'),
            'fundacion_id': user.get('fundacion_id') or 1,
            'rol': user.get('rol') or 'SUPERADMIN',
            'username': user.get('username') or user.get('email') or 'sistema',
        }

    def list_talento(self) -> list[dict[str, Any]]:
        ctx = self.context()
        return self.repo.list_talento(ctx.get('fundacion_id'), ctx.get('rol') == 'SUPERADMIN')

    def integral_dashboard(self) -> dict[str, Any]:
        ctx=self.context(); return self.repo.integral_dashboard(int(ctx.get('fundacion_id') or 1))

    def integral_person(self, person_id: int) -> dict[str, Any] | None:
        ctx=self.context(); return self.repo.integral_person(person_id,int(ctx.get('fundacion_id') or 1))

    def integral_add(self, entity: str, payload: dict[str, Any]) -> dict[str, Any]:
        ctx=self.context(); self.repo.integral_add(entity,payload,ctx); return self.integral_dashboard()

    def guardar_registros(self, registros: list[dict[str, Any]], origen: str = 'guardar_registros_talento') -> dict[str, Any]:
        ctx = self.context()
        normalizados = []
        for reg in registros:
            if not reg:
                continue
            if 'nombres' not in reg or 'apellidos' not in reg:
                reg = normalizar_registro(reg, reg.get('archivo') or origen)
            normalizados.append(reg)
        resultado = self.repo.save_base_records(normalizados, ctx)
        sync = self.sincronizar_global(origen=origen)
        resultado['sincronizacion'] = sync
        return resultado

    def update_talento(self, talento_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        ctx = self.context()
        registro = normalizar_registro(data, data.get('archivo') or 'manual')
        actualizado = self.repo.update_base_record(talento_id, registro, ctx)
        if actualizado:
            self.sincronizar_global(origen='editar_talento')
        return actualizado

    def delete_talento(self, talento_id: int, hard: bool = False) -> bool:
        ctx = self.context()
        ok = self.repo.hard_delete_base_record(talento_id, ctx) if hard else self.repo.deactivate_base_record(talento_id, ctx)
        if ok:
            self.sincronizar_global(origen='eliminar_talento' if hard else 'desactivar_talento')
        return ok

    def sincronizar_global(self, origen: str = 'manual', fuente: str = 'operativa', ctx_override: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = {**self.context(), **(ctx_override or {})}
        self.repo.init_schema()
        fuente_normalizada = str(fuente or 'operativa').strip().lower()
        if fuente_normalizada == 'base_maestra':
            filas = self.repo.list_master_talento(int(ctx.get('fundacion_id') or 1))
        else:
            filas = self.repo.list_talento(ctx.get('fundacion_id'), ctx.get('rol') == 'SUPERADMIN')
        resultado = {
            'origen': origen,
            'fuente': 'master_talento_humano' if fuente_normalizada == 'base_maestra' else 'coordinadores',
            'talento_base': len(filas),
            'coordinadores_creados': 0,
            'coordinadores_actualizados': 0,
            'docentes_creados': 0,
            'docentes_actualizados': 0,
            'equipos_creados': 0,
            'equipos_actualizados': 0,
            'asignaciones_creadas': 0,
            'asignaciones_actualizadas': 0,
            'unidades_asignadas_creadas': 0,
            'unidades_actualizadas': 0,
            'beneficiarios_actualizados': 0,
            'usuarios_actualizados': 0,
            'th_personas_creadas': 0,
            'th_personas_actualizadas': 0,
            'th_asignaciones_creadas': 0,
            'th_asignaciones_actualizadas': 0,
        }

        coord_cache: dict[str, int] = {}
        coord_nombre_por_id: dict[int, str] = {}
        coord_por_unidad: dict[str, tuple[int, str]] = {}

        # Primer pase: coordinadores explícitos.
        for row in filas:
            rol = normalizar_rol(row)
            fundacion_id = int(row.get('fundacion_id') or ctx.get('fundacion_id') or 1)
            persona_id, persona_nueva = self.repo.upsert_th_persona(row, rol, ctx)
            if persona_nueva:
                resultado['th_personas_creadas'] += 1
            else:
                resultado['th_personas_actualizadas'] += 1
            if rol != 'COORDINADOR':
                continue
            coord_id, nuevo = self.repo.upsert_gp_coordinador(row, fundacion_id, ctx)
            if coord_id:
                coord_nombre_por_id[coord_id] = row.get('nombre') or ''
                coord_cache[normalizar_texto(row.get('nombre'))] = coord_id
                if row.get('documento'):
                    coord_cache[str(row.get('documento')).strip()] = coord_id
                for unidad in unidades_de_row(row):
                    coord_por_unidad[normalizar_texto(unidad)] = (coord_id, row.get('nombre') or '')
                    if self.repo.upsert_unidad_asignada(coord_id, unidad, fundacion_id, ctx):
                        resultado['unidades_asignadas_creadas'] += 1
            if nuevo:
                resultado['coordinadores_creados'] += 1
            else:
                resultado['coordinadores_actualizados'] += 1

        # Segundo pase: coordinadores referenciados por nombre.
        for row in filas:
            coord_nombre = limpiar_valor(row.get('coordinador')).upper()
            if not coord_nombre:
                continue
            key = normalizar_texto(coord_nombre)
            if key in coord_cache:
                continue
            fundacion_id = int(row.get('fundacion_id') or ctx.get('fundacion_id') or 1)
            coord_id = self.repo.find_gp_coordinador(coord_nombre, '', row.get('contrato') or '', fundacion_id)
            if not coord_id:
                coord_id, nuevo = self.repo.upsert_gp_coordinador(row, fundacion_id, ctx, placeholder_name=coord_nombre)
                if nuevo:
                    resultado['coordinadores_creados'] += 1
                else:
                    resultado['coordinadores_actualizados'] += 1
            if coord_id:
                coord_cache[key] = coord_id

        def resolver_coordinador(row: dict[str, Any], fundacion_id: int) -> tuple[int | None, str]:
            coord_nombre = limpiar_valor(row.get('coordinador')).upper()
            if coord_nombre and normalizar_texto(coord_nombre) in coord_cache:
                cid = coord_cache[normalizar_texto(coord_nombre)]
                return cid, coord_nombre or coord_nombre_por_id.get(cid, '')
            if coord_nombre:
                cid = self.repo.find_gp_coordinador(coord_nombre, '', row.get('contrato') or '', fundacion_id)
                if cid:
                    return cid, coord_nombre or coord_nombre_por_id.get(cid, '')

            # Bases ICBF Talento Humano UDS no siempre traen una columna de
            # coordinador responsable. En ese caso se infiere por Nombre UDS:
            # primero se indexan los coordinadores explícitos por sus unidades
            # y luego cada docente/equipo toma el coordinador de su misma UDS.
            for unidad in unidades_de_row(row):
                asignado = coord_por_unidad.get(normalizar_texto(unidad))
                if asignado:
                    return asignado

            ids_unicos = set(coord_cache.values())
            if len(ids_unicos) == 1:
                cid = next(iter(ids_unicos))
                return cid, coord_nombre_por_id.get(cid, coord_nombre)
            return None, coord_nombre

        # Tercer pase: docentes, equipo, asignaciones y unidades.
        for row in filas:
            rol = normalizar_rol(row)
            fundacion_id = int(row.get('fundacion_id') or ctx.get('fundacion_id') or 1)
            persona_id, _ = self.repo.upsert_th_persona(row, rol, ctx)
            coord_id, coord_nombre = resolver_coordinador(row, fundacion_id)
            if self.repo.upsert_th_asignacion(persona_id, row, coord_id, coord_nombre, rol, fundacion_id, ctx):
                resultado['th_asignaciones_creadas'] += 1
            else:
                resultado['th_asignaciones_actualizadas'] += 1

            if rol == 'COORDINADOR':
                continue
            if rol == 'DOCENTE':
                _, nuevo = self.repo.upsert_gp_docente(row, coord_id, fundacion_id, ctx)
                if nuevo:
                    resultado['docentes_creados'] += 1
                else:
                    resultado['docentes_actualizados'] += 1
                for unidad in unidades_de_row(row):
                    resultado['unidades_actualizadas'] += self.repo.update_unidad_docente(unidad, row, coord_nombre, fundacion_id)
                    op = self.repo.update_docente_in_operacion(unidad, row.get('nombre') or '', fundacion_id)
                    resultado['beneficiarios_actualizados'] += op.get('beneficiarios', 0)
                    resultado['usuarios_actualizados'] += op.get('usuarios', 0)
                    if coord_id and self.repo.upsert_unidad_asignada(coord_id, unidad, fundacion_id, ctx):
                        resultado['unidades_asignadas_creadas'] += 1
            else:
                _, nuevo = self.repo.upsert_gp_equipo(row, coord_id, rol, fundacion_id, ctx)
                if nuevo:
                    resultado['equipos_creados'] += 1
                else:
                    resultado['equipos_actualizados'] += 1

            if self.repo.upsert_gp_asignacion(row, coord_id, rol, fundacion_id, ctx):
                resultado['asignaciones_creadas'] += 1
            else:
                resultado['asignaciones_actualizadas'] += 1

        self.repo.log_sync(resultado, ctx, origen)
        try:
            self.repo.execute(
                """
                INSERT INTO gp_historial_acciones
                (usuario, accion, entidad_tipo, entidad_id, datos_nuevos, fecha_accion, fundacion_id, usuario_creador_id)
                VALUES (?, 'SINCRONIZAR_TALENTO_GLOBAL', 'talento_humano', NULL, ?, ?, ?, ?)
                """,
                [
                    ctx.get('username') or 'sistema',
                    safe_json(resultado),
                    __import__('datetime').datetime.now().isoformat(timespec='seconds'),
                    ctx.get('fundacion_id') or 1,
                    ctx.get('usuario_id'),
                ],
            )
        except Exception:
            pass
        return resultado

    def resumen_integracion(self) -> dict[str, Any]:
        ctx = self.context()
        fundacion_id = ctx.get('fundacion_id') or 1
        superadmin = ctx.get('rol') == 'SUPERADMIN'
        filtro = "1=1" if superadmin else "(fundacion_id = ? OR fundacion_id IS NULL)"
        params = [] if superadmin else [fundacion_id]

        def count(table: str, extra: str = '') -> int:
            try:
                where = filtro
                if extra:
                    where = f"({where}) AND ({extra})"
                row = self.repo.fetch_one(f"SELECT COUNT(*) AS total FROM {table} WHERE {where}", params)
                return int(row['total']) if row else 0
            except Exception:
                return 0

        resumen = {
            'talento_base': count('coordinadores', 'COALESCE(activo,1)=1'),
            'gp_coordinadores': count('gp_coordinadores', 'COALESCE(activo,1)=1'),
            # Claves históricas: se conservan para no romper frontend ni módulos.
            'gp_docentes': count('gp_docentes', 'COALESCE(activo,1)=1'),
            'gp_equipo': count('gp_equipos_interdisciplinarios', 'COALESCE(activo,1)=1'),
            'gp_asignaciones': count('gp_asignaciones_coordinador', "COALESCE(estado,'ACTIVO')='ACTIVO'"),
            'th_personas': count('th_personas', 'COALESCE(activo,1)=1'),
            'th_asignaciones': count('th_asignaciones', "COALESCE(estado,'ACTIVO')='ACTIVO'"),
            'th_docentes': count('th_personas', "rol_normalizado='DOCENTE' AND COALESCE(activo,1)=1"),
            'th_coordinadores': count('th_personas', "rol_normalizado='COORDINADOR' AND COALESCE(activo,1)=1"),
            'th_equipo': count('th_personas', "rol_normalizado NOT IN ('DOCENTE','COORDINADOR') AND COALESCE(activo,1)=1"),
            # Claves nuevas de presentación: en ICBF la figura operativa se llama Agente Educativo.
            'gp_agentes_educativos': count('gp_docentes', 'COALESCE(activo,1)=1'),
            'th_agentes_educativos': count('th_personas', "rol_normalizado='DOCENTE' AND COALESCE(activo,1)=1"),
            'th_psicosocial': count('th_personas', "rol_normalizado='PSICOSOCIAL' AND COALESCE(activo,1)=1"),
            'th_enfermeria': count('th_personas', "rol_normalizado='ENFERMERIA' AND COALESCE(activo,1)=1"),
            'th_nutricionistas': count('th_personas', "rol_normalizado='NUTRICIONISTA' AND COALESCE(activo,1)=1"),
            'th_pedagogia': count('th_personas', "rol_normalizado='PEDAGOGIA' AND COALESCE(activo,1)=1"),
            'th_administrativo': count('th_personas', "rol_normalizado='ADMINISTRATIVO' AND COALESCE(activo,1)=1"),
            'th_apoyo': count('th_personas', "rol_normalizado='APOYO' AND COALESCE(activo,1)=1"),
            'unidades_con_docente': 0,
            'unidades_con_agente_educativo': 0,
            'ultimo_evento': None,
            'th_ultimo_evento': None,
        }
        try:
            row = self.repo.fetch_one("SELECT COUNT(*) AS total FROM unidades WHERE COALESCE(docente_asignado,'') != ''")
            total_unidades_con_agente = int(row['total']) if row else 0
            resumen['unidades_con_docente'] = total_unidades_con_agente
            resumen['unidades_con_agente_educativo'] = total_unidades_con_agente
        except Exception:
            pass
        try:
            resumen['th_ultimo_evento'] = self.repo.latest_sync()
            resumen['ultimo_evento'] = resumen['th_ultimo_evento']
        except Exception:
            pass
        return resumen

    def fuente_maestra(self) -> dict[str, Any]:
        ctx = self.context()
        fundacion_id = int(ctx.get('fundacion_id') or 1)
        allow_global = (
            ctx.get('rol') == 'SUPERADMIN'
            and bool(getattr(g, 'allow_global_tenant_access', False))
        )
        filtro_personas = "1=1" if allow_global else "COALESCE(fundacion_id, 1) = ?"
        params_personas = [] if allow_global else [fundacion_id]
        personas = self.repo.fetch_all(
            f"""
            SELECT id, documento, nombre, cargo, tipo_equipo, rol_normalizado, unidad,
                   telefono, coordinador, contrato, estado, activo, fecha_actualizacion
            FROM th_personas
            WHERE {filtro_personas}
            ORDER BY rol_normalizado, unidad, nombre
            """,
            params_personas,
        )
        if allow_global:
            join_personas = 'p.id = a.persona_id'
            filtro_asignaciones = '1=1'
            params_asignaciones: list[Any] = []
        else:
            join_personas = 'p.id = a.persona_id AND COALESCE(p.fundacion_id, 1) = ?'
            filtro_asignaciones = 'COALESCE(a.fundacion_id, 1) = ?'
            params_asignaciones = [fundacion_id, fundacion_id]
        asignaciones = self.repo.fetch_all(
            f"""
            SELECT a.id, a.persona_id, p.nombre, p.documento, a.rol, a.unidad,
                   a.coordinador_id, a.coordinador_nombre, a.estado, a.fecha_actualizacion
            FROM th_asignaciones a
            LEFT JOIN th_personas p ON {join_personas}
            WHERE {filtro_asignaciones}
            ORDER BY a.unidad, a.rol, p.nombre
            """,
            params_asignaciones,
        )
        return {'resumen': self.resumen_integracion(), 'personas': personas, 'asignaciones': asignaciones}
