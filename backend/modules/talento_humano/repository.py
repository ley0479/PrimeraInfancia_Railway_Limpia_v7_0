from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Iterable

from modules.sqlalchemy_compat import CoreCompatRepository
from .schema import (
    TALENTO_SCHEMA_SQL,
    GP_SCHEMA_SQL,
    COORDINADORES_COLUMNS,
    UNIDADES_COLUMNS,
    USUARIOS_COLUMNS,
    BENEFICIARIOS_COLUMNS,
    GP_COMMON_COLUMNS,
    TH_INDEXES,
)


def now_iso() -> str:
    return datetime.now().isoformat(timespec='seconds')


def as_dict(row: Any | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def safe_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        return json.dumps(str(value), ensure_ascii=False)


def json_loads(value: Any, default: Any = None) -> Any:
    if value in (None, ''):
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


class TalentoHumanoRepository(CoreCompatRepository):
    """Repositorio SQLAlchemy Core para Talento Humano como fuente maestra.

    Mantiene compatibilidad con las tablas históricas, pero evita abrir SQLite
    directamente. La conversión completa a PostgreSQL se controla por Alembic.
    """

    def init_schema(self) -> None:
        # La sincronización llama varios upserts por persona. Ejecutar todas las
        # comprobaciones DDL en cada fila hacía que una publicación real tardara
        # cerca de un minuto y podía agotar el tiempo de la petición.
        if getattr(self, '_talento_schema_initialized', False):
            return
        self.execute_script(TALENTO_SCHEMA_SQL)
        self.execute_script(GP_SCHEMA_SQL)

        for table, columns in {
            'coordinadores': COORDINADORES_COLUMNS,
            'unidades': UNIDADES_COLUMNS,
            # Compatibilidad con bases creadas antes de Talento Humano fuente maestra.
            # Estas tablas ya pueden existir sin la columna docente; si no se asegura,
            # la sincronización falla con: sqlite3.OperationalError no such column: docente.
            'usuarios': USUARIOS_COLUMNS,
            'beneficiarios': BENEFICIARIOS_COLUMNS,
        }.items():
            for column, definition in columns.items():
                self.ensure_column(table, column, definition)

        for table in [
            'gp_coordinadores',
            'gp_docentes',
            'gp_equipos_interdisciplinarios',
            'gp_unidades_asignadas',
            'gp_asignaciones_coordinador',
            'gp_historial_acciones',
        ]:
            for column, definition in GP_COMMON_COLUMNS.items():
                self.ensure_column(table, column, definition)

        for statement in TH_INDEXES:
            try:
                self.execute_script(statement)
            except Exception:
                # En PostgreSQL algunos índices se gestionan desde Alembic. El
                # fallo no debe bloquear el arranque local.
                pass
        self._talento_schema_initialized = True

    def _fundacion_filter(self, fundacion_id: int | None, superadmin: bool, alias: str = '') -> tuple[str, list[Any]]:
        prefix = f"{alias}." if alias else ''
        if superadmin or not fundacion_id:
            return "1=1", []
        return f"({prefix}fundacion_id = ? OR {prefix}fundacion_id IS NULL)", [fundacion_id]

    def integral_dashboard(self, fundacion_id: int) -> dict[str, Any]:
        self.init_schema()
        today = datetime.now().date().isoformat()
        people = self.fetch_all("SELECT id,nombre,documento,cargo,rol_normalizado,unidad,estado,activo FROM th_personas WHERE fundacion_id=? AND activo=1 ORDER BY nombre", [fundacion_id])
        documents = self.fetch_all("SELECT d.*,p.nombre persona_nombre,p.unidad FROM th_documentos d JOIN th_personas p ON p.id=d.persona_id AND p.fundacion_id=d.fundacion_id WHERE d.fundacion_id=? ORDER BY d.fecha_vencimiento,d.id DESC", [fundacion_id])
        trainings = self.fetch_all("SELECT f.*,p.nombre persona_nombre,p.unidad FROM th_formaciones f JOIN th_personas p ON p.id=f.persona_id AND p.fundacion_id=f.fundacion_id WHERE f.fundacion_id=? ORDER BY f.fecha_inicio DESC,f.id DESC", [fundacion_id])
        evaluations = self.fetch_all("SELECT e.*,p.nombre persona_nombre,p.unidad FROM th_evaluaciones e JOIN th_personas p ON p.id=e.persona_id AND p.fundacion_id=e.fundacion_id WHERE e.fundacion_id=? ORDER BY e.fecha_evaluacion DESC,e.id DESC", [fundacion_id])
        capabilities = self.fetch_all("SELECT capacidad,nivel,COUNT(*) total,SUM(necesidad_formacion) necesidades,SUM(interes_apoyo) apoyos FROM th_capacidades WHERE fundacion_id=? GROUP BY capacidad,nivel ORDER BY capacidad,nivel", [fundacion_id])
        expired=sum(bool(row.get('fecha_vencimiento')) and str(row['fecha_vencimiento']) < today and row.get('estado')!='RENOVADO' for row in documents)
        return {'resumen':{'colaboradores_activos':len(people),'documentos':len(documents),'documentos_vencidos':expired,'formaciones_programadas':sum(row.get('estado')=='PROGRAMADA' for row in trainings),'evaluaciones_borrador':sum(row.get('estado')=='BORRADOR' for row in evaluations)},'personas':people,'documentos':documents,'formaciones':trainings,'evaluaciones':evaluations,'mapa_capacidades':capabilities}

    def integral_person(self, person_id: int, fundacion_id: int) -> dict[str, Any] | None:
        self.init_schema(); person=self.fetch_one("SELECT * FROM th_personas WHERE id=? AND fundacion_id=?",[person_id,fundacion_id])
        if not person:return None
        person['asignaciones']=self.fetch_all("SELECT * FROM th_asignaciones WHERE persona_id=? AND fundacion_id=? ORDER BY fecha_inicio DESC",[person_id,fundacion_id])
        person['documentos']=self.fetch_all("SELECT * FROM th_documentos WHERE persona_id=? AND fundacion_id=? ORDER BY fecha_vencimiento",[person_id,fundacion_id])
        person['formaciones']=self.fetch_all("SELECT * FROM th_formaciones WHERE persona_id=? AND fundacion_id=? ORDER BY fecha_inicio DESC",[person_id,fundacion_id])
        person['evaluaciones']=self.fetch_all("SELECT * FROM th_evaluaciones WHERE persona_id=? AND fundacion_id=? ORDER BY fecha_evaluacion DESC",[person_id,fundacion_id])
        person['capacidades']=self.fetch_all("SELECT * FROM th_capacidades WHERE persona_id=? AND fundacion_id=? ORDER BY capacidad",[person_id,fundacion_id])
        return person

    def integral_add(self, entity: str, payload: dict[str, Any], ctx: dict[str, Any]) -> None:
        self.init_schema(); fid=int(ctx.get('fundacion_id') or 1); uid=ctx.get('usuario_id'); now=now_iso(); pid=int(payload.get('persona_id') or 0)
        if not self.fetch_one("SELECT id FROM th_personas WHERE id=? AND fundacion_id=?",[pid,fid]): raise ValueError('Colaborador no encontrado en la fuente maestra.')
        if entity=='documentos':
            if not str(payload.get('tipo') or '').strip() or not str(payload.get('nombre') or '').strip(): raise ValueError('Tipo y nombre del documento son obligatorios.')
            self.execute("INSERT INTO th_documentos(fundacion_id,persona_id,tipo,nombre,fecha_emision,fecha_vencimiento,estado,archivo_referencia,observaciones,creado_por,fecha_creacion,fecha_actualizacion) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",[fid,pid,payload.get('tipo'),payload.get('nombre'),payload.get('fecha_emision'),payload.get('fecha_vencimiento'),'VIGENTE',payload.get('archivo_referencia'),payload.get('observaciones'),uid,now,now])
        elif entity=='formaciones':
            if not str(payload.get('nombre') or '').strip(): raise ValueError('Nombre de formación obligatorio.')
            self.execute("INSERT INTO th_formaciones(fundacion_id,persona_id,nombre,entidad,tipo,fecha_inicio,fecha_fin,horas,estado,observaciones,creado_por,fecha_creacion,fecha_actualizacion) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",[fid,pid,payload.get('nombre'),payload.get('entidad'),payload.get('tipo') or 'FORMACION',payload.get('fecha_inicio'),payload.get('fecha_fin'),float(payload.get('horas') or 0),'PROGRAMADA',payload.get('observaciones'),uid,now,now])
        elif entity=='evaluaciones':
            if not payload.get('periodo'): raise ValueError('Periodo obligatorio.')
            self.execute("INSERT INTO th_evaluaciones(fundacion_id,persona_id,periodo,tipo,fortalezas,oportunidades,compromisos,resultado,estado,evaluador_id,evaluador_nombre,fecha_evaluacion,fecha_creacion,fecha_actualizacion) VALUES(?,?,?,?,?,?,?,?, 'BORRADOR',?,?,?,?,?)",[fid,pid,payload.get('periodo'),payload.get('tipo') or 'ACOMPANAMIENTO',payload.get('fortalezas'),payload.get('oportunidades'),payload.get('compromisos'),payload.get('resultado'),uid,ctx.get('username'),payload.get('fecha_evaluacion') or datetime.now().date().isoformat(),now,now])
        elif entity=='capacidades':
            if not payload.get('capacidad'): raise ValueError('Capacidad obligatoria.')
            self.execute("INSERT INTO th_capacidades(fundacion_id,persona_id,capacidad,nivel,interes_apoyo,necesidad_formacion,observaciones,actualizado_por,fecha_actualizacion) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(fundacion_id,persona_id,capacidad) DO UPDATE SET nivel=excluded.nivel,interes_apoyo=excluded.interes_apoyo,necesidad_formacion=excluded.necesidad_formacion,observaciones=excluded.observaciones,actualizado_por=excluded.actualizado_por,fecha_actualizacion=excluded.fecha_actualizacion",[fid,pid,payload.get('capacidad'),payload.get('nivel') or 'EN_DESARROLLO',1 if payload.get('interes_apoyo') else 0,1 if payload.get('necesidad_formacion') else 0,payload.get('observaciones'),uid,now])
        else: raise ValueError('Entidad integral inválida.')
        self.audit('CREAR_'+entity.upper(),'th_'+entity,pid,None,payload,ctx)

    def list_talento(self, fundacion_id: int | None = None, superadmin: bool = False) -> list[dict[str, Any]]:
        self.init_schema()
        filtro, params = self._fundacion_filter(fundacion_id, superadmin)
        return self.fetch_all(
            f"""
            SELECT id, documento, nombre, nombres, apellidos, cargo, unidad, unidades,
                   direccion, telefono, coordinador, tipo_equipo, contrato, perfil,
                   estado, activo, archivo, fecha_carga, fecha_ultima_actualizacion,
                   fundacion_id, usuario_creador_id, fecha_creacion, fecha_actualizacion
            FROM coordinadores
            WHERE {filtro}
            ORDER BY unidad, cargo, nombre
            """,
            params,
        )

    def list_master_talento(self, fundacion_id: int) -> list[dict[str, Any]]:
        """Lee exclusivamente la versión publicada de Talento Humano maestro."""
        return self.fetch_all(
            """
            SELECT id, documento, nombre_completo AS nombre, nombres, apellidos,
                   cargo, unidad_servicio AS unidad, '[]' AS unidades,
                   '' AS direccion, telefono, coordinador,
                   rol_normalizado AS tipo_equipo, '' AS contrato, '' AS perfil,
                   estado, activo, 'BASE_MAESTRA_PUBLICADA' AS archivo,
                   fecha_consolidacion AS fecha_carga,
                   fecha_consolidacion AS fecha_ultima_actualizacion,
                   fundacion_id, NULL AS usuario_creador_id,
                   fecha_consolidacion AS fecha_creacion,
                   fecha_consolidacion AS fecha_actualizacion
            FROM master_talento_humano
            WHERE fundacion_id=? AND activo=1
            ORDER BY unidad_servicio, cargo, nombre_completo
            """,
            [int(fundacion_id)],
        )

    def get_talento(self, talento_id: int, fundacion_id: int | None = None, superadmin: bool = False) -> dict[str, Any] | None:
        self.init_schema()
        filtro, params = self._fundacion_filter(fundacion_id, superadmin)
        return self.fetch_one(f"SELECT * FROM coordinadores WHERE id = ? AND {filtro}", [talento_id, *params])

    def upsert_base_record(self, reg: dict[str, Any], ctx: dict[str, Any]) -> tuple[int | None, bool]:
        self.init_schema()
        documento = str(reg.get('documento') or '').strip()
        nombre = str(reg.get('nombre') or '').strip()
        if not documento or not nombre:
            return None, False

        fundacion_id = int(reg.get('fundacion_id') or ctx.get('fundacion_id') or 1)
        usuario_id = ctx.get('usuario_id')
        ahora = now_iso()

        unidad_key = str(reg.get('unidad') or '').strip()
        # La restricción real de la tabla es UNIQUE(fundacion_id, documento).
        # Buscar también por unidad/cargo hacía que una segunda fila de la
        # misma persona se tratara como nueva y PostgreSQL rechazara el INSERT.
        existente = self.fetch_one(
            """
            SELECT * FROM coordinadores
            WHERE documento = ? AND (fundacion_id = ? OR fundacion_id IS NULL)
            ORDER BY CASE WHEN fundacion_id = ? THEN 0 ELSE 1 END, id
            LIMIT 1
            """,
            [documento, fundacion_id, fundacion_id],
        )

        payload = {
            'documento': documento,
            'nombre': nombre,
            'nombres': reg.get('nombres') or '',
            'apellidos': reg.get('apellidos') or '',
            'cargo': reg.get('cargo') or '',
            'unidad': reg.get('unidad') or '',
            'unidades': reg.get('unidades') or '[]',
            'direccion': reg.get('direccion') or '',
            'telefono': reg.get('telefono') or '',
            'coordinador': reg.get('coordinador') or '',
            'tipo_equipo': reg.get('tipo_equipo') or '',
            'contrato': reg.get('contrato') or '',
            'perfil': reg.get('perfil') or '',
            'estado': reg.get('estado') or 'activo',
            'activo': int(reg.get('activo', 1) or 0),
            'archivo': reg.get('archivo') or '',
            'fundacion_id': fundacion_id,
            'usuario_creador_id': usuario_id,
            'fecha_actualizacion': ahora,
        }

        if existente:
            self.execute_update(
                """
                UPDATE coordinadores
                SET documento=:documento, nombre=:nombre, nombres=:nombres, apellidos=:apellidos,
                    cargo=:cargo, unidad=:unidad, unidades=:unidades, direccion=:direccion,
                    telefono=:telefono, coordinador=:coordinador, tipo_equipo=:tipo_equipo,
                    contrato=:contrato, perfil=:perfil, estado=:estado, activo=:activo,
                    archivo=:archivo, fundacion_id=:fundacion_id, usuario_creador_id=COALESCE(usuario_creador_id, :usuario_creador_id),
                    fecha_ultima_actualizacion=:fecha_actualizacion, fecha_actualizacion=:fecha_actualizacion
                WHERE id=:id
                """,
                {**payload, 'id': existente['id']},
            )
            self.audit('ACTUALIZAR_TALENTO_BASE', 'coordinadores', existente['id'], dict(existente), payload, ctx)
            return int(existente['id']), False

        payload['fecha_carga'] = ahora
        payload['fecha_creacion'] = ahora
        self.execute(
            """
            INSERT INTO coordinadores
            (documento, nombre, nombres, apellidos, cargo, unidad, unidades, direccion,
             telefono, coordinador, tipo_equipo, contrato, perfil, estado, activo, archivo,
             fecha_carga, fecha_ultima_actualizacion, fundacion_id, usuario_creador_id,
             fecha_creacion, fecha_actualizacion)
            VALUES
            (:documento, :nombre, :nombres, :apellidos, :cargo, :unidad, :unidades, :direccion,
             :telefono, :coordinador, :tipo_equipo, :contrato, :perfil, :estado, :activo, :archivo,
             :fecha_carga, :fecha_actualizacion, :fundacion_id, :usuario_creador_id,
             :fecha_creacion, :fecha_actualizacion)
            """,
            payload,
        )
        inserted = self.fetch_one(
            """
            SELECT id FROM coordinadores
            WHERE documento = ? AND fundacion_id = ?
            ORDER BY id DESC LIMIT 1
            """,
            [documento, fundacion_id],
        )
        talent_id = int(inserted['id']) if inserted else None
        self.audit('CREAR_TALENTO_BASE', 'coordinadores', talent_id, None, payload, ctx)
        return talent_id, True

    def save_base_records(self, registros: list[dict[str, Any]], ctx: dict[str, Any]) -> dict[str, int]:
        created = updated = skipped = 0
        for reg in registros:
            talent_id, is_new = self.upsert_base_record(reg, ctx)
            if not talent_id:
                skipped += 1
            elif is_new:
                created += 1
            else:
                updated += 1
        return {'creados': created, 'actualizados': updated, 'omitidos': skipped, 'total': created + updated}

    def update_base_record(self, talento_id: int, reg: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any] | None:
        actual = self.get_talento(talento_id, ctx.get('fundacion_id'), ctx.get('rol') == 'SUPERADMIN')
        if not actual:
            return None
        merged = dict(actual)
        merged.update(reg)
        merged['documento'] = str(merged.get('documento') or '').strip()
        merged['nombre'] = str(merged.get('nombre') or '').strip()
        if not merged['documento'] or not merged['nombre']:
            raise ValueError('Nombre y documento son obligatorios.')
        self.execute_update(
            """
            UPDATE coordinadores
            SET documento=:documento, nombre=:nombre, nombres=:nombres, apellidos=:apellidos,
                cargo=:cargo, unidad=:unidad, unidades=:unidades, direccion=:direccion,
                telefono=:telefono, coordinador=:coordinador, tipo_equipo=:tipo_equipo,
                contrato=:contrato, perfil=:perfil, estado=:estado, activo=:activo,
                fecha_ultima_actualizacion=:fecha_actualizacion, fecha_actualizacion=:fecha_actualizacion
            WHERE id=:id
            """,
            {
                'id': talento_id,
                'documento': merged.get('documento') or '',
                'nombre': merged.get('nombre') or '',
                'nombres': merged.get('nombres') or '',
                'apellidos': merged.get('apellidos') or '',
                'cargo': merged.get('cargo') or '',
                'unidad': merged.get('unidad') or '',
                'unidades': merged.get('unidades') or '[]',
                'direccion': merged.get('direccion') or '',
                'telefono': merged.get('telefono') or '',
                'coordinador': merged.get('coordinador') or '',
                'tipo_equipo': merged.get('tipo_equipo') or '',
                'contrato': merged.get('contrato') or '',
                'perfil': merged.get('perfil') or '',
                'estado': merged.get('estado') or 'activo',
                'activo': int(merged.get('activo', 1) or 0),
                'fecha_actualizacion': now_iso(),
            },
        )
        self.audit('EDITAR_TALENTO_BASE', 'coordinadores', talento_id, actual, merged, ctx)
        return self.get_talento(talento_id, ctx.get('fundacion_id'), ctx.get('rol') == 'SUPERADMIN')

    def deactivate_base_record(self, talento_id: int, ctx: dict[str, Any]) -> bool:
        actual = self.get_talento(talento_id, ctx.get('fundacion_id'), ctx.get('rol') == 'SUPERADMIN')
        if not actual:
            return False
        self.execute_update(
            """
            UPDATE coordinadores
            SET estado='inactivo', activo=0, fecha_ultima_actualizacion=?, fecha_actualizacion=?
            WHERE id=?
            """,
            [now_iso(), now_iso(), talento_id],
        )
        self.audit('DESACTIVAR_TALENTO_BASE', 'coordinadores', talento_id, actual, {'estado': 'inactivo'}, ctx)
        return True

    def hard_delete_base_record(self, talento_id: int, ctx: dict[str, Any]) -> bool:
        actual = self.get_talento(talento_id, ctx.get('fundacion_id'), ctx.get('rol') == 'SUPERADMIN')
        if not actual:
            return False
        self.execute_update("DELETE FROM coordinadores WHERE id = ?", [talento_id])
        self.audit('BORRAR_TALENTO_BASE', 'coordinadores', talento_id, actual, None, ctx)
        return True

    def audit(self, accion: str, tabla: str, registro_id: int | None, antes: Any, despues: Any, ctx: dict[str, Any]) -> None:
        try:
            self.init_schema()
            self.execute(
                """
                INSERT INTO th_historial
                (persona_id, accion, datos_anteriores, datos_nuevos, usuario, fundacion_id, fecha_accion)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    registro_id,
                    accion,
                    safe_json(antes) if antes is not None else None,
                    safe_json(despues) if despues is not None else None,
                    ctx.get('username') or 'sistema',
                    ctx.get('fundacion_id') or 1,
                    now_iso(),
                ],
            )
        except Exception:
            pass

    def upsert_th_persona(self, row: dict[str, Any], rol_normalizado: str, ctx: dict[str, Any]) -> tuple[int | None, bool]:
        self.init_schema()
        documento = str(row.get('documento') or '').strip()
        nombre = str(row.get('nombre') or '').strip()
        if not nombre:
            return None, False
        fundacion_id = int(row.get('fundacion_id') or ctx.get('fundacion_id') or 1)
        existing = None
        if documento:
            existing = self.fetch_one(
                """
                SELECT * FROM th_personas
                WHERE documento = ? AND (fundacion_id = ? OR fundacion_id IS NULL)
                ORDER BY id LIMIT 1
                """,
                [documento, fundacion_id],
            )
        if not existing:
            existing = self.fetch_one(
                """
                SELECT * FROM th_personas
                WHERE origen_tabla='coordinadores' AND origen_id = ? AND fundacion_id = ?
                ORDER BY id LIMIT 1
                """,
                [row.get('id'), fundacion_id],
            )
        payload = {
            'documento': documento,
            'nombre': nombre,
            'nombres': row.get('nombres') or '',
            'apellidos': row.get('apellidos') or '',
            'cargo': row.get('cargo') or '',
            'tipo_equipo': row.get('tipo_equipo') or '',
            'rol_normalizado': rol_normalizado,
            'unidad': row.get('unidad') or '',
            'direccion': row.get('direccion') or '',
            'telefono': row.get('telefono') or '',
            'coordinador': row.get('coordinador') or '',
            'contrato': row.get('contrato') or '',
            'perfil': row.get('perfil') or '',
            'estado': row.get('estado') or 'activo',
            'activo': int(row.get('activo', 1) or 0),
            'origen_tabla': 'coordinadores',
            'origen_id': row.get('id'),
            'archivo': row.get('archivo') or '',
            'fundacion_id': fundacion_id,
            'usuario_creador_id': ctx.get('usuario_id'),
            'fecha_actualizacion': now_iso(),
        }
        if existing:
            self.execute_update(
                """
                UPDATE th_personas
                SET documento=:documento, nombre=:nombre, nombres=:nombres, apellidos=:apellidos,
                    cargo=:cargo, tipo_equipo=:tipo_equipo, rol_normalizado=:rol_normalizado,
                    unidad=:unidad, direccion=:direccion, telefono=:telefono, coordinador=:coordinador,
                    contrato=:contrato, perfil=:perfil, estado=:estado, activo=:activo,
                    origen_tabla=:origen_tabla, origen_id=:origen_id, archivo=:archivo,
                    fundacion_id=:fundacion_id, usuario_creador_id=COALESCE(usuario_creador_id, :usuario_creador_id),
                    fecha_actualizacion=:fecha_actualizacion
                WHERE id=:id
                """,
                {**payload, 'id': existing['id']},
            )
            return int(existing['id']), False
        payload['fecha_creacion'] = now_iso()
        self.execute(
            """
            INSERT INTO th_personas
            (documento, nombre, nombres, apellidos, cargo, tipo_equipo, rol_normalizado, unidad,
             direccion, telefono, coordinador, contrato, perfil, estado, activo, origen_tabla,
             origen_id, archivo, fundacion_id, usuario_creador_id, fecha_creacion, fecha_actualizacion)
            VALUES
            (:documento, :nombre, :nombres, :apellidos, :cargo, :tipo_equipo, :rol_normalizado, :unidad,
             :direccion, :telefono, :coordinador, :contrato, :perfil, :estado, :activo, :origen_tabla,
             :origen_id, :archivo, :fundacion_id, :usuario_creador_id, :fecha_creacion, :fecha_actualizacion)
            """,
            payload,
        )
        new_row = self.fetch_one(
            """
            SELECT id FROM th_personas
            WHERE fundacion_id = ? AND origen_tabla='coordinadores' AND origen_id = ?
            ORDER BY id DESC LIMIT 1
            """,
            [fundacion_id, row.get('id')],
        )
        return (int(new_row['id']) if new_row else None), True

    def find_gp_coordinador(self, nombre: str = '', documento: str = '', contrato: str = '', fundacion_id: int = 1) -> int | None:
        if documento:
            row = self.fetch_one(
                """
                SELECT id FROM gp_coordinadores
                WHERE COALESCE(documento,'') = ? AND (fundacion_id = ? OR fundacion_id IS NULL)
                ORDER BY id LIMIT 1
                """,
                [documento, fundacion_id],
            )
            if row:
                return int(row['id'])
        if nombre:
            rows = self.fetch_all(
                """
                SELECT id, nombre FROM gp_coordinadores
                WHERE (fundacion_id = ? OR fundacion_id IS NULL) AND COALESCE(activo,1)=1
                """,
                [fundacion_id],
            )
            needle = nombre.strip().lower()
            for row in rows:
                if str(row.get('nombre') or '').strip().lower() == needle:
                    return int(row['id'])
        # No se debe usar el contrato como clave única para coordinadores:
        # en los listados ICBF todas las personas de la EAS pueden compartir
        # el mismo contrato, y eso mezclaba varios coordinadores en un solo
        # registro. La identidad real aquí es documento y, como respaldo, nombre.
        return None

    def upsert_gp_coordinador(self, row: dict[str, Any], fundacion_id: int, ctx: dict[str, Any], placeholder_name: str | None = None) -> tuple[int | None, bool]:
        nombre = str(placeholder_name or row.get('nombre') or 'SIN COORDINADOR ASIGNADO').strip().upper()
        documento = '' if placeholder_name else str(row.get('documento') or '').strip()
        contrato = str(row.get('contrato') or '').strip()
        existing_id = self.find_gp_coordinador(nombre, documento, contrato, fundacion_id)

        unidades = set()
        parsed_units = json_loads(row.get('unidades'), [])
        if isinstance(parsed_units, list):
            unidades.update(str(u).strip() for u in parsed_units if str(u).strip())
        if row.get('unidad'):
            unidades.add(str(row.get('unidad')).strip())
        if existing_id:
            existing_units_row = self.fetch_one("SELECT unidades_json FROM gp_coordinadores WHERE id = ?", [existing_id])
            existing_units = json_loads(existing_units_row['unidades_json'] if existing_units_row else None, [])
            if isinstance(existing_units, list):
                unidades.update(str(u).strip() for u in existing_units if str(u).strip())

        payload = {
            'nombre': nombre,
            'documento': documento,
            'telefono': '' if placeholder_name else row.get('telefono') or '',
            'cargo': 'COORDINADOR',
            'contrato': contrato,
            'unidades_json': safe_json(sorted(unidades)),
            'fundacion_id': fundacion_id,
            'usuario_creador_id': ctx.get('usuario_id'),
            'fecha': now_iso(),
        }
        if existing_id:
            self.execute_update(
                """
                UPDATE gp_coordinadores
                SET nombre=:nombre, documento=COALESCE(NULLIF(:documento,''), documento),
                    telefono=COALESCE(NULLIF(:telefono,''), telefono),
                    contrato=COALESCE(NULLIF(:contrato,''), contrato),
                    unidades_json=:unidades_json,
                    fundacion_id=:fundacion_id,
                    fecha_actualizacion=:fecha
                WHERE id=:id
                """,
                {**payload, 'id': existing_id},
            )
            return existing_id, False
        self.execute(
            """
            INSERT INTO gp_coordinadores
            (nombre, documento, telefono, cargo, contrato, unidades_json, activo,
             fecha_creacion, fecha_actualizacion, fundacion_id, usuario_creador_id)
            VALUES
            (:nombre, :documento, :telefono, :cargo, :contrato, :unidades_json, 1,
             :fecha, :fecha, :fundacion_id, :usuario_creador_id)
            """,
            payload,
        )
        created = self.find_gp_coordinador(nombre, documento, contrato, fundacion_id)
        return created, True

    def upsert_gp_docente(self, row: dict[str, Any], coordinador_id: int | None, fundacion_id: int, ctx: dict[str, Any]) -> tuple[int | None, bool]:
        documento = str(row.get('documento') or '').strip()
        unidad = str(row.get('unidad') or '').strip()
        existing = None
        if documento and unidad:
            existing = self.fetch_one(
                """
                SELECT id FROM gp_docentes
                WHERE documento = ? AND unidad = ? AND (fundacion_id = ? OR fundacion_id IS NULL)
                ORDER BY id LIMIT 1
                """,
                [documento, unidad, fundacion_id],
            )
        elif documento:
            existing = self.fetch_one(
                """
                SELECT id FROM gp_docentes
                WHERE documento = ? AND (fundacion_id = ? OR fundacion_id IS NULL)
                ORDER BY id LIMIT 1
                """,
                [documento, fundacion_id],
            )
        if not existing and unidad:
            existing = self.fetch_one(
                """
                SELECT id FROM gp_docentes
                WHERE unidad = ? AND nombre = ? AND (fundacion_id = ? OR fundacion_id IS NULL)
                ORDER BY id LIMIT 1
                """,
                [unidad, row.get('nombre') or '', fundacion_id],
            )
        payload = {
            'coordinador_id': coordinador_id,
            'nombre': row.get('nombre') or '',
            'documento': documento,
            'unidad': unidad,
            'telefono': row.get('telefono') or '',
            'cargo': row.get('cargo') or 'DOCENTE',
            'fundacion_id': fundacion_id,
            'usuario_creador_id': ctx.get('usuario_id'),
            'fecha': now_iso(),
        }
        if existing:
            self.execute_update(
                """
                UPDATE gp_docentes
                SET coordinador_id=:coordinador_id, nombre=:nombre, documento=:documento, unidad=:unidad,
                    telefono=:telefono, cargo=:cargo, activo=1, fundacion_id=:fundacion_id,
                    fecha_actualizacion=:fecha
                WHERE id=:id
                """,
                {**payload, 'id': existing['id']},
            )
            return int(existing['id']), False
        self.execute(
            """
            INSERT INTO gp_docentes
            (coordinador_id, nombre, documento, unidad, telefono, cargo, activo,
             fecha_creacion, fecha_actualizacion, fundacion_id, usuario_creador_id)
            VALUES
            (:coordinador_id, :nombre, :documento, :unidad, :telefono, :cargo, 1,
             :fecha, :fecha, :fundacion_id, :usuario_creador_id)
            """,
            payload,
        )
        created = self.fetch_one(
            """
            SELECT id FROM gp_docentes
            WHERE nombre = ? AND unidad = ? AND fundacion_id = ?
            ORDER BY id DESC LIMIT 1
            """,
            [payload['nombre'], unidad, fundacion_id],
        )
        return (int(created['id']) if created else None), True

    def upsert_gp_equipo(self, row: dict[str, Any], coordinador_id: int | None, rol: str, fundacion_id: int, ctx: dict[str, Any]) -> tuple[int | None, bool]:
        documento = str(row.get('documento') or '').strip()
        existing = None
        if documento and coordinador_id:
            existing = self.fetch_one(
                """
                SELECT id FROM gp_equipos_interdisciplinarios
                WHERE documento = ? AND rol = ? AND COALESCE(coordinador_id, 0) = ?
                  AND (fundacion_id = ? OR fundacion_id IS NULL)
                ORDER BY id LIMIT 1
                """,
                [documento, rol, int(coordinador_id), fundacion_id],
            )
        elif documento:
            existing = self.fetch_one(
                """
                SELECT id FROM gp_equipos_interdisciplinarios
                WHERE documento = ? AND rol = ? AND (fundacion_id = ? OR fundacion_id IS NULL)
                ORDER BY id LIMIT 1
                """,
                [documento, rol, fundacion_id],
            )
        payload = {
            'coordinador_id': coordinador_id,
            'nombre': row.get('nombre') or '',
            'documento': documento,
            'rol': rol,
            'profesion': row.get('perfil') or row.get('cargo') or '',
            'telefono': row.get('telefono') or '',
            'fundacion_id': fundacion_id,
            'usuario_creador_id': ctx.get('usuario_id'),
            'fecha': now_iso(),
        }
        if existing:
            self.execute_update(
                """
                UPDATE gp_equipos_interdisciplinarios
                SET coordinador_id=:coordinador_id, nombre=:nombre, documento=:documento,
                    rol=:rol, profesion=:profesion, telefono=:telefono, activo=1,
                    fundacion_id=:fundacion_id, fecha_actualizacion=:fecha
                WHERE id=:id
                """,
                {**payload, 'id': existing['id']},
            )
            return int(existing['id']), False
        self.execute(
            """
            INSERT INTO gp_equipos_interdisciplinarios
            (coordinador_id, nombre, documento, rol, profesion, telefono, activo,
             fecha_creacion, fecha_actualizacion, fundacion_id, usuario_creador_id)
            VALUES
            (:coordinador_id, :nombre, :documento, :rol, :profesion, :telefono, 1,
             :fecha, :fecha, :fundacion_id, :usuario_creador_id)
            """,
            payload,
        )
        created = self.fetch_one(
            """
            SELECT id FROM gp_equipos_interdisciplinarios
            WHERE nombre = ? AND rol = ? AND fundacion_id = ?
            ORDER BY id DESC LIMIT 1
            """,
            [payload['nombre'], rol, fundacion_id],
        )
        return (int(created['id']) if created else None), True

    def upsert_gp_asignacion(self, row: dict[str, Any], coordinador_id: int | None, rol: str, fundacion_id: int, ctx: dict[str, Any]) -> bool:
        documento = str(row.get('documento') or '').strip()
        unidad = str(row.get('unidad') or '').strip()
        existing = self.fetch_one(
            """
            SELECT id FROM gp_asignaciones_coordinador
            WHERE COALESCE(documento,'') = ? AND COALESCE(unidad,'') = ?
              AND COALESCE(rol,'') = ? AND (fundacion_id = ? OR fundacion_id IS NULL)
            ORDER BY id LIMIT 1
            """,
            [documento, unidad, rol, fundacion_id],
        )
        payload = {
            'coordinador_id': coordinador_id,
            'tipo_talento': rol,
            'origen_tabla': 'coordinadores',
            'origen_id': row.get('id'),
            'nombre': row.get('nombre') or '',
            'documento': documento,
            'cargo': row.get('cargo') or '',
            'rol': rol,
            'unidad': unidad,
            'telefono': row.get('telefono') or '',
            'estado': 'ACTIVO' if int(row.get('activo', 1) or 0) else 'INACTIVO',
            'observaciones': 'Sincronizado desde Talento Humano fuente maestra.',
            'fundacion_id': fundacion_id,
            'usuario_creador_id': ctx.get('usuario_id'),
            'fecha': now_iso(),
        }
        if existing:
            self.execute_update(
                """
                UPDATE gp_asignaciones_coordinador
                SET coordinador_id=:coordinador_id, tipo_talento=:tipo_talento,
                    origen_tabla=:origen_tabla, origen_id=:origen_id, nombre=:nombre,
                    documento=:documento, cargo=:cargo, rol=:rol, unidad=:unidad,
                    telefono=:telefono, estado=:estado, observaciones=:observaciones,
                    fundacion_id=:fundacion_id, fecha_actualizacion=:fecha
                WHERE id=:id
                """,
                {**payload, 'id': existing['id']},
            )
            return False
        self.execute(
            """
            INSERT INTO gp_asignaciones_coordinador
            (coordinador_id, tipo_talento, origen_tabla, origen_id, nombre, documento,
             cargo, rol, unidad, telefono, estado, fecha_inicio, observaciones,
             fundacion_id, usuario_creador_id, fecha_creacion, fecha_actualizacion)
            VALUES
            (:coordinador_id, :tipo_talento, :origen_tabla, :origen_id, :nombre, :documento,
             :cargo, :rol, :unidad, :telefono, :estado, :fecha, :observaciones,
             :fundacion_id, :usuario_creador_id, :fecha, :fecha)
            """,
            payload,
        )
        return True

    def upsert_th_asignacion(self, persona_id: int | None, row: dict[str, Any], coordinador_id: int | None, coordinador_nombre: str, rol: str, fundacion_id: int, ctx: dict[str, Any]) -> bool:
        if not persona_id:
            return False
        unidad = row.get('unidad') or ''
        existing = self.fetch_one(
            """
            SELECT id FROM th_asignaciones
            WHERE persona_id = ? AND COALESCE(unidad,'') = ? AND COALESCE(rol,'') = ?
              AND (fundacion_id = ? OR fundacion_id IS NULL)
            ORDER BY id LIMIT 1
            """,
            [persona_id, unidad, rol, fundacion_id],
        )
        payload = {
            'persona_id': persona_id,
            'coordinador_id': coordinador_id,
            'coordinador_nombre': coordinador_nombre,
            'unidad': unidad,
            'rol': rol,
            'cargo': row.get('cargo') or '',
            'estado': 'ACTIVO' if int(row.get('activo', 1) or 0) else 'INACTIVO',
            'fundacion_id': fundacion_id,
            'usuario_creador_id': ctx.get('usuario_id'),
            'fecha': now_iso(),
        }
        if existing:
            self.execute_update(
                """
                UPDATE th_asignaciones
                SET coordinador_id=:coordinador_id, coordinador_nombre=:coordinador_nombre,
                    unidad=:unidad, rol=:rol, cargo=:cargo, estado=:estado,
                    fundacion_id=:fundacion_id, fecha_actualizacion=:fecha
                WHERE id=:id
                """,
                {**payload, 'id': existing['id']},
            )
            return False
        self.execute(
            """
            INSERT INTO th_asignaciones
            (persona_id, coordinador_id, coordinador_nombre, unidad, rol, cargo, estado,
             fecha_inicio, fundacion_id, usuario_creador_id, fecha_creacion, fecha_actualizacion)
            VALUES
            (:persona_id, :coordinador_id, :coordinador_nombre, :unidad, :rol, :cargo,
             :estado, :fecha, :fundacion_id, :usuario_creador_id, :fecha, :fecha)
            """,
            payload,
        )
        return True

    def upsert_unidad_asignada(self, coordinador_id: int | None, unidad: str, fundacion_id: int, ctx: dict[str, Any]) -> bool:
        if not coordinador_id or not unidad:
            return False
        existing = self.fetch_one(
            """
            SELECT id FROM gp_unidades_asignadas
            WHERE coordinador_id = ? AND unidad = ? AND (fundacion_id = ? OR fundacion_id IS NULL)
            ORDER BY id LIMIT 1
            """,
            [coordinador_id, unidad, fundacion_id],
        )
        if existing:
            self.execute_update(
                "UPDATE gp_unidades_asignadas SET estado='activo', fecha_actualizacion=? WHERE id=?",
                [now_iso(), existing['id']],
            )
            return False
        self.execute(
            """
            INSERT INTO gp_unidades_asignadas
            (coordinador_id, unidad, estado, fecha_creacion, fecha_actualizacion, fundacion_id, usuario_creador_id)
            VALUES (?, ?, 'activo', ?, ?, ?, ?)
            """,
            [coordinador_id, unidad, now_iso(), now_iso(), fundacion_id, ctx.get('usuario_id')],
        )
        return True

    def update_unidad_docente(self, unidad: str, docente: dict[str, Any], coordinador_nombre: str, fundacion_id: int) -> int:
        if not unidad:
            return 0
        row = self.fetch_one(
            "SELECT id FROM unidades WHERE nombre = ? AND COALESCE(fundacion_id,1) = ?",
            [unidad, fundacion_id],
        )
        if row:
            return self.execute_update(
                """
                UPDATE unidades
                SET docente_asignado=?, docente_documento=?, coordinador_nombre=?,
                    contrato=?, direccion=COALESCE(NULLIF(?,''), direccion),
                    telefono=COALESCE(NULLIF(?,''), telefono),
                    fundacion_id=COALESCE(fundacion_id, ?), fecha_actualizacion=?
                WHERE id=?
                """,
                [
                    docente.get('nombre') or '',
                    docente.get('documento') or '',
                    coordinador_nombre or '',
                    docente.get('contrato') or '',
                    docente.get('direccion') or '',
                    docente.get('telefono') or '',
                    fundacion_id,
                    now_iso(),
                    row['id'],
                ],
            )
        self.execute(
            """
            INSERT INTO unidades
            (nombre, docente_asignado, docente_documento, coordinador_nombre, contrato,
             direccion, telefono, fundacion_id, total_usuarios, total_gestantes, fecha_actualizacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?)
            """,
            [
                unidad,
                docente.get('nombre') or '',
                docente.get('documento') or '',
                coordinador_nombre or '',
                docente.get('contrato') or '',
                docente.get('direccion') or '',
                docente.get('telefono') or '',
                fundacion_id,
                now_iso(),
            ],
        )
        return 1

    def update_docente_in_operacion(self, unidad: str, docente_nombre: str, fundacion_id: int) -> dict[str, int]:
        """Propaga el Agente Educativo responsable a operación.

        Las tablas históricas conservan el nombre de columna ``docente`` porque
        otros módulos y formatos oficiales ya la consumen. En bases anteriores,
        especialmente ``beneficiarios``, esa columna podía no existir y causaba
        ``OperationalError: no such column: docente`` durante la carga.
        """
        if not unidad or not docente_nombre:
            return {'beneficiarios': 0, 'usuarios': 0}

        self.init_schema()
        unidad = str(unidad or '').strip()
        variantes = sorted({
            unidad,
            unidad.upper(),
            f'UCA {unidad}'.strip(),
            f'UCA {unidad.upper()}'.strip(),
        })
        placeholders = ','.join(['?'] * len(variantes))
        params = [docente_nombre, *variantes, int(fundacion_id or 1)]
        sql = f"""
            UPDATE {{table}}
            SET docente = ?
            WHERE UPPER(TRIM(COALESCE(unidad,''))) IN ({placeholders})
              AND COALESCE(fundacion_id,1) = ?
        """
        beneficiarios = self.execute_update(sql.format(table='beneficiarios'), params)
        usuarios = self.execute_update(sql.format(table='usuarios'), params)
        return {'beneficiarios': beneficiarios, 'usuarios': usuarios}

    def log_sync(self, resultado: dict[str, Any], ctx: dict[str, Any], origen: str) -> None:
        self.execute(
            """
            INSERT INTO th_sincronizaciones
            (origen, total_personas, total_asignaciones, resultado_json, usuario, fundacion_id, fecha_sincronizacion)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                origen,
                int(resultado.get('th_personas_creadas', 0)) + int(resultado.get('th_personas_actualizadas', 0)),
                int(resultado.get('th_asignaciones_creadas', 0)) + int(resultado.get('th_asignaciones_actualizadas', 0)),
                safe_json(resultado),
                ctx.get('username') or 'sistema',
                ctx.get('fundacion_id') or 1,
                now_iso(),
            ],
        )

    def latest_sync(self) -> dict[str, Any] | None:
        return self.fetch_one("SELECT * FROM th_sincronizaciones ORDER BY fecha_sincronizacion DESC LIMIT 1")
