from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import date, datetime, timedelta
from typing import Any

from flask import g, jsonify, request
from werkzeug.utils import secure_filename
from sqlalchemy import text

from .repository import BillingRepository, add_months, now_iso, parse_date, today_iso
from .schema import CREDIT_COSTS, CREDIT_PATH_RULES, PATH_MODULE_MAP
from modules.runtime_schema import migration_mode, runtime_schema_ddl_disabled, schema_ddl_enabled
from database import database


def normalize_estado_suscripcion(fecha_vencimiento: str, estado_actual: str = 'ACTIVA', dias_gracia: int = 5) -> str:
    estado = (estado_actual or 'ACTIVA').upper()
    if estado in {'SUSPENDIDA', 'CANCELADA'}:
        return estado
    venc = parse_date(fecha_vencimiento, date.today())
    hoy = date.today()
    if venc < hoy:
        return 'VENCIDA'
    if 0 <= (venc - hoy).days <= 5:
        return 'POR_VENCER'
    return 'ACTIVA'


def subscription_to_api(sub: dict[str, Any] | None) -> dict[str, Any]:
    if not sub:
        return {}
    data = dict(sub)
    data['modulos_habilitados'] = json.loads(data.get('modulos_habilitados') or '[]') if isinstance(data.get('modulos_habilitados'), str) else (data.get('modulos_habilitados') or [])
    try:
        inicio = parse_date(data.get('fecha_inicio'))
        venc = parse_date(data.get('fecha_vencimiento'))
        gracia = int(data.get('dias_gracia') or 0)
        data['dias_totales'] = max(0, (venc - inicio).days)
        data['dias_transcurridos'] = max(0, min(data['dias_totales'], (date.today() - inicio).days))
        data['dias_restantes'] = (venc - date.today()).days
        data['porcentaje_tiempo_consumido'] = round(
            (data['dias_transcurridos'] / data['dias_totales'] * 100) if data['dias_totales'] else 0, 2
        )
        data['fecha_fin_gracia'] = (venc + timedelta(days=gracia)).isoformat()
        data['en_gracia'] = venc < date.today() <= venc + timedelta(days=gracia)
        data['gracia_vencida'] = date.today() > venc + timedelta(days=gracia)
    except Exception:
        data['dias_restantes'] = 0
        data['dias_totales'] = 0
        data['dias_transcurridos'] = 0
        data['porcentaje_tiempo_consumido'] = 0
        data['en_gracia'] = False
        data['gracia_vencida'] = False
    return data


class BillingService:
    _INIT_LOCK = threading.RLock()
    _INITIALIZED_DATABASES: set[str] = set()

    def __init__(self, repo: BillingRepository, upload_folder: str | None = None):
        self.repo = repo
        self.upload_folder = upload_folder

    def init(self, *, force: bool = False) -> None:
        """Inicializa catálogos una sola vez por base y proceso.

        Antes se ejecutaban DDL, semillas y actualizaciones de suscripción en
        cada request autenticado. Ese patrón multiplicaba escritores SQLite y
        podía bloquear el login mientras el navegador cargaba el tablero.
        """
        key = str(getattr(self.repo, 'database_path', '') or 'default')
        # En workers de producción el esquema ya fue migrado por init_hosting.
        # No ejecutar DDL ni escrituras de catálogo en registro/before_request.
        if runtime_schema_ddl_disabled() and not force:
            self._INITIALIZED_DATABASES.add(key)
            return
        if not force and key in self._INITIALIZED_DATABASES:
            return
        with self._INIT_LOCK:
            if not force and key in self._INITIALIZED_DATABASES:
                return
            self.repo.init_schema()
            self.refresh_all_subscription_states()
            self._INITIALIZED_DATABASES.add(key)

    def authorized_fundacion_id(self, fundacion_id: int | None = None) -> int:
        current = int(self.repo.current_fundacion_id() or 1)
        fid = int(fundacion_id or current)
        if not self.repo.is_superadmin() and fid != current:
            raise PermissionError('No tienes permiso para operar sobre otra fundación.')
        return fid

    def refresh_all_subscription_states(self) -> None:
        conn = self.repo.connect()
        cur = conn.cursor()
        if self.repo.is_superadmin() or self.repo.context().get('rol') == 'SYSTEM':
            rows = cur.execute("SELECT * FROM suscripciones_fundacion").fetchall()
        else:
            rows = cur.execute(
                "SELECT * FROM suscripciones_fundacion WHERE fundacion_id=?",
                (self.repo.current_fundacion_id(),),
            ).fetchall()
        changed = False
        timestamp = now_iso()
        for row in rows:
            estado = normalize_estado_suscripcion(row['fecha_vencimiento'], row['estado'], int(row['dias_gracia'] or 0))
            if str(row.get('estado') or '').upper() != estado:
                cur.execute(
                    "UPDATE suscripciones_fundacion SET estado=?, fecha_actualizacion=? WHERE id=?",
                    (estado, timestamp, row['id']),
                )
                changed = True
            try:
                foundation = cur.execute(
                    "SELECT suscripcion_estado, creditos_disponibles FROM fundaciones WHERE id=?",
                    (row['fundacion_id'],),
                ).fetchone()
                if (
                    not foundation
                    or str(foundation.get('suscripcion_estado') or '').upper() != estado
                    or int(foundation.get('creditos_disponibles') or 0) != int(row['creditos_disponibles'] or 0)
                ):
                    cur.execute(
                        "UPDATE fundaciones SET suscripcion_estado=?, creditos_disponibles=?, fecha_actualizacion=? WHERE id=?",
                        (estado, row['creditos_disponibles'], timestamp, row['fundacion_id']),
                    )
                    changed = True
            except Exception:
                pass
        if changed:
            conn.commit()
        else:
            conn.rollback()
        conn.close()

    def list_planes(self) -> list[dict[str, Any]]:
        rows = self.repo.fetch_all("SELECT * FROM planes_suscripcion ORDER BY precio_mensual, nombre")
        for row in rows:
            row['modulos_habilitados'] = json.loads(row.get('modulos_habilitados') or '[]')
        return rows

    def create_or_update_plan(self, data: dict[str, Any], plan_id: int | None = None) -> dict[str, Any]:
        nombre = (data.get('nombre') or '').strip().upper()
        if not nombre:
            raise ValueError('Nombre de plan requerido.')
        modules = data.get('modulos_habilitados') or data.get('modulos') or []
        if isinstance(modules, str):
            try:
                modules = json.loads(modules)
            except Exception:
                modules = [m.strip() for m in modules.split(',') if m.strip()]
        modules_json = json.dumps(modules, ensure_ascii=False)
        payload = (
            nombre,
            data.get('descripcion') or '',
            float(data.get('precio_mensual') or 0),
            int(data.get('limite_usuarios') or 0),
            int(data.get('limite_coordinadores') or 0),
            int(data.get('limite_unidades') or 0),
            int(data.get('creditos_incluidos') or 0),
            modules_json,
            (data.get('estado') or 'ACTIVO').upper(),
            int(bool(data.get('personalizado'))),
            now_iso(),
        )
        if plan_id:
            before = self.repo.fetch_one("SELECT * FROM planes_suscripcion WHERE id=?", (plan_id,))
            if not before:
                raise ValueError('Plan no encontrado.')
            self.repo.execute_update(
                """
                UPDATE planes_suscripcion
                SET nombre=?, descripcion=?, precio_mensual=?, limite_usuarios=?, limite_coordinadores=?,
                    limite_unidades=?, creditos_incluidos=?, modulos_habilitados=?, estado=?, personalizado=?, fecha_actualizacion=?
                WHERE id=?
                """,
                payload + (plan_id,),
            )
            self._sync_modulos_plan(plan_id, modules)
            plan = self.repo.fetch_one("SELECT * FROM planes_suscripcion WHERE id=?", (plan_id,))
            self.repo.log('EDITAR_PLAN', 'planes_suscripcion', plan_id, before, plan)
            return subscription_to_api(plan)
        new_id = self.repo.execute(
            """
            INSERT INTO planes_suscripcion
            (nombre, descripcion, precio_mensual, limite_usuarios, limite_coordinadores,
             limite_unidades, creditos_incluidos, modulos_habilitados, estado, personalizado, fecha_creacion, fecha_actualizacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            payload + (now_iso(),),
        )
        self._sync_modulos_plan(new_id, modules)
        plan = self.repo.fetch_one("SELECT * FROM planes_suscripcion WHERE id=?", (new_id,))
        self.repo.log('CREAR_PLAN', 'planes_suscripcion', new_id, despues=plan)
        return subscription_to_api(plan)

    def _sync_modulos_plan(self, plan_id: int, modules: list[str]) -> None:
        self.repo.execute_update("DELETE FROM modulos_plan WHERE plan_id=?", (plan_id,))
        for modulo in modules:
            self.repo.execute(
                "INSERT INTO modulos_plan (plan_id, modulo_codigo, habilitado, fecha_creacion) VALUES (?, ?, 1, ?)",
                (plan_id, modulo, now_iso()),
            )

    def delete_or_disable_plan(self, plan_id: int) -> dict[str, Any]:
        before = self.repo.fetch_one("SELECT * FROM planes_suscripcion WHERE id=?", (plan_id,))
        if not before:
            raise ValueError('Plan no encontrado.')
        self.repo.execute_update("UPDATE planes_suscripcion SET estado='INACTIVO', fecha_actualizacion=? WHERE id=?", (now_iso(), plan_id))
        plan = self.repo.fetch_one("SELECT * FROM planes_suscripcion WHERE id=?", (plan_id,))
        self.repo.log('INACTIVAR_PLAN', 'planes_suscripcion', plan_id, before, plan)
        return plan or {}

    def list_suscripciones(self) -> list[dict[str, Any]]:
        self.refresh_all_subscription_states()
        where, params = self.repo.fundacion_scope_clause('s')
        rows = self.repo.fetch_all(
            f"""
            SELECT s.*, f.nombre AS fundacion_nombre, f.nit AS fundacion_nit, p.nombre AS plan_nombre, p.precio_mensual
            FROM suscripciones_fundacion s
            LEFT JOIN fundaciones f ON f.id=s.fundacion_id
            LEFT JOIN planes_suscripcion p ON p.id=s.plan_id
            WHERE {where}
            ORDER BY s.estado, f.nombre
            """,
            params,
        )
        return [subscription_to_api(r) for r in rows]

    def get_subscription_snapshot(
        self,
        fundacion_id: int | None = None,
        *,
        trusted_internal: bool = False,
    ) -> dict[str, Any]:
        """Consulta la suscripción sin ejecutar DDL ni escrituras de mantenimiento.

        ``trusted_internal`` se reserva para el flujo interno de login, donde la
        contraseña ya fue validada pero todavía no existe un contexto de sesión
        autenticado en ``flask.g``. No se expone como parámetro de ninguna API.
        """
        if trusted_internal:
            if fundacion_id is None:
                return {}
            fid = int(fundacion_id)
        else:
            fid = self.authorized_fundacion_id(fundacion_id)
        row = self.repo.fetch_one(
            """
            SELECT s.*, f.nombre AS fundacion_nombre, f.nit AS fundacion_nit, p.nombre AS plan_nombre, p.precio_mensual,
                   p.limite_usuarios, p.limite_coordinadores, p.limite_unidades
            FROM suscripciones_fundacion s
            LEFT JOIN fundaciones f ON f.id=s.fundacion_id
            LEFT JOIN planes_suscripcion p ON p.id=s.plan_id
            WHERE s.fundacion_id=?
            """,
            (fid,),
        )
        data = subscription_to_api(row)
        if data:
            data['estado'] = normalize_estado_suscripcion(
                str(data.get('fecha_vencimiento') or ''),
                str(data.get('estado') or 'ACTIVA'),
                int(data.get('dias_gracia') or 0),
            )
        return data

    def get_subscription(self, fundacion_id: int | None = None) -> dict[str, Any]:
        self.refresh_all_subscription_states()
        fid = self.authorized_fundacion_id(fundacion_id)
        row = self.repo.fetch_one(
            """
            SELECT s.*, f.nombre AS fundacion_nombre, f.nit AS fundacion_nit, p.nombre AS plan_nombre, p.precio_mensual,
                   p.limite_usuarios, p.limite_coordinadores, p.limite_unidades
            FROM suscripciones_fundacion s
            LEFT JOIN fundaciones f ON f.id=s.fundacion_id
            LEFT JOIN planes_suscripcion p ON p.id=s.plan_id
            WHERE s.fundacion_id=?
            """,
            (fid,),
        )
        if not row and schema_ddl_enabled():
            self.repo.init_schema()
            row = self.repo.fetch_one(
                """
                SELECT s.*, f.nombre AS fundacion_nombre, f.nit AS fundacion_nit, p.nombre AS plan_nombre, p.precio_mensual,
                       p.limite_usuarios, p.limite_coordinadores, p.limite_unidades
                FROM suscripciones_fundacion s
                LEFT JOIN fundaciones f ON f.id=s.fundacion_id
                LEFT JOIN planes_suscripcion p ON p.id=s.plan_id
                WHERE s.fundacion_id=?
                """,
                (fid,),
            )
        data = subscription_to_api(row)
        if not data:
            return data
        ledger = self.repo.fetch_one(
            """SELECT
                   COALESCE(SUM(CASE WHEN creditos > 0 THEN creditos ELSE 0 END),0) AS creditos_totales,
                   COALESCE(SUM(CASE WHEN creditos < 0 THEN ABS(creditos) ELSE 0 END),0) AS creditos_consumidos
               FROM movimientos_credito WHERE fundacion_id=? AND COALESCE(estado,'APLICADO')='APLICADO'""",
            (fid,),
        ) or {}
        total = int(ledger.get('creditos_totales') or 0)
        consumed = int(ledger.get('creditos_consumidos') or 0)
        available = int(data.get('creditos_disponibles') or 0)
        elapsed = max(1, int(data.get('dias_transcurridos') or 0))
        daily_average = round(consumed / elapsed, 2) if consumed > 0 else 0
        projected_days = int(available / daily_average) if daily_average > 0 else None
        available_percentage = round((available / total * 100) if total > 0 else 0, 2)
        data.update({
            'creditos_totales': total,
            'creditos_consumidos': consumed,
            'porcentaje_consumido': round((consumed / total * 100) if total > 0 else 0, 2),
            'porcentaje_disponible': available_percentage,
            'promedio_diario_consumo': daily_average,
            'dias_estimados_agotamiento': projected_days,
            'fecha_estimada_agotamiento': (
                (date.today() + timedelta(days=projected_days)).isoformat()
                if projected_days is not None else None
            ),
            'estado_creditos': (
                'AGOTADO' if available <= 0 else 'CRITICO' if available_percentage <= 5
                else 'ALTO' if available_percentage <= 10 else 'ADVERTENCIA'
                if available_percentage <= 25 else 'NORMAL'
            ),
        })
        return data

    def upsert_subscription(self, data: dict[str, Any], fundacion_id: int | None = None) -> dict[str, Any]:
        fid = self.authorized_fundacion_id(
            fundacion_id or int(data.get('fundacion_id') or self.repo.current_fundacion_id())
        )
        before = self.get_subscription(fid)
        plan_id = int(data.get('plan_id') or before.get('plan_id') or 1)
        plan = self.repo.fetch_one("SELECT * FROM planes_suscripcion WHERE id=?", (plan_id,))
        if not plan:
            raise ValueError('Plan no encontrado.')
        modules = data.get('modulos_habilitados') or before.get('modulos_habilitados') or json.loads(plan.get('modulos_habilitados') or '[]')
        if isinstance(modules, list):
            modules_json = json.dumps(modules, ensure_ascii=False)
        else:
            modules_json = modules
        inicio = data.get('fecha_inicio') or before.get('fecha_inicio') or today_iso()
        venc = data.get('fecha_vencimiento') or before.get('fecha_vencimiento') or add_months(parse_date(inicio), 1).isoformat()
        estado = (data.get('estado') or normalize_estado_suscripcion(venc, before.get('estado') or 'ACTIVA', int(data.get('dias_gracia') or before.get('dias_gracia') or 5))).upper()
        dias_gracia = int(data.get('dias_gracia') or before.get('dias_gracia') or 5)
        creditos = int(data.get('creditos_disponibles') if data.get('creditos_disponibles') is not None else before.get('creditos_disponibles') or plan.get('creditos_incluidos') or 0)
        existing = self.repo.fetch_one("SELECT id FROM suscripciones_fundacion WHERE fundacion_id=?", (fid,))
        if existing:
            sid = existing['id']
            self.repo.execute_update(
                """
                UPDATE suscripciones_fundacion
                SET plan_id=?, estado=?, fecha_inicio=?, fecha_vencimiento=?, dias_gracia=?, creditos_disponibles=?,
                    creditos_incluidos_periodo=?, modulos_habilitados=?, observaciones=?, fecha_actualizacion=?
                WHERE id=?
                """,
                (plan_id, estado, inicio, venc, dias_gracia, creditos, int(plan.get('creditos_incluidos') or 0), modules_json, data.get('observaciones') or before.get('observaciones'), now_iso(), sid),
            )
        else:
            sid = self.repo.execute(
                """
                INSERT INTO suscripciones_fundacion
                (fundacion_id, plan_id, estado, fecha_inicio, fecha_vencimiento, dias_gracia,
                 creditos_disponibles, creditos_incluidos_periodo, modulos_habilitados, observaciones, fecha_creacion, fecha_actualizacion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (fid, plan_id, estado, inicio, venc, dias_gracia, creditos, int(plan.get('creditos_incluidos') or 0), modules_json, data.get('observaciones'), now_iso(), now_iso()),
            )
        self.repo.execute_update("UPDATE fundaciones SET plan_id=?, suscripcion_estado=?, creditos_disponibles=?, fecha_actualizacion=? WHERE id=?", (plan_id, estado, creditos, now_iso(), fid))
        if creditos <= 0 or estado in {'VENCIDA', 'SUSPENDIDA', 'CANCELADA'}:
            self.repo.execute_update(
                "UPDATE sesiones_usuario SET activa=0, fecha_cierre=? WHERE fundacion_id=? AND activa=1",
                (now_iso(), fid),
            )
        after = self.get_subscription(fid)
        self.repo.execute(
            """
            INSERT INTO historial_suscripcion
            (fundacion_id, suscripcion_id, accion, estado_anterior, estado_nuevo, plan_anterior_id, plan_nuevo_id,
             datos_anteriores, datos_nuevos, usuario_id, fecha_accion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (fid, after.get('id'), 'ACTUALIZAR_SUSCRIPCION', before.get('estado'), after.get('estado'), before.get('plan_id'), after.get('plan_id'), json.dumps(before, ensure_ascii=False), json.dumps(after, ensure_ascii=False), self.repo.current_user_id(), now_iso()),
        )
        self.repo.log('ACTUALIZAR_SUSCRIPCION', 'suscripciones_fundacion', after.get('id'), before, after)
        return after

    def save_comprobante(self, file) -> tuple[str | None, str | None]:
        if not file or not getattr(file, 'filename', ''):
            return None, None
        base = self.upload_folder or os.path.join(os.getcwd(), 'pagos')
        os.makedirs(base, exist_ok=True)
        nombre = secure_filename(file.filename) or 'comprobante'
        guardado = f"PAGO_{datetime.now().strftime('%Y%m%d%H%M%S')}_{nombre}"
        ruta = os.path.join(base, guardado)
        file.save(ruta)
        return guardado, ruta

    def registrar_pago(self, data: dict[str, Any], file=None) -> dict[str, Any]:
        fid = self.authorized_fundacion_id(int(data.get('fundacion_id') or self.repo.current_fundacion_id()))
        sub = self.get_subscription(fid)
        plan_id = int(data.get('plan_id') or sub.get('plan_id') or 1)
        plan = self.repo.fetch_one("SELECT * FROM planes_suscripcion WHERE id=?", (plan_id,))
        if not plan:
            raise ValueError('Plan no encontrado.')
        fecha_pago = data.get('fecha_pago') or today_iso()
        fecha_vencimiento = data.get('fecha_vencimiento') or add_months(parse_date(fecha_pago), 1).isoformat()
        metodo = data.get('metodo_pago') or data.get('metodo') or 'Otro'
        valor = float(data.get('valor_pagado') or plan.get('precio_mensual') or 0)
        nombre_comp, ruta_comp = self.save_comprobante(file)
        pago_id = self.repo.execute(
            """
            INSERT INTO pagos_suscripcion
            (fundacion_id, suscripcion_id, plan_id, valor_pagado, metodo_pago, fecha_pago, fecha_vencimiento,
             referencia_pago, comprobante_nombre, comprobante_ruta, usuario_registra_id, observaciones, fecha_creacion, fecha_actualizacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (fid, sub.get('id'), plan_id, valor, metodo, fecha_pago, fecha_vencimiento, data.get('referencia_pago') or data.get('referencia'), nombre_comp, ruta_comp, self.repo.current_user_id(), data.get('observaciones'), now_iso(), now_iso()),
        )
        creditos_incluidos = int(plan.get('creditos_incluidos') or 0)
        updated = self.upsert_subscription({
            'fundacion_id': fid,
            'plan_id': plan_id,
            'estado': 'ACTIVA',
            'fecha_inicio': fecha_pago,
            'fecha_vencimiento': fecha_vencimiento,
            # El saldo se mantiene y la suma queda registrada como movimiento de crédito.
            'creditos_disponibles': int(sub.get('creditos_disponibles') or 0),
            'modulos_habilitados': json.loads(plan.get('modulos_habilitados') or '[]'),
            'observaciones': data.get('observaciones') or 'Pago registrado',
        }, fid)
        if creditos_incluidos:
            self.registrar_movimiento_credito(fid, 'ASIGNACION', 'creditos_plan_pago', creditos_incluidos, f'Créditos incluidos por pago del plan {plan.get("nombre")}', referencia_tipo='pago', referencia_id=str(pago_id))
            updated = self.get_subscription(fid)
        pago = self.repo.fetch_one("SELECT * FROM pagos_suscripcion WHERE id=?", (pago_id,)) or {}
        self.repo.log('REGISTRAR_PAGO', 'pagos_suscripcion', pago_id, despues=pago)
        return {'pago': pago, 'suscripcion': updated}

    def registrar_movimiento_credito(
        self, fundacion_id: int, tipo: str, accion: str, creditos: int,
        descripcion: str = '', referencia_tipo: str | None = None,
        referencia_id: str | None = None, *, idempotency_key: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        fundacion_id = self.authorized_fundacion_id(fundacion_id)
        movement_type = str(tipo or '').strip().upper()
        amount = abs(int(creditos))
        if amount <= 0:
            raise ValueError('La cantidad de créditos debe ser mayor que cero.')
        key = str(idempotency_key or uuid.uuid4().hex).strip()[:180]
        timestamp = now_iso()

        with database.transaction() as conn:
            lock_suffix = ' FOR UPDATE' if database.is_postgresql else ''
            sub_result = conn.execute(
                text('SELECT * FROM suscripciones_fundacion WHERE fundacion_id=:fid' + lock_suffix),
                {'fid': fundacion_id},
            ).mappings().first()
            if not sub_result:
                raise ValueError('La fundación no tiene una suscripción configurada.')
            sub = dict(sub_result)

            existing = conn.execute(
                text('''SELECT * FROM movimientos_credito
                        WHERE fundacion_id=:fid AND idempotency_key=:key LIMIT 1'''),
                {'fid': fundacion_id, 'key': key},
            ).mappings().first()
            if existing:
                return dict(existing)

            previous_balance = int(sub.get('creditos_disponibles') or 0)
            if movement_type == 'CONSUMO':
                if previous_balance < amount:
                    raise PermissionError('Créditos insuficientes')
                new_balance = previous_balance - amount
                signed_amount = -amount
            else:
                new_balance = previous_balance + amount
                signed_amount = amount

            inserted = conn.execute(
                text('''INSERT INTO movimientos_credito
                        (fundacion_id,suscripcion_id,tipo,accion,creditos,saldo_anterior,saldo_nuevo,
                         referencia_tipo,referencia_id,descripcion,usuario_id,fecha_movimiento,
                         idempotency_key,estado,metadata_json,fecha_aplicacion)
                        VALUES (:fid,:sid,:tipo,:accion,:creditos,:anterior,:nuevo,:ref_tipo,:ref_id,
                                :descripcion,:usuario,:fecha,:key,'APLICADO',:metadata,:fecha)
                        RETURNING id'''),
                {
                    'fid': fundacion_id, 'sid': sub.get('id'), 'tipo': movement_type,
                    'accion': accion, 'creditos': signed_amount, 'anterior': previous_balance,
                    'nuevo': new_balance, 'ref_tipo': referencia_tipo, 'ref_id': referencia_id,
                    'descripcion': descripcion, 'usuario': self.repo.current_user_id(),
                    'fecha': timestamp, 'key': key,
                    'metadata': json.dumps(metadata or {}, ensure_ascii=False),
                },
            ).scalar_one()
            conn.execute(
                text('''UPDATE suscripciones_fundacion
                        SET creditos_disponibles=:saldo, fecha_actualizacion=:fecha
                        WHERE fundacion_id=:fid'''),
                {'saldo': new_balance, 'fecha': timestamp, 'fid': fundacion_id},
            )
            conn.execute(
                text('''UPDATE fundaciones SET creditos_disponibles=:saldo,
                        fecha_actualizacion=:fecha WHERE id=:fid'''),
                {'saldo': new_balance, 'fecha': timestamp, 'fid': fundacion_id},
            )
            if movement_type == 'CONSUMO' and new_balance <= 0:
                conn.execute(
                    text('''UPDATE sesiones_usuario SET activa=0, fecha_cierre=:fecha
                            WHERE fundacion_id=:fid AND activa=1'''),
                    {'fecha': timestamp, 'fid': fundacion_id},
                )
            mov = dict(conn.execute(
                text('SELECT * FROM movimientos_credito WHERE id=:id'), {'id': int(inserted)}
            ).mappings().one())

        self.repo.log('CREDITOS_' + movement_type, 'movimientos_credito', int(mov['id']), despues=mov)
        return mov

    def asignar_creditos(self, data: dict[str, Any]) -> dict[str, Any]:
        fid = self.authorized_fundacion_id(int(data.get('fundacion_id') or self.repo.current_fundacion_id()))
        creditos = int(data.get('creditos') or 0)
        if creditos <= 0:
            paquete_id = data.get('paquete_id')
            if paquete_id:
                paquete = self.repo.fetch_one("SELECT * FROM paquetes_credito WHERE id=?", (paquete_id,))
                creditos = int(paquete.get('creditos') or 0) if paquete else 0
        if creditos <= 0:
            raise ValueError('Cantidad de créditos requerida.')
        return self.registrar_movimiento_credito(
            fid, 'ASIGNACION', data.get('accion') or 'asignacion_manual', creditos,
            data.get('descripcion') or 'Asignación manual de créditos', referencia_tipo='paquete',
            referencia_id=str(data.get('paquete_id') or 'manual'),
            idempotency_key=data.get('idempotency_key'),
        )

    def consumir_creditos(
        self, fundacion_id: int, accion: str, referencia_tipo: str | None = None,
        referencia_id: str | None = None, descripcion: str = '', *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        fundacion_id = self.authorized_fundacion_id(fundacion_id)
        costo = int(CREDIT_COSTS.get(accion, 0))
        if costo <= 0:
            return {}
        sub = self.get_subscription(fundacion_id)
        saldo = int(sub.get('creditos_disponibles') or 0)
        if saldo < costo:
            raise PermissionError('Créditos insuficientes')
        return self.registrar_movimiento_credito(
            fundacion_id, 'CONSUMO', accion, costo,
            descripcion or f'Consumo de {costo} crédito(s) por {accion}', referencia_tipo,
            referencia_id, idempotency_key=idempotency_key,
        )

    def credit_rule_for_request(self, path: str, method: str) -> dict[str, Any] | None:
        for rule in CREDIT_PATH_RULES:
            if method.upper() not in rule.get('methods', []):
                continue
            if not path.startswith(rule.get('prefix', '')):
                continue
            contains = rule.get('contains')
            if contains and contains not in path:
                continue
            accion = rule.get('accion')
            costo = int(CREDIT_COSTS.get(accion, 0))
            if costo > 0:
                return {**rule, 'costo': costo}
        return None

    def module_for_path(self, path: str) -> str | None:
        for prefix, modulo in PATH_MODULE_MAP:
            if path.startswith(prefix):
                return modulo
        return None

    def dashboard(self) -> dict[str, Any]:
        self.refresh_all_subscription_states()
        if self.repo.is_superadmin():
            mes_actual = date.today().strftime('%Y-%m')
            stats = self.repo.fetch_one(
                """
                SELECT
                    (SELECT COUNT(*) FROM fundaciones) AS fundaciones_total,
                    (SELECT COUNT(*) FROM suscripciones_fundacion WHERE estado='ACTIVA') AS activas,
                    (SELECT COUNT(*) FROM suscripciones_fundacion WHERE estado='POR_VENCER') AS por_vencer,
                    (SELECT COUNT(*) FROM suscripciones_fundacion WHERE estado='VENCIDA') AS vencidas,
                    (SELECT COUNT(*) FROM suscripciones_fundacion WHERE estado='SUSPENDIDA') AS suspendidas,
                    (SELECT COALESCE(SUM(valor_pagado),0) FROM pagos_suscripcion WHERE substr(fecha_pago,1,7)=?) AS ingresos_mes,
                    (SELECT COALESCE(SUM(CASE WHEN tipo='CONSUMO' THEN ABS(creditos) ELSE 0 END),0) FROM movimientos_credito WHERE substr(fecha_movimiento,1,7)=?) AS creditos_consumidos_mes
                """,
                (mes_actual, mes_actual),
            ) or {}
            recientes = self.repo.fetch_all(
                """
                SELECT p.*, f.nombre AS fundacion_nombre, ps.nombre AS plan_nombre
                FROM pagos_suscripcion p
                LEFT JOIN fundaciones f ON f.id=p.fundacion_id
                LEFT JOIN planes_suscripcion ps ON ps.id=p.plan_id
                ORDER BY p.fecha_pago DESC, p.id DESC LIMIT 20
                """
            )
            vencidas = self.repo.fetch_all(
                """
                SELECT s.*, f.nombre AS fundacion_nombre, p.nombre AS plan_nombre
                FROM suscripciones_fundacion s
                LEFT JOIN fundaciones f ON f.id=s.fundacion_id
                LEFT JOIN planes_suscripcion p ON p.id=s.plan_id
                WHERE s.estado IN ('VENCIDA','SUSPENDIDA','POR_VENCER')
                ORDER BY s.fecha_vencimiento ASC LIMIT 50
                """
            )
            return {
                'stats': stats,
                'pagos_recientes': recientes,
                'alertas': [subscription_to_api(v) for v in vencidas],
                'suscripciones': self.list_suscripciones(),
                'fecha_actual': date.today().isoformat(),
            }
        sub = self.get_subscription()
        movimientos = self.repo.fetch_all(
            """
            SELECT * FROM movimientos_credito WHERE fundacion_id=? ORDER BY fecha_movimiento DESC, id DESC LIMIT 50
            """,
            (self.repo.current_fundacion_id(),),
        )
        pagos = self.repo.fetch_all("SELECT * FROM pagos_suscripcion WHERE fundacion_id=? ORDER BY fecha_pago DESC, id DESC LIMIT 20", (self.repo.current_fundacion_id(),))
        return {
            'suscripcion': sub, 'movimientos': movimientos, 'pagos': pagos,
            'alertas': self.subscription_alerts(sub),
            'fecha_actual': date.today().isoformat(),
        }

    def subscription_alerts(self, sub: dict[str, Any]) -> list[dict[str, Any]]:
        """Recordatorios deterministas; una alerta por tipo y umbral."""
        if not sub:
            return []
        alerts: list[dict[str, Any]] = []
        days = int(sub.get('dias_restantes') or 0)
        time_level = next(((limit, level) for limit, level in (
            (0, 'VENCIDA'), (1, 'CRITICA'), (3, 'ALTA'), (7, 'ADVERTENCIA'), (14, 'INFORMATIVA')
        ) if days <= limit), None)
        if time_level:
            limit, level = time_level
            alerts.append({
                'tipo': 'VIGENCIA', 'nivel': level, 'umbral': limit,
                'fundacion_nombre': sub.get('fundacion_nombre'),
                'mensaje': ('La suscripción está vencida.' if days <= 0 else f'La suscripción vence en {days} día(s).'),
                'fecha_vencimiento': sub.get('fecha_vencimiento'),
            })
        available = float(sub.get('porcentaje_disponible') or 0)
        credit_level = next(((limit, level) for limit, level in (
            (0, 'AGOTADA'), (5, 'CRITICA'), (10, 'ALTA'), (25, 'ADVERTENCIA'), (50, 'INFORMATIVA')
        ) if available <= limit), None)
        if credit_level:
            limit, level = credit_level
            alerts.append({
                'tipo': 'CREDITOS', 'nivel': level, 'umbral': limit,
                'fundacion_nombre': sub.get('fundacion_nombre'),
                'mensaje': f"Quedan {int(sub.get('creditos_disponibles') or 0)} créditos ({available:.1f}% disponible).",
            })
        projected = sub.get('dias_estimados_agotamiento')
        if projected is not None and int(projected) < max(0, days):
            alerts.append({
                'tipo': 'PROYECCION', 'nivel': 'ALTA', 'umbral': int(projected),
                'fundacion_nombre': sub.get('fundacion_nombre'),
                'mensaje': f'Los créditos podrían agotarse en {int(projected)} día(s), antes del vencimiento.',
            })
        return alerts

    def list_movimientos(self, fundacion_id: int | None = None, limit: int = 500) -> list[dict[str, Any]]:
        if self.repo.is_superadmin() and fundacion_id:
            return self.repo.fetch_all("SELECT m.*, f.nombre AS fundacion_nombre FROM movimientos_credito m LEFT JOIN fundaciones f ON f.id=m.fundacion_id WHERE m.fundacion_id=? ORDER BY m.fecha_movimiento DESC LIMIT ?", (fundacion_id, limit))
        if self.repo.is_superadmin() and not fundacion_id:
            return self.repo.fetch_all("SELECT m.*, f.nombre AS fundacion_nombre FROM movimientos_credito m LEFT JOIN fundaciones f ON f.id=m.fundacion_id ORDER BY m.fecha_movimiento DESC LIMIT ?", (limit,))
        return self.repo.fetch_all("SELECT * FROM movimientos_credito WHERE fundacion_id=? ORDER BY fecha_movimiento DESC LIMIT ?", (self.repo.current_fundacion_id(), limit))

    def list_pagos(self, fundacion_id: int | None = None, limit: int = 500) -> list[dict[str, Any]]:
        if self.repo.is_superadmin() and fundacion_id:
            return self.repo.fetch_all("SELECT p.*, f.nombre AS fundacion_nombre, ps.nombre AS plan_nombre FROM pagos_suscripcion p LEFT JOIN fundaciones f ON f.id=p.fundacion_id LEFT JOIN planes_suscripcion ps ON ps.id=p.plan_id WHERE p.fundacion_id=? ORDER BY p.fecha_pago DESC LIMIT ?", (fundacion_id, limit))
        if self.repo.is_superadmin() and not fundacion_id:
            return self.repo.fetch_all("SELECT p.*, f.nombre AS fundacion_nombre, ps.nombre AS plan_nombre FROM pagos_suscripcion p LEFT JOIN fundaciones f ON f.id=p.fundacion_id LEFT JOIN planes_suscripcion ps ON ps.id=p.plan_id ORDER BY p.fecha_pago DESC LIMIT ?", (limit,))
        return self.repo.fetch_all("SELECT * FROM pagos_suscripcion WHERE fundacion_id=? ORDER BY fecha_pago DESC LIMIT ?", (self.repo.current_fundacion_id(), limit))

    def list_paquetes(self) -> list[dict[str, Any]]:
        return self.repo.fetch_all("SELECT * FROM paquetes_credito ORDER BY creditos, precio")

    def save_paquete(self, data: dict[str, Any], paquete_id: int | None = None) -> dict[str, Any]:
        nombre = (data.get('nombre') or '').strip()
        creditos = int(data.get('creditos') or 0)
        precio = float(data.get('precio') or 0)
        estado = (data.get('estado') or 'ACTIVO').upper()
        personalizado = int(bool(data.get('personalizado')))
        if not nombre:
            raise ValueError('Nombre de paquete requerido.')
        if paquete_id:
            before = self.repo.fetch_one("SELECT * FROM paquetes_credito WHERE id=?", (paquete_id,))
            if not before:
                raise ValueError('Paquete no encontrado.')
            self.repo.execute_update("UPDATE paquetes_credito SET nombre=?, creditos=?, precio=?, estado=?, personalizado=?, fecha_actualizacion=? WHERE id=?", (nombre, creditos, precio, estado, personalizado, now_iso(), paquete_id))
            after = self.repo.fetch_one("SELECT * FROM paquetes_credito WHERE id=?", (paquete_id,)) or {}
            self.repo.log('EDITAR_PAQUETE_CREDITOS', 'paquetes_credito', paquete_id, before, after)
            return after
        new_id = self.repo.execute("INSERT INTO paquetes_credito (nombre, creditos, precio, estado, personalizado, fecha_creacion, fecha_actualizacion) VALUES (?, ?, ?, ?, ?, ?, ?)", (nombre, creditos, precio, estado, personalizado, now_iso(), now_iso()))
        paquete = self.repo.fetch_one("SELECT * FROM paquetes_credito WHERE id=?", (new_id,)) or {}
        self.repo.log('CREAR_PAQUETE_CREDITOS', 'paquetes_credito', new_id, despues=paquete)
        return paquete


def _json_error(message: str, status: int = 403):
    return jsonify({'error': message}), status


def register_billing_middleware(app, database_path: str, upload_folder: str | None = None) -> None:
    repo = BillingRepository(database_path)
    service = BillingService(repo, upload_folder)
    service.init(force=migration_mode())

    @app.before_request
    def _billing_before_request():
        if not request.path.startswith('/api/'):
            return None
        if request.method == 'OPTIONS':
            return None
        if request.path.startswith('/api/auth') or request.path.startswith('/api/health'):
            return None
        user = getattr(g, 'current_user', None)
        if not user:
            return None
        if user.get('rol') == 'SUPERADMIN':
            return None
        fid = int(user.get('fundacion_id') or 1)
        sub = service.get_subscription_snapshot(fid)
        if not sub:
            return _json_error('La fundación no tiene suscripción configurada.', 402)

        # La fundación siempre puede ver y regularizar su facturación o crear tickets comerciales/soporte.
        if request.path.startswith('/api/facturacion') or request.path.startswith('/api/panel-comercial'):
            g.billing_subscription = sub
            return None

        if app.config.get('ENFORCE_LOGIN_BILLING', False) and int(sub.get('creditos_disponibles') or 0) <= 0:
            return _json_error('Acceso bloqueado: la fundación agotó sus créditos. Registra una recarga para continuar.', 402)

        module = service.module_for_path(request.path)
        if module:
            enabled = set(sub.get('modulos_habilitados') or [])
            if module not in enabled and 'todos' not in enabled:
                return _json_error(f'El módulo {module} no está habilitado en tu plan.', 403)

        estado = (sub.get('estado') or 'ACTIVA').upper()
        if estado in {'SUSPENDIDA', 'CANCELADA'}:
            if request.method == 'GET':
                return None
            return _json_error(f'La suscripción está {estado.lower()}. Solo puedes consultar información y registrar pago.', 402)
        if sub.get('gracia_vencida'):
            if request.method == 'GET':
                return None
            return _json_error('La suscripción está vencida y superó los días de gracia. Registra un pago para reactivar.', 402)

        rule = service.credit_rule_for_request(request.path, request.method) if app.config.get('ENABLE_CREDIT_ENFORCEMENT', False) else None
        if rule:
            request_data = request.get_json(silent=True) if request.is_json else request.form
            idempotency_key = (
                request.headers.get('Idempotency-Key') or request.headers.get('X-Idempotency-Key')
                or request.headers.get('X-Request-ID') or (request_data or {}).get('idempotency_key')
            )
            if not idempotency_key:
                return _json_error('Esta operación requiere Idempotency-Key para proteger el cobro.', 400)
            saldo = int(sub.get('creditos_disponibles') or 0)
            if saldo < int(rule.get('costo') or 0):
                return _json_error('Créditos insuficientes. Compra o solicita asignación de nuevos créditos.', 402)
            g.billing_credit_rule = rule
            g.billing_credit_fundacion_id = fid
            g.billing_credit_idempotency_key = str(idempotency_key)
        g.billing_subscription = sub
        return None

    @app.after_request
    def _billing_after_request(response):
        rule = getattr(g, 'billing_credit_rule', None)
        fid = getattr(g, 'billing_credit_fundacion_id', None)
        idempotency_key = getattr(g, 'billing_credit_idempotency_key', None)
        if rule and fid and 200 <= int(response.status_code) < 300:
            try:
                service.consumir_creditos(
                    int(fid),
                    rule['accion'],
                    referencia_tipo='endpoint',
                    referencia_id=request.path,
                    descripcion=f"Consumo automático por {request.method} {request.path}",
                    idempotency_key=idempotency_key,
                )
                response.headers['X-Credit-Charge'] = 'confirmed'
            except Exception:
                app.logger.exception('[CREDITS] automatic_charge_failed path=%s fundacion_id=%s', request.path, fid)
                response.headers['X-Credit-Charge'] = 'failed'
        sub = getattr(g, 'billing_subscription', None)
        if sub and response is not None:
            try:
                response.headers['X-Subscription-Status'] = str(sub.get('estado') or '')
                response.headers['X-Subscription-Credits'] = str(sub.get('creditos_disponibles') or 0)
                if sub.get('en_gracia'):
                    response.headers['X-Subscription-Warning'] = 'La suscripción está en días de gracia.'
            except Exception:
                pass
        return response
