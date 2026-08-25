"""
Repositorio del módulo Salud y Nutrición Inteligente.

Fase 2C.8:
- Reemplaza conexiones sqlite3 directas por SQLAlchemy Core transicional.
- Conserva compatibilidad con consultas históricas de placeholders ?.
- Formaliza historial nutricional, BOA, diagnósticos, alertas,
  seguimientos trimestrales y calendario nutricional.
"""
from __future__ import annotations

import json
from typing import Any, Iterable

from modules.sqlalchemy_compat import CoreCompatRepository
from modules.seguridad.tenant_context import current_tenant_context
from .schema import SCHEMA_SQL
from .services import now_iso


def _security_context() -> dict:
    try:
        from modules.seguridad.services import get_request_user_context
        return get_request_user_context()
    except Exception:
        return {'fundacion_id': 1, 'usuario_id': None, 'rol': 'SUPERADMIN', 'username': 'sistema'}


def _is_superadmin() -> bool:
    return str(_security_context().get('rol') or '').upper() == 'SUPERADMIN'


def _allow_global() -> bool:
    context = current_tenant_context()
    return context.role == 'SUPERADMIN' and bool(context.allow_global)


def _ctx_fundacion_id() -> int:
    try:
        return int(_security_context().get('fundacion_id') or 1)
    except Exception:
        return 1


def _ctx_usuario_id() -> int | None:
    try:
        uid = _security_context().get('usuario_id')
        return int(uid) if uid is not None and uid != '' else None
    except Exception:
        return None


def _scope_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if _allow_global():
        return rows
    fid = _ctx_fundacion_id()
    return [row for row in rows if row.get('fundacion_id') in (fid, None, '')]


class SaludNutricionRepository(CoreCompatRepository):
    def __init__(self, database_path: str | None = None):
        self.database_path = database_path

    def init_schema(self) -> None:
        self.execute_script(SCHEMA_SQL)

        # Compatibilidad incremental para bases creadas en versiones anteriores.
        for table in (
            'sn_valoraciones', 'sn_alertas', 'sn_cargas', 'sn_comparaciones',
            'sn_calendario', 'sn_adjuntos', 'sn_historial_acciones', 'sn_referencias_oms'
        ):
            if self.table_exists(table):
                self.ensure_column(table, 'fundacion_id', 'INTEGER DEFAULT 1')
                self.ensure_column(table, 'usuario_creador_id', 'INTEGER')
                self.ensure_column(table, 'fecha_actualizacion', 'TEXT')

        # Columnas históricas específicas.
        if self.table_exists('sn_valoraciones'):
            self.ensure_column('sn_valoraciones', 'usuario_carga', "TEXT DEFAULT 'sistema'")
            self.ensure_column('sn_valoraciones', 'observaciones', "TEXT")
        if self.table_exists('sn_alertas'):
            self.ensure_column('sn_alertas', 'atendida', "INTEGER DEFAULT 0")
        if self.table_exists('peso_talla'):
            for column, definition in {
                'documento': 'TEXT',
                'nombre': 'TEXT',
                'unidad': 'TEXT',
                'fecha_toma': 'TEXT',
                'estado': 'TEXT',
                'fecha_medicion': 'TEXT',
                'responsable': 'TEXT',
                'estado_nutricional': "TEXT DEFAULT 'PENDIENTE'",
                'fecha_proximo_control': 'TEXT',
                'fecha_carga': 'TEXT',
                'fundacion_id': 'INTEGER DEFAULT 1',
                'usuario_creador_id': 'INTEGER',
                'fecha_actualizacion': 'TEXT',
            }.items():
                self.ensure_column('peso_talla', column, definition)

    def fetch_all(self, sql: str, params: Iterable[Any] | None = None) -> list[dict[str, Any]]:
        return _scope_rows(super().fetch_all(sql, params))

    def fetch_one(self, sql: str, params: Iterable[Any] | None = None) -> dict[str, Any] | None:
        rows = self.fetch_all(sql, params)
        return rows[0] if rows else None

    def _insert_with_context(self, table: str, campos: list[str], row: dict[str, Any]) -> int:
        if 'fundacion_id' in self.columns(table) and 'fundacion_id' not in campos:
            campos.append('fundacion_id')
            row['fundacion_id'] = _ctx_fundacion_id()
        if 'usuario_creador_id' in self.columns(table) and 'usuario_creador_id' not in campos:
            campos.append('usuario_creador_id')
            row['usuario_creador_id'] = _ctx_usuario_id()
        if 'fecha_actualizacion' in self.columns(table) and 'fecha_actualizacion' not in campos:
            campos.append('fecha_actualizacion')
            row['fecha_actualizacion'] = now_iso()

        placeholders = ', '.join(['?'] * len(campos))
        sql = f"INSERT INTO {table} ({', '.join(campos)}) VALUES ({placeholders})"
        new_id = super().execute(sql, [row.get(campo) for campo in campos])
        if not new_id:
            # Fallback compatible con SQLAlchemy/SQLite cuando lastrowid no se propaga.
            latest = super().fetch_one(f"SELECT id FROM {table} ORDER BY id DESC LIMIT 1")
            new_id = int((latest or {}).get('id') or 0)
        return new_id

    def log(self, accion: str, entidad_tipo: str = '', entidad_id: int | None = None,
            documento: str = '', usuario: str = 'sistema', anteriores: Any = None, nuevos: Any = None) -> None:
        campos = [
            'usuario', 'accion', 'entidad_tipo', 'entidad_id', 'documento',
            'datos_anteriores', 'datos_nuevos', 'fecha_accion'
        ]
        row = {
            'usuario': usuario,
            'accion': accion,
            'entidad_tipo': entidad_tipo,
            'entidad_id': entidad_id,
            'documento': documento,
            'datos_anteriores': json.dumps(anteriores, ensure_ascii=False) if anteriores is not None else None,
            'datos_nuevos': json.dumps(nuevos, ensure_ascii=False) if nuevos is not None else None,
            'fecha_accion': now_iso(),
        }
        self._insert_with_context('sn_historial_acciones', campos, row)

    def guardar_valoracion(self, data: dict[str, Any], fuente_archivo: str = '', usuario: str = 'sistema') -> int:
        campos = [
            'tipo_documento', 'documento', 'nui', 'nombre_completo', 'fecha_nacimiento',
            'edad_meses', 'edad_texto', 'sexo', 'unidad', 'docente', 'acudiente', 'telefono',
            'direccion', 'fecha_valoracion', 'peso_kg', 'talla_cm', 'imc',
            'perimetro_braquial_cm', 'perimetro_cefalico_cm',
            'z_peso_edad', 'z_talla_edad', 'z_peso_talla', 'z_imc_edad', 'z_braquial_edad',
            'diag_peso_edad', 'diag_talla_edad', 'diag_peso_talla', 'diag_imc_edad',
            'diag_braquial_edad', 'diagnostico_global', 'nivel_alerta', 'estado_control',
            'trimestre', 'periodo', 'proximo_control', 'fuente_archivo', 'observaciones',
            'activo', 'fecha_carga', 'usuario_carga'
        ]
        row = {campo: data.get(campo) for campo in campos}
        row['fuente_archivo'] = fuente_archivo
        row['activo'] = 1
        row['fecha_carga'] = now_iso()
        row['usuario_carga'] = usuario
        valoracion_id = self._insert_with_context('sn_valoraciones', list(campos), row)

        # Mantener tabla histórica peso_talla alimentada para compatibilidad con módulos anteriores.
        self.sincronizar_peso_talla_desde_valoracion(valoracion_id, row)
        self.programar_seguimiento_trimestral(valoracion_id, row)
        return valoracion_id

    def sincronizar_peso_talla_desde_valoracion(self, valoracion_id: int, row: dict[str, Any]) -> None:
        if not self.table_exists('peso_talla'):
            return
        benef = self.fetch_one(
            """SELECT id FROM beneficiarios
               WHERE (documento = ? OR nui = ?)
                 AND COALESCE(fundacion_id,1)=?
               ORDER BY id DESC LIMIT 1""",
            (row.get('documento'), row.get('documento'), _ctx_fundacion_id())
        ) or {}
        campos = [
            'beneficiario_id', 'documento', 'nombre', 'unidad', 'peso', 'talla',
            'fecha_toma', 'estado', 'fecha_medicion', 'responsable',
            'estado_nutricional', 'fecha_proximo_control', 'fecha_carga'
        ]
        estado = row.get('estado_control') or 'Pendiente'
        data = {
            # NULL conserva la medición por documento cuando no existe una
            # proyección histórica; 0 rompe la FK o enlaza datos incorrectos.
            'beneficiario_id': benef.get('id'),
            'documento': row.get('documento'),
            'nombre': row.get('nombre_completo'),
            'unidad': row.get('unidad'),
            'peso': row.get('peso_kg'),
            'talla': row.get('talla_cm'),
            'fecha_toma': row.get('fecha_valoracion'),
            'estado': str(estado).lower().replace(' ', '_'),
            'fecha_medicion': row.get('fecha_valoracion'),
            'responsable': row.get('docente') or row.get('usuario_carga') or 'sistema',
            'estado_nutricional': row.get('diagnostico_global') or 'Pendiente',
            'fecha_proximo_control': row.get('proximo_control'),
            'fecha_carga': now_iso(),
        }
        self._insert_with_context('peso_talla', campos, data)

    def programar_seguimiento_trimestral(self, valoracion_id: int, row: dict[str, Any]) -> None:
        if not self.table_exists('sn_calendario') or not row.get('proximo_control'):
            return
        campos = [
            'documento', 'valoracion_id', 'tipo_evento', 'fecha_programada', 'estado',
            'nivel', 'unidad', 'responsable', 'descripcion', 'fecha_creacion'
        ]
        nivel = row.get('nivel_alerta') or 'VERDE'
        estado = 'PENDIENTE' if nivel in {'ROJO', 'AMARILLO'} else 'PROGRAMADO'
        descripcion = f"Control nutricional trimestral · {row.get('diagnostico_global') or 'Pendiente'}"
        data = {
            'documento': row.get('documento'),
            'valoracion_id': valoracion_id,
            'tipo_evento': 'SEGUIMIENTO_TRIMESTRAL',
            'fecha_programada': row.get('proximo_control'),
            'estado': estado,
            'nivel': nivel,
            'unidad': row.get('unidad'),
            'responsable': row.get('docente') or row.get('usuario_carga') or '',
            'descripcion': descripcion,
            'fecha_creacion': now_iso(),
        }
        self._insert_with_context('sn_calendario', campos, data)

    def ultima_valoracion(self, documento: str, excluir_id: int | None = None) -> dict[str, Any] | None:
        if excluir_id:
            return self.fetch_one(
                """
                SELECT * FROM sn_valoraciones
                WHERE documento = ? AND id != ? AND activo = 1
                ORDER BY fecha_valoracion DESC, id DESC
                LIMIT 1
                """,
                (documento, excluir_id),
            )
        return self.fetch_one(
            """
            SELECT * FROM sn_valoraciones
            WHERE documento = ? AND activo = 1
            ORDER BY fecha_valoracion DESC, id DESC
            LIMIT 1
            """,
            (documento,),
        )

    def guardar_alertas(self, valoracion_id: int, alertas: list[dict[str, Any]]) -> None:
        if not alertas:
            return
        for alerta in alertas:
            campos = [
                'documento', 'valoracion_id', 'tipo', 'nivel', 'mensaje', 'unidad',
                'fecha_alerta', 'atendida', 'observaciones', 'fecha_creacion'
            ]
            row = {
                'documento': alerta.get('documento', ''),
                'valoracion_id': valoracion_id,
                'tipo': alerta.get('tipo', ''),
                'nivel': alerta.get('nivel', 'AMARILLO'),
                'mensaje': alerta.get('mensaje', ''),
                'unidad': alerta.get('unidad', ''),
                'fecha_alerta': now_iso(),
                'atendida': 0,
                'observaciones': '',
                'fecha_creacion': now_iso(),
            }
            self._insert_with_context('sn_alertas', campos, row)

    def latest_valoraciones(self, periodo: str | None = None) -> list[dict[str, Any]]:
        fundacion_id = _ctx_fundacion_id()
        where_periodo_v = "AND v.periodo = ?" if periodo else ""
        where_periodo_x = "AND x.periodo = v.periodo" if periodo else ""
        params: list[Any] = [fundacion_id]
        if periodo:
            params.append(periodo)
        params.append(fundacion_id)
        sql = f"""
            SELECT v.*
            FROM sn_valoraciones v
            WHERE v.activo = 1
              AND COALESCE(v.fundacion_id, 1) = ?
              {where_periodo_v}
              AND NOT EXISTS (
                SELECT 1
                FROM sn_valoraciones x
                WHERE x.documento = v.documento
                  AND x.activo = 1
                  AND COALESCE(x.fundacion_id, 1) = ?
                  {where_periodo_x}
                  AND (
                    COALESCE(x.fecha_valoracion, '') > COALESCE(v.fecha_valoracion, '')
                    OR (
                      COALESCE(x.fecha_valoracion, '') = COALESCE(v.fecha_valoracion, '')
                      AND x.id > v.id
                    )
                  )
              )
            ORDER BY v.unidad, v.nombre_completo
        """
        return self.fetch_all(sql, params)

    def historial_documento(self, documento: str) -> dict[str, Any] | None:
        datos = self.fetch_all(
            """
            SELECT *
            FROM sn_valoraciones
            WHERE documento = ? AND activo = 1
            ORDER BY fecha_valoracion DESC, id DESC
            """,
            (documento,),
        )
        if not datos:
            return None
        alertas = self.fetch_all(
            """
            SELECT *
            FROM sn_alertas
            WHERE documento = ?
            ORDER BY fecha_creacion DESC, id DESC
            """,
            (documento,),
        )
        eventos = self.fetch_all(
            """
            SELECT *
            FROM sn_calendario
            WHERE documento = ?
            ORDER BY fecha_programada DESC, id DESC
            """,
            (documento,),
        ) if self.table_exists('sn_calendario') else []
        return {'beneficiario': datos[0], 'historial': datos, 'alertas': alertas, 'calendario': eventos}

    def boa_data(self, periodo: str | None = None, unidad: str | None = None,
                 diagnostico: str | None = None, nivel: str | None = None) -> dict[str, Any]:
        latest = self.latest_valoraciones(periodo)
        if unidad:
            latest = [r for r in latest if (r.get('unidad') or '') == unidad]
        if diagnostico:
            latest = [r for r in latest if (r.get('diagnostico_global') or '') == diagnostico]
        if nivel:
            latest = [r for r in latest if (r.get('nivel_alerta') or '') == nivel]

        resumen = {
            'Adecuado': 0, 'Riesgo de desnutrición': 0, 'Desnutrición moderada': 0,
            'Desnutrición severa': 0, 'Riesgo de sobrepeso': 0, 'Sobrepeso': 0,
            'Obesidad': 0, 'Pendiente': 0
        }
        controles = {'Al día': 0, 'Próximo a vencer': 0, 'Vencido': 0, 'Pendiente': 0}
        unidades: dict[str, dict[str, Any]] = {}
        detalles = []
        for row in latest:
            diag = row.get('diagnostico_global') or 'Pendiente'
            estado = row.get('estado_control') or 'Pendiente'
            resumen[diag] = resumen.get(diag, 0) + 1
            controles[estado] = controles.get(estado, 0) + 1
            uni = row.get('unidad') or 'SIN UNIDAD'
            if uni not in unidades:
                unidades[uni] = {
                    'unidad': uni, 'total': 0, 'riesgo': 0, 'desnutricion': 0,
                    'sobrepeso_obesidad': 0, 'vencidos': 0, 'pendientes': 0
                }
            unidades[uni]['total'] += 1
            if 'Riesgo' in diag:
                unidades[uni]['riesgo'] += 1
            if 'Desnutrición' in diag:
                unidades[uni]['desnutricion'] += 1
            if diag in {'Sobrepeso', 'Obesidad', 'Riesgo de sobrepeso'}:
                unidades[uni]['sobrepeso_obesidad'] += 1
            if estado == 'Vencido':
                unidades[uni]['vencidos'] += 1
            if estado == 'Pendiente':
                unidades[uni]['pendientes'] += 1
            detalles.append({
                'unidad': uni,
                'nombre': row.get('nombre_completo') or '',
                'documento': row.get('documento') or '',
                'edad': row.get('edad_texto') or '',
                'edad_meses': row.get('edad_meses') or 0,
                'sexo': row.get('sexo') or '',
                'peso': row.get('peso_kg'),
                'talla': row.get('talla_cm'),
                'imc': row.get('imc'),
                'diagnostico': diag,
                'riesgo': row.get('nivel_alerta') or '',
                'fecha_valoracion': row.get('fecha_valoracion') or '',
                'proxima_valoracion': row.get('proximo_control') or '',
                'trimestre': row.get('trimestre') or '',
                'estado': estado,
                'observaciones': row.get('observaciones') or '',
                'docente': row.get('docente') or '',
                'acudiente': row.get('acudiente') or '',
            })

        return {
            'resumen': resumen,
            'controles': controles,
            'unidades': sorted(unidades.values(), key=lambda x: x['unidad']),
            'detalles': detalles,
        }

    def calendario_nutricional(self, periodo: str | None = None) -> dict[str, Any]:
        eventos = []
        if self.table_exists('sn_calendario'):
            rows = self.fetch_all(
                """
                SELECT *
                FROM sn_calendario
                ORDER BY fecha_programada ASC, id ASC
                LIMIT 2000
                """
            )
            eventos.extend(rows)

        # Reconstrucción derivada para conservar compatibilidad si no hay tabla histórica.
        existentes = {(e.get('documento'), e.get('fecha_programada'), e.get('tipo_evento')) for e in eventos}
        for row in self.latest_valoraciones(periodo):
            key = (row.get('documento'), row.get('proximo_control'), 'SEGUIMIENTO_TRIMESTRAL')
            if row.get('proximo_control') and key not in existentes:
                eventos.append({
                    'documento': row.get('documento'),
                    'valoracion_id': row.get('id'),
                    'tipo_evento': 'SEGUIMIENTO_TRIMESTRAL',
                    'fecha_programada': row.get('proximo_control'),
                    'estado': 'PENDIENTE' if row.get('nivel_alerta') in {'ROJO', 'AMARILLO'} else 'PROGRAMADO',
                    'nivel': row.get('nivel_alerta') or 'VERDE',
                    'unidad': row.get('unidad'),
                    'responsable': row.get('docente'),
                    'descripcion': f"Próximo control trimestral · {row.get('diagnostico_global') or 'Pendiente'}",
                })
        eventos.sort(key=lambda x: (x.get('fecha_programada') or '', x.get('unidad') or '', x.get('documento') or ''))
        return {'eventos': eventos}

    def dashboard_data(self, periodo: str | None = None) -> dict[str, Any]:
        latest = self.latest_valoraciones(periodo)
        total = len(latest)
        valorados = sum(1 for x in latest if x.get('peso_kg') is not None and x.get('talla_cm') is not None)
        pendientes = total - valorados
        criticos = sum(1 for x in latest if x.get('nivel_alerta') == 'ROJO')
        seguimiento = sum(1 for x in latest if x.get('nivel_alerta') == 'AMARILLO')
        sexo = {}
        edad = {'0-6 meses': 0, '6-11 meses': 0, '1-2 años': 0, '3-5 años': 0, '5+ años': 0}
        unidad = {}
        diagnostico = {}
        estado_control = {}
        tendencias = {}
        for row in latest:
            sexo[row.get('sexo') or 'Sin dato'] = sexo.get(row.get('sexo') or 'Sin dato', 0) + 1
            em = int(row.get('edad_meses') or 0)
            if em <= 6:
                edad['0-6 meses'] += 1
            elif em <= 11:
                edad['6-11 meses'] += 1
            elif em <= 35:
                edad['1-2 años'] += 1
            elif em <= 71:
                edad['3-5 años'] += 1
            else:
                edad['5+ años'] += 1
            unidad[row.get('unidad') or 'Sin unidad'] = unidad.get(row.get('unidad') or 'Sin unidad', 0) + 1
            diagnostico[row.get('diagnostico_global') or 'Pendiente'] = diagnostico.get(row.get('diagnostico_global') or 'Pendiente', 0) + 1
            estado_control[row.get('estado_control') or 'Pendiente'] = estado_control.get(row.get('estado_control') or 'Pendiente', 0) + 1
            key = (row.get('periodo') or 'SIN PERIODO', row.get('diagnostico_global') or 'Pendiente')
            tendencias[key] = tendencias.get(key, 0) + 1

        tendencias_rows = [
            {'periodo': periodo_key, 'diagnostico_global': diag_key, 'total': total_key}
            for (periodo_key, diag_key), total_key in sorted(tendencias.items())
        ]

        return {
            'total_usuarios': total,
            'total_valorados': valorados,
            'total_pendientes': pendientes,
            'casos_criticos': criticos,
            'casos_seguimiento': seguimiento,
            'cumplimiento': round((valorados / total) * 100, 1) if total else 0,
            'por_sexo': sexo,
            'por_edad': edad,
            'por_unidad': dict(sorted(unidad.items(), key=lambda item: item[0])),
            'por_diagnostico': diagnostico,
            'por_estado_control': estado_control,
            'tendencias': tendencias_rows,
            'ultimos_casos': latest[:200],
        }
