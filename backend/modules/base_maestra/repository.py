from __future__ import annotations

import json
import os
from modules.dbapi_compat import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

from .schema import SCHEMA_SQL
from modules.seguridad.tenant_context import current_tenant_context, strict_tenant_mode


def now_iso() -> str:
    return datetime.now().isoformat(timespec='seconds')


class BaseMaestraRepository:
    """Repositorio SQLite aislado para la arquitectura Base Maestra.

    No reemplaza tablas históricas. Todas las escrituras nuevas quedan en tablas
    independientes de Base Maestra para conservar reversibilidad.
    """

    def __init__(self, database_path: str):
        self.database_path = str(database_path)

    @contextmanager
    def connect(self):
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        try:
            yield conn
        finally:
            conn.close()

    def init_schema(self) -> None:
        if (
            os.getenv('SKIP_RUNTIME_SCHEMA_DDL', '').strip().lower()
            in {'1', 'true', 'yes', 'si', 'sí', 'on'}
            and os.getenv('APP_SCHEMA_MIGRATION_MODE', '').strip().lower()
            not in {'1', 'true', 'yes', 'si', 'sí', 'on'}
        ):
            return
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)
            self._ensure_retention_schema(conn)
            self._repair_active_version_index(conn)
            self._seed_corporaciones(conn)
            conn.commit()

    @staticmethod
    def _ensure_retention_schema(conn) -> None:
        """Migra de forma aditiva bases existentes para la retención mensual."""
        columns = {row['name'] for row in conn.execute('PRAGMA table_info(master_versiones)').fetchall()}
        if 'fecha_archivada' not in columns:
            conn.execute('ALTER TABLE master_versiones ADD COLUMN fecha_archivada TEXT')
        conn.execute(
            'CREATE INDEX IF NOT EXISTS idx_master_versiones_retencion '
            'ON master_versiones(fundacion_id, activa, fecha_archivada)'
        )

    @staticmethod
    def _repair_active_version_index(conn) -> None:
        """Repara el índice legado que también hacía únicos los borradores.

        Algunas bases PostgreSQL fueron creadas con un índice único sobre
        ``(fundacion_id, activa)`` sin predicado. ``IF NOT EXISTS`` no cambia
        esa definición y, por tanto, impedía conservar más de una versión con
        ``activa = 0``. Solo la fila activa debe ser única por fundación.
        """
        if hasattr(conn, '_connection'):
            row = conn.execute(
                """
                SELECT pg_get_indexdef(i.indexrelid) AS indexdef
                FROM pg_index i
                JOIN pg_class idx ON idx.oid = i.indexrelid
                WHERE i.indrelid = 'master_versiones'::regclass
                  AND idx.relname = ?
                """,
                ('idx_master_version_activa',),
            ).fetchone()
            definition = str(row['indexdef'] or '') if row else ''
        else:
            row = conn.execute(
                "SELECT sql AS indexdef FROM sqlite_master WHERE type = 'index' AND name = ?",
                ('idx_master_version_activa',),
            ).fetchone()
            definition = str(row['indexdef'] or '') if row else ''

        if definition and 'where' not in definition.lower():
            conn.execute('DROP INDEX IF EXISTS idx_master_version_activa')
            conn.execute(
                """
                CREATE UNIQUE INDEX idx_master_version_activa
                ON master_versiones(fundacion_id, activa) WHERE activa = 1
                """
            )

    def _seed_corporaciones(self, conn: sqlite3.Connection) -> None:
        """Crea una corporación operativa por fundación sin cruces entre tenants.

        En una petición multi-fundación solo se inicializa la fundación del
        contexto autenticado. Durante bootstrap (sin tenant) se pueden recorrer
        todas las fundaciones, porque todavía no existe una sesión de usuario.
        """
        now = now_iso()
        context = current_tenant_context()
        tenant_id = int(context.tenant_id or 0)
        try:
            if strict_tenant_mode() and tenant_id and not context.allow_global:
                rows = conn.execute(
                    "SELECT id, nombre, nit, representante, estado FROM fundaciones WHERE id=?",
                    (tenant_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, nombre, nit, representante, estado FROM fundaciones ORDER BY id"
                ).fetchall()
        except Exception:
            rows = []

        for row in rows:
            fid = int(row['id'])
            exists = conn.execute(
                "SELECT id FROM corporaciones WHERE fundacion_id=? LIMIT 1",
                (fid,),
            ).fetchone()
            if exists:
                continue
            conn.execute(
                """
                INSERT INTO corporaciones
                (fundacion_id, nombre, nit, representante, estado, fecha_creacion, fecha_actualizacion)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fid,
                    row['nombre'],
                    row['nit'] if 'nit' in row.keys() else None,
                    row['representante'] if 'representante' in row.keys() else None,
                    row['estado'] or 'ACTIVA',
                    now,
                    now,
                ),
            )

        # Compatibilidad para una base muy antigua sin tabla fundaciones.
        if not rows and (not strict_tenant_mode() or tenant_id in {0, 1}):
            exists = conn.execute(
                "SELECT id FROM corporaciones WHERE fundacion_id=1 LIMIT 1"
            ).fetchone()
            if not exists:
                conn.execute(
                    """
                    INSERT INTO corporaciones
                    (fundacion_id, nombre, estado, fecha_creacion, fecha_actualizacion)
                    VALUES (1, 'Fundación Principal', 'ACTIVA', ?, ?)
                    """,
                    (now, now),
                )

    def fetch_all(self, sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
        with self.connect() as conn:
            return [dict(row) for row in conn.execute(sql, tuple(params)).fetchall()]

    def fetch_one(self, sql: str, params: Iterable[Any] = ()) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(sql, tuple(params)).fetchone()
            return dict(row) if row else None

    def execute(self, sql: str, params: Iterable[Any] = ()) -> int:
        with self.connect() as conn:
            cur = conn.execute(sql, tuple(params))
            conn.commit()
            return int(cur.lastrowid or 0)

    def json_dumps(self, value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, default=str)

    def ensure_corporacion_for_foundation(
        self,
        fundacion_id: int,
        nombre: str,
        nit: str | None = None,
        representante: str | None = None,
        estado: str = 'ACTIVA',
    ) -> int:
        """Garantiza una corporación operativa vinculada a una fundación."""
        fid = int(fundacion_id or 0)
        if fid <= 0:
            raise ValueError('fundacion_id inválido para corporación.')
        self.init_schema()
        row = self.fetch_one(
            "SELECT id FROM corporaciones WHERE fundacion_id=? LIMIT 1",
            (fid,),
        )
        if row:
            return int(row['id'])
        new_id = self.execute(
            """
            INSERT INTO corporaciones
            (fundacion_id, nombre, nit, representante, estado, fecha_creacion, fecha_actualizacion)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fid,
                str(nombre or f'Fundación {fid}').strip(),
                nit,
                representante,
                str(estado or 'ACTIVA').upper(),
                now_iso(),
                now_iso(),
            ),
        )
        return int(new_id)

    def corporacion_para_fundacion(self, fundacion_id: int | None) -> int:
        fundacion_id = int(fundacion_id or 1)
        self.init_schema()
        row = self.fetch_one("SELECT id FROM corporaciones WHERE fundacion_id = ? LIMIT 1", (fundacion_id,))
        return int(row['id']) if row else 1

    def crear_carga(self, meta: dict[str, Any]) -> int:
        now = now_iso()
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO cargas_archivos
                (tipo_fuente, nombre_archivo_original, nombre_archivo_guardado, ruta_archivo, extension,
                 fecha_carga, usuario_id, usuario, corporacion_id, fundacion_id, total_registros,
                 registros_validos, registros_error, estado, columnas_json, errores_json, metadata_json, fecha_actualizacion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    meta.get('tipo_fuente'), meta.get('nombre_archivo_original'), meta.get('nombre_archivo_guardado'),
                    meta.get('ruta_archivo'), meta.get('extension'), now, meta.get('usuario_id'), meta.get('usuario'),
                    meta.get('corporacion_id'), meta.get('fundacion_id') or 1, meta.get('total_registros') or 0,
                    meta.get('registros_validos') or 0, meta.get('registros_error') or 0, meta.get('estado') or 'cargado',
                    self.json_dumps(meta.get('columnas') or []), self.json_dumps(meta.get('errores') or []),
                    self.json_dumps(meta.get('metadata') or {}), now,
                ),
            )
            conn.commit()
            return int(cur.lastrowid)

    def actualizar_carga(self, carga_id: int, **fields: Any) -> None:
        if not fields:
            return
        allowed = {
            'total_registros', 'registros_validos', 'registros_error', 'estado', 'columnas_json',
            'errores_json', 'metadata_json', 'fecha_actualizacion'
        }
        sets = []
        params = []
        for key, value in fields.items():
            if key not in allowed:
                continue
            sets.append(f'{key} = ?')
            params.append(value)
        if not sets:
            return
        sets.append('fecha_actualizacion = ?')
        params.append(now_iso())
        params.append(carga_id)
        with self.connect() as conn:
            conn.execute(f"UPDATE cargas_archivos SET {', '.join(sets)} WHERE id = ?", tuple(params))
            conn.commit()

    def insertar_staging(self, tipo_fuente: str, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        table = {
            'cuentame': 'staging_cuentame',
            'talento_humano': 'staging_talento_humano',
            'talento': 'staging_talento_humano',
            'salud_nutricion': 'staging_salud_nutricion',
            'nutricion': 'staging_salud_nutricion',
        }.get(tipo_fuente, 'staging_cuentame')
        with self.connect() as conn:
            cur = conn.cursor()
            for row in rows:
                columns = list(row.keys())
                placeholders = ','.join(['?'] * len(columns))
                cur.execute(
                    f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})",
                    tuple(row[col] for col in columns),
                )
            conn.commit()

    def limpiar_staging_carga(self, carga_id: int, tipo_fuente: str) -> None:
        table = {
            'cuentame': 'staging_cuentame',
            'talento_humano': 'staging_talento_humano',
            'talento': 'staging_talento_humano',
            'salud_nutricion': 'staging_salud_nutricion',
            'nutricion': 'staging_salud_nutricion',
        }.get(tipo_fuente, 'staging_cuentame')
        with self.connect() as conn:
            conn.execute(f"DELETE FROM {table} WHERE carga_id = ?", (carga_id,))
            conn.execute("DELETE FROM master_inconsistencias WHERE carga_id = ? AND version_id IS NULL", (carga_id,))
            conn.commit()

    def staging_rows(self, tipo_fuente: str, carga_id: int | None = None, fundacion_id: int | None = None) -> list[dict[str, Any]]:
        table = {
            'cuentame': 'staging_cuentame',
            'talento_humano': 'staging_talento_humano',
            'talento': 'staging_talento_humano',
            'salud_nutricion': 'staging_salud_nutricion',
            'nutricion': 'staging_salud_nutricion',
        }.get(tipo_fuente, 'staging_cuentame')
        where = []
        params: list[Any] = []
        if carga_id:
            where.append('carga_id = ?')
            params.append(carga_id)
        if fundacion_id:
            where.append('fundacion_id = ?')
            params.append(fundacion_id)
        sql = f"SELECT * FROM {table}"
        if where:
            sql += ' WHERE ' + ' AND '.join(where)
        sql += ' ORDER BY id'
        return self.fetch_all(sql, params)

    def registrar_inconsistencia(self, data: dict[str, Any]) -> int:
        now = now_iso()
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO master_inconsistencias
                (version_id, carga_id, tipo_fuente, severidad, tipo, documento, nombre, unidad_servicio,
                 campo, descripcion, valor_1, valor_2, datos_json, corporacion_id, fundacion_id, fecha_creacion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data.get('version_id'), data.get('carga_id'), data.get('tipo_fuente'), data.get('severidad') or 'ADVERTENCIA',
                    data.get('tipo'), data.get('documento'), data.get('nombre'), data.get('unidad_servicio'), data.get('campo'),
                    data.get('descripcion'), data.get('valor_1'), data.get('valor_2'), self.json_dumps(data.get('datos') or {}),
                    data.get('corporacion_id'), data.get('fundacion_id') or 1, now,
                ),
            )
            conn.commit()
            return int(cur.lastrowid)

    def guardar_validacion(self, data: dict[str, Any]) -> int:
        now = now_iso()
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO validaciones_cargas
                (carga_id, tipo_fuente, fundacion_id, corporacion_id, estado, semaforo, total_registros,
                 registros_validos, registros_error, errores_criticos, advertencias, duplicados,
                 calidad_porcentaje, reporte_json, recomendaciones_json, fecha_validacion, usuario_id, usuario)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data.get('carga_id'), data.get('tipo_fuente'), data.get('fundacion_id') or 1, data.get('corporacion_id'),
                    data.get('estado') or 'pendiente', data.get('semaforo') or 'ROJO', data.get('total_registros') or 0,
                    data.get('registros_validos') or 0, data.get('registros_error') or 0, data.get('errores_criticos') or 0,
                    data.get('advertencias') or 0, data.get('duplicados') or 0, data.get('calidad_porcentaje') or 0,
                    self.json_dumps(data.get('reporte') or {}), self.json_dumps(data.get('recomendaciones') or []),
                    now, data.get('usuario_id'), data.get('usuario'),
                ),
            )
            conn.commit()
            return int(cur.lastrowid)

    def ultima_carga(self, tipo_fuente: str, fundacion_id: int, estados: tuple[str, ...] = ('validado', 'consolidado', 'publicado', 'cargado')) -> dict[str, Any] | None:
        placeholders = ','.join(['?'] * len(estados))
        return self.fetch_one(
            f"""
            SELECT * FROM cargas_archivos
            WHERE tipo_fuente = ? AND fundacion_id = ? AND estado IN ({placeholders})
            ORDER BY fecha_carga DESC, id DESC LIMIT 1
            """,
            (tipo_fuente, fundacion_id, *estados),
        )

    def version_activa(self, fundacion_id: int) -> dict[str, Any] | None:
        return self.fetch_one(
            "SELECT * FROM master_versiones WHERE fundacion_id = ? AND activa = 1 ORDER BY id DESC LIMIT 1",
            (fundacion_id,),
        )

    def crear_version_borrador(self, data: dict[str, Any]) -> int:
        fundacion_id = int(data.get('fundacion_id') or 1)
        with self.connect() as conn:
            row = conn.execute("SELECT COALESCE(MAX(version_numero), 0) + 1 AS nextv FROM master_versiones WHERE fundacion_id = ?", (fundacion_id,)).fetchone()
            version_numero = int(row['nextv'] or 1)
            now = now_iso()
            cur = conn.execute(
                """
                INSERT INTO master_versiones
                (version_numero, corporacion_id, fundacion_id, estado, activa, fecha_creacion, usuario_id,
                 usuario, cargas_json, resumen_json, errores_criticos, advertencias, calidad_porcentaje, observaciones)
                VALUES (?, ?, ?, 'BORRADOR', 0, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    version_numero, data.get('corporacion_id'), fundacion_id, now, data.get('usuario_id'), data.get('usuario'),
                    self.json_dumps(data.get('cargas') or {}), self.json_dumps(data.get('resumen') or {}),
                    data.get('errores_criticos') or 0, data.get('advertencias') or 0,
                    data.get('calidad_porcentaje') or 0, data.get('observaciones'),
                ),
            )
            conn.commit()
            return int(cur.lastrowid)

    def actualizar_version_resumen(self, version_id: int, resumen: dict[str, Any], errores_criticos: int, advertencias: int, calidad: float) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE master_versiones
                SET resumen_json = ?, errores_criticos = ?, advertencias = ?, calidad_porcentaje = ?
                WHERE id = ?
                """,
                (self.json_dumps(resumen), errores_criticos, advertencias, calidad, version_id),
            )
            conn.commit()

    def publicar_version(self, version_id: int, ctx: dict[str, Any], observaciones: str = '') -> dict[str, Any]:
        now = now_iso()
        with self.connect() as conn:
            version = conn.execute("SELECT * FROM master_versiones WHERE id = ?", (version_id,)).fetchone()
            if not version:
                raise ValueError('Versión no encontrada.')
            fundacion_id = int(version['fundacion_id'] or 1)
            criticos = conn.execute(
                "SELECT COUNT(*) c FROM master_inconsistencias WHERE version_id = ? AND severidad = 'CRITICA' AND COALESCE(resuelta,0)=0",
                (version_id,),
            ).fetchone()['c']
            if int(criticos or 0) > 0:
                raise ValueError(f'No se puede publicar: existen {criticos} inconsistencias críticas sin resolver.')
            anterior = conn.execute(
                "SELECT id FROM master_versiones WHERE fundacion_id = ? AND activa = 1 ORDER BY id DESC LIMIT 1",
                (fundacion_id,),
            ).fetchone()
            anterior_id = int(anterior['id']) if anterior else None
            if anterior_id:
                conn.execute(
                    "UPDATE master_versiones SET activa = 0, estado = 'ARCHIVADA', fecha_archivada = ? WHERE id = ?",
                    (now, anterior_id),
                )
            conn.execute("UPDATE master_versiones SET activa = 1, estado = 'ACTIVA', fecha_publicacion = ? WHERE id = ?", (now, version_id))
            for table in ['master_ninos', 'master_salud_nutricion', 'master_talento_humano', 'master_unidades']:
                conn.execute(f"UPDATE {table} SET activo = 0 WHERE fundacion_id = ?", (fundacion_id,))
                conn.execute(f"UPDATE {table} SET activo = 1 WHERE version_id = ?", (version_id,))
            cur = conn.execute(
                """
                INSERT INTO master_publicaciones
                (version_id, version_anterior_id, corporacion_id, fundacion_id, usuario_id, usuario, estado,
                 resumen_json, fecha_publicacion, observaciones)
                VALUES (?, ?, ?, ?, ?, ?, 'PUBLICADA', ?, ?, ?)
                """,
                (
                    version_id, anterior_id, version['corporacion_id'], fundacion_id, ctx.get('usuario_id'),
                    ctx.get('usuario'), version['resumen_json'], now, observaciones,
                ),
            )
            conn.commit()
            return {'publicacion_id': int(cur.lastrowid), 'version_id': version_id, 'version_anterior_id': anterior_id, 'fecha_publicacion': now}

    def aplicar_retencion(
        self,
        fundacion_id: int,
        dias_versiones: int = 30,
        horas_temporales: int = 48,
        ahora: datetime | None = None,
    ) -> dict[str, Any]:
        """Conserva la activa y, como máximo, una anterior durante 30 días.

        La operación está aislada por fundación. Nunca elimina la versión activa.
        Los staging y borradores vencidos se limpian a las 48 horas.
        """
        fid = int(fundacion_id or 1)
        current = ahora or datetime.now()
        cutoff_versions = (current - timedelta(days=max(1, int(dias_versiones)))).isoformat(timespec='seconds')
        cutoff_temp = (current - timedelta(hours=max(1, int(horas_temporales)))).isoformat(timespec='seconds')
        deleted: dict[str, int] = {}

        with self.connect() as conn:
            active = conn.execute(
                'SELECT id FROM master_versiones WHERE fundacion_id=? AND activa=1 ORDER BY id DESC LIMIT 1',
                (fid,),
            ).fetchone()
            active_id = int(active['id']) if active else None
            archived = conn.execute(
                """
                SELECT id, COALESCE(fecha_archivada, fecha_publicacion, fecha_creacion) AS fecha_retencion
                FROM master_versiones
                WHERE fundacion_id=? AND activa=0 AND estado='ARCHIVADA'
                ORDER BY COALESCE(fecha_archivada, fecha_publicacion, fecha_creacion) DESC, id DESC
                """,
                (fid,),
            ).fetchall()
            keep_previous = None
            if archived and str(archived[0]['fecha_retencion'] or '') >= cutoff_versions:
                keep_previous = int(archived[0]['id'])

            purge_ids = [int(row['id']) for row in archived if int(row['id']) != keep_previous]
            stale_drafts = conn.execute(
                """
                SELECT id FROM master_versiones
                WHERE fundacion_id=? AND activa=0 AND estado='BORRADOR' AND fecha_creacion < ?
                """,
                (fid, cutoff_temp),
            ).fetchall()
            purge_ids.extend(int(row['id']) for row in stale_drafts)
            purge_ids = sorted({vid for vid in purge_ids if vid != active_id})

            if purge_ids:
                marks = ','.join('?' for _ in purge_ids)
                conn.execute(
                    f'UPDATE master_publicaciones SET version_anterior_id=NULL '
                    f'WHERE fundacion_id=? AND version_anterior_id IN ({marks})',
                    (fid, *purge_ids),
                )
                for table in (
                    'master_projection_status', 'master_publicaciones', 'master_historial_cambios',
                    'master_movimientos', 'master_inconsistencias', 'master_salud_nutricion',
                    'master_talento_humano', 'master_unidades', 'master_ninos',
                ):
                    cursor = conn.execute(
                        f'DELETE FROM {table} WHERE fundacion_id=? AND version_id IN ({marks})',
                        (fid, *purge_ids),
                    )
                    deleted[table] = max(0, int(cursor.rowcount or 0))
                cursor = conn.execute(
                    f'DELETE FROM master_versiones WHERE fundacion_id=? AND activa=0 AND id IN ({marks})',
                    (fid, *purge_ids),
                )
                deleted['master_versiones'] = max(0, int(cursor.rowcount or 0))

            old_loads = conn.execute(
                """
                SELECT c.id FROM cargas_archivos c
                WHERE c.fundacion_id=? AND c.fecha_carga < ? AND (
                    EXISTS (SELECT 1 FROM staging_cuentame s WHERE s.fundacion_id=? AND s.carga_id=c.id)
                    OR EXISTS (SELECT 1 FROM staging_talento_humano s WHERE s.fundacion_id=? AND s.carga_id=c.id)
                    OR EXISTS (SELECT 1 FROM staging_salud_nutricion s WHERE s.fundacion_id=? AND s.carga_id=c.id)
                    OR EXISTS (SELECT 1 FROM validaciones_cargas v WHERE v.fundacion_id=? AND v.carga_id=c.id)
                )
                """,
                (fid, cutoff_temp, fid, fid, fid, fid),
            ).fetchall()
            load_ids = [int(row['id']) for row in old_loads]
            if load_ids:
                marks = ','.join('?' for _ in load_ids)
                for table in ('staging_cuentame', 'staging_talento_humano', 'staging_salud_nutricion'):
                    cursor = conn.execute(
                        f'DELETE FROM {table} WHERE fundacion_id=? AND carga_id IN ({marks})',
                        (fid, *load_ids),
                    )
                    deleted[table] = max(0, int(cursor.rowcount or 0))
                cursor = conn.execute(
                    f'DELETE FROM validaciones_cargas WHERE fundacion_id=? AND carga_id IN ({marks})',
                    (fid, *load_ids),
                )
                deleted['validaciones_cargas'] = max(0, int(cursor.rowcount or 0))
            if purge_ids or load_ids:
                policy = {'dias_versiones': dias_versiones, 'horas_temporales': horas_temporales, 'max_versiones': 2}
                conn.execute(
                    """
                    INSERT INTO master_retention_runs
                    (fundacion_id,version_activa_id,version_anterior_id,versiones_eliminadas_json,
                     cargas_depuradas,registros_eliminados_json,politica_json,fecha_ejecucion)
                    VALUES (?,?,?,?,?,?,?,?)
                    """,
                    (
                        fid, active_id, keep_previous, self.json_dumps(purge_ids), len(load_ids),
                        self.json_dumps(deleted), self.json_dumps(policy), current.isoformat(timespec='seconds'),
                    ),
                )
            conn.commit()

        return {
            'fundacion_id': fid,
            'version_activa_protegida': active_id,
            'version_anterior_conservada': keep_previous,
            'versiones_eliminadas': purge_ids,
            'cargas_temporales_depuradas': len(load_ids),
            'registros_eliminados': deleted,
            'politica': {'dias_versiones': dias_versiones, 'horas_temporales': horas_temporales, 'max_versiones': 2},
        }
