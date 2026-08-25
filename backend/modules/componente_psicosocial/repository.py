"""Capa especializada del componente psicosocial.

Enlaza el expediente familiar y los productos transversales existentes. Las
caracterizaciones y planes se almacenan por versiones y nunca se cierran sin
validación humana.
"""
from __future__ import annotations

import json
import mimetypes
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from modules.dbapi_compat import sqlite3
from modules.seguridad.tenant_context import tenant_storage_root
from modules.motor_gestion_proyecto.services import source_key as mgp_source_key

from .schema import SCHEMA_SQL, SCHEMA_VERSION
from .services import COMPLETED_STATES, file_sha256, json_dump, normalize, now_iso, parse_json, unit_key


class ComponentePsicosocialRepository:
    def __init__(self, database_path: str, data_dir: str, output_folder: str):
        self.database_path = str(database_path)
        self.data_dir = Path(data_dir).resolve()
        self.output_folder = Path(output_folder).resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.output_folder.mkdir(parents=True, exist_ok=True)

    def connect(self):
        conn = sqlite3.connect(self.database_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    @staticmethod
    def _table_exists(conn, table: str) -> bool:
        return bool(conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone())

    @staticmethod
    def _columns(conn, table: str) -> set[str]:
        if not ComponentePsicosocialRepository._table_exists(conn, table):
            return set()
        return {str(row[1]) for row in conn.execute(f'PRAGMA table_info("{table}")').fetchall()}

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.execute(
                "INSERT INTO ps_schema_version(id,version,fecha_actualizacion) VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET version=excluded.version,fecha_actualizacion=excluded.fecha_actualizacion",
                (SCHEMA_VERSION, now_iso()),
            )
            conn.commit()

    def audit(self, fundacion_id: int, user: dict[str, Any], action: str, expediente_id: int | None, detail: dict[str, Any] | None = None, conn=None) -> None:
        own = conn is None; target = conn or self.connect()
        try:
            target.execute(
                "INSERT INTO ps_auditoria_accesos(fundacion_id,expediente_id,usuario_id,usuario,rol,accion,detalle_json,fecha) VALUES(?,?,?,?,?,?,?,?)",
                (fundacion_id, expediente_id, user.get("id"), user.get("username") or user.get("email") or "sistema", user.get("rol"), action, json_dump(detail or {}), now_iso()),
            )
            if own: target.commit()
        finally:
            if own: target.close()

    def sync_expedientes(self, fundacion_id: int, user: dict[str, Any], unit: str | None = None) -> dict[str, Any]:
        now = now_iso(); created = updated = 0
        with self.connect() as conn:
            if not self._table_exists(conn, "fcr_expedientes_familiares"):
                return {"creados": 0, "actualizados": 0, "mensaje": "Primero sincroniza Gestión de Familias y Redes."}
            where = ["fundacion_id=?", "estado='ACTIVO'"]; params: list[Any] = [fundacion_id]
            if unit:
                where.append("UPPER(COALESCE(unidad_nombre,''))=UPPER(?)"); params.append(unit)
            rows = conn.execute("SELECT * FROM fcr_expedientes_familiares WHERE " + " AND ".join(where), params).fetchall()
            for row in rows:
                existing = conn.execute("SELECT id FROM ps_expedientes WHERE fundacion_id=? AND fcr_expediente_familiar_id=?", (fundacion_id, row["id"])).fetchone()
                values = (
                    row["expediente_uca_id"], row["unidad_nombre"], row["unidad_clave"], row["participante_origen"], row["participante_id"],
                    user.get("id") if user.get("rol") == "PSICOSOCIAL" else None,
                    user.get("nombre_completo") or user.get("username") if user.get("rol") == "PSICOSOCIAL" else None,
                    user.get("id"), now,
                )
                if existing:
                    conn.execute(
                        """UPDATE ps_expedientes SET expediente_uca_id=?,unidad_nombre=?,unidad_clave=?,participante_origen=?,participante_id=?,
                        profesional_referente_id=COALESCE(profesional_referente_id,?),profesional_referente_nombre=COALESCE(profesional_referente_nombre,?),
                        actualizado_por=?,fecha_actualizacion=? WHERE fundacion_id=? AND id=?""",
                        values + (fundacion_id, int(existing[0])),
                    ); updated += 1
                else:
                    conn.execute(
                        """INSERT INTO ps_expedientes
                        (fundacion_id,fcr_expediente_familiar_id,expediente_uca_id,unidad_nombre,unidad_clave,participante_origen,participante_id,
                         profesional_referente_id,profesional_referente_nombre,nivel_acceso,estado,motivo_apertura,fecha_apertura,
                         creado_por,actualizado_por,fecha_creacion,fecha_actualizacion)
                        VALUES(?,?,?,?,?,?,?,?,?,'RESTRINGIDO','ACTIVO','Sincronización referencial',?,?,?,?,?)""",
                        (fundacion_id, row["id"], row["expediente_uca_id"], row["unidad_nombre"], row["unidad_clave"], row["participante_origen"], row["participante_id"],
                         values[5], values[6], date.today().isoformat(), user.get("id"), user.get("id"), now, now),
                    ); created += 1
            self.audit(fundacion_id, user, "SINCRONIZAR_EXPEDIENTES", None, {"creados": created, "actualizados": updated}, conn)
            conn.commit()
        return {"creados": created, "actualizados": updated, "mensaje": "Sincronización referencial completada."}

    def _participant(self, conn, source: str, participant_id: int, fundacion_id: int) -> dict[str, Any] | None:
        if source not in {"master_ninos", "beneficiarios", "usuarios"} or not self._table_exists(conn, source):
            return None
        cols = self._columns(conn, source); where = ["id=?"]; params: list[Any] = [participant_id]
        if "fundacion_id" in cols: where.append("fundacion_id=?"); params.append(fundacion_id)
        row = conn.execute(f'SELECT * FROM "{source}" WHERE ' + " AND ".join(where), params).fetchone()
        if not row: return None
        data = dict(row)
        def pick(*names):
            for name in names:
                if data.get(name) not in (None, ""): return data.get(name)
            return None
        documento = pick("documento","numero_documento","identificacion")
        origen_efectivo = source
        # Los expedientes históricos conservan su referencia, pero su identidad
        # visible se resuelve desde la versión maestra vigente por documento.
        if source != "master_ninos" and documento and self._table_exists(conn, "master_ninos"):
            canonical = conn.execute(
                """SELECT * FROM master_ninos WHERE fundacion_id=? AND activo=1
                   AND documento=? ORDER BY id DESC LIMIT 1""",
                (fundacion_id, str(documento).strip()),
            ).fetchone()
            if canonical:
                data = dict(canonical); participant_id = int(data.get("id") or participant_id)
                origen_efectivo = "master_ninos"
                documento = data.get("documento")
        nombre = data.get("nombre_completo") or data.get("nombre") or data.get("nombres") or f"Participante #{participant_id}"
        return {"id": participant_id, "origen": origen_efectivo, "documento": documento, "nombre": nombre, "raw": data}

    def list_expedientes(self, fundacion_id: int, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        filters = filters or {}; where=["p.fundacion_id=?"]; params: list[Any]=[fundacion_id]
        if filters.get("unidad"): where.append("UPPER(COALESCE(p.unidad_nombre,'')) LIKE UPPER(?)"); params.append(f"%{filters['unidad']}%")
        if filters.get("estado"): where.append("p.estado=?"); params.append(normalize(filters["estado"]))
        if filters.get("profesional_id"): where.append("p.profesional_referente_id=?"); params.append(int(filters["profesional_id"]))
        with self.connect() as conn:
            rows=conn.execute(
                """SELECT p.*,f.cuidador_principal,f.parentesco,f.telefono_principal,f.correo,f.direccion,f.caracterizacion_json
                   FROM ps_expedientes p JOIN fcr_expedientes_familiares f ON f.id=p.fcr_expediente_familiar_id
                   WHERE """+" AND ".join(where)+" ORDER BY p.unidad_nombre,p.id",params).fetchall()
            result=[]
            for row in rows:
                item=dict(row); participant=self._participant(conn,item.get("participante_origen") or "master_ninos",int(item.get("participante_id") or 0),fundacion_id)
                item["participante"]=participant; item["nombre_participante"]=(participant or {}).get("nombre") or f"Participante #{item.get('participante_id')}"
                item["documento_participante"]=(participant or {}).get("documento")
                item["caracterizacion_familiar"]=parse_json(item.get("caracterizacion_json"),{})
                item["ultima_caracterizacion"]=self._latest_characterization(conn,fundacion_id,int(item["id"]))
                item["planes_abiertos"]=int(conn.execute("SELECT COUNT(*) FROM ps_planes_acompanamiento WHERE fundacion_id=? AND expediente_id=? AND estado NOT IN ('CERRADO','CANCELADO')",(fundacion_id,item["id"])).fetchone()[0])
                item["acciones_pendientes"]=int(conn.execute("SELECT COUNT(*) FROM ps_acciones_plan a JOIN ps_planes_acompanamiento p2 ON p2.id=a.plan_id WHERE a.fundacion_id=? AND p2.expediente_id=? AND a.estado NOT IN ('COMPLETADA','VALIDADA','CANCELADA')",(fundacion_id,item["id"])).fetchone()[0])
                result.append(item)
        return result

    def expediente(self, fundacion_id: int, expediente_id: int, user: dict[str, Any] | None = None) -> dict[str, Any]:
        matches=[row for row in self.list_expedientes(fundacion_id) if int(row["id"])==int(expediente_id)]
        if not matches: raise LookupError("Expediente psicosocial no encontrado.")
        item=matches[0]
        with self.connect() as conn:
            item["caracterizaciones"]=[self._characterization(dict(row)) for row in conn.execute("SELECT * FROM ps_caracterizaciones WHERE fundacion_id=? AND expediente_id=? ORDER BY version DESC",(fundacion_id,expediente_id)).fetchall()]
            item["planes"]=[self._plan_detail(conn,dict(row)) for row in conn.execute("SELECT * FROM ps_planes_acompanamiento WHERE fundacion_id=? AND expediente_id=? ORDER BY fecha_creacion DESC",(fundacion_id,expediente_id)).fetchall()]
            item["actividades_vinculadas"]=[dict(row) for row in conn.execute("""SELECT v.*,a.tipo,a.titulo,a.fecha_programada,a.fecha_ejecucion,a.estado,a.profesional_nombre FROM ps_vinculos_actividad v JOIN fcr_actividades a ON a.id=v.fcr_actividad_id WHERE v.fundacion_id=? AND v.expediente_id=? ORDER BY a.fecha_programada DESC""",(fundacion_id,expediente_id)).fetchall()]
            item["seguimientos"]=[dict(row) for row in conn.execute("SELECT * FROM ps_seguimientos WHERE fundacion_id=? AND expediente_id=? ORDER BY fecha DESC,id DESC",(fundacion_id,expediente_id)).fetchall()]
            item["documentos"]=[dict(row) for row in conn.execute("SELECT * FROM ps_documentos WHERE fundacion_id=? AND expediente_id=? ORDER BY fecha_generacion DESC",(fundacion_id,expediente_id)).fetchall()]
        if user: self.audit(fundacion_id,user,"CONSULTAR_EXPEDIENTE",expediente_id,{"nivel_acceso":item.get("nivel_acceso")})
        return item

    def _latest_characterization(self, conn, fundacion_id: int, expediente_id: int) -> dict[str, Any] | None:
        row=conn.execute("SELECT * FROM ps_caracterizaciones WHERE fundacion_id=? AND expediente_id=? AND activo=1 ORDER BY version DESC LIMIT 1",(fundacion_id,expediente_id)).fetchone()
        return self._characterization(dict(row)) if row else None

    @staticmethod
    def _characterization(data: dict[str, Any]) -> dict[str, Any]:
        for key in ("composicion_familiar_json","dinamicas_cuidado_json","factores_protectores_json","situaciones_acompanar_json","redes_presentes_json","barreras_acceso_json","enfoque_diferencial_json"):
            data[key.replace("_json","")]=parse_json(data.get(key),[] if key.endswith("es_json") or key.startswith(("factores","situaciones","redes","barreras")) else {})
        return data

    def create_characterization(self,fundacion_id:int,expediente_id:int,data:dict[str,Any],user:dict[str,Any])->dict[str,Any]:
        self.expediente(fundacion_id,expediente_id)
        now=now_iso()
        with self.connect() as conn:
            version=int(conn.execute("SELECT COALESCE(MAX(version),0)+1 FROM ps_caracterizaciones WHERE fundacion_id=? AND expediente_id=?",(fundacion_id,expediente_id)).fetchone()[0])
            conn.execute("UPDATE ps_caracterizaciones SET activo=0,fecha_actualizacion=? WHERE fundacion_id=? AND expediente_id=? AND activo=1",(now,fundacion_id,expediente_id))
            cur=conn.execute("""INSERT INTO ps_caracterizaciones
            (fundacion_id,expediente_id,version,fecha_caracterizacion,tipo,composicion_familiar_json,dinamicas_cuidado_json,
             factores_protectores_json,situaciones_acompanar_json,redes_presentes_json,barreras_acceso_json,enfoque_diferencial_json,
             conclusion_profesional,recomendaciones,estado,activo,elaborado_por,fecha_creacion,fecha_actualizacion)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'BORRADOR',1,?,?,?)""",
            (fundacion_id,expediente_id,version,data.get("fecha_caracterizacion") or date.today().isoformat(),normalize(data.get("tipo")) or "SEGUIMIENTO",
             json_dump(data.get("composicion_familiar") or {}),json_dump(data.get("dinamicas_cuidado") or {}),json_dump(data.get("factores_protectores") or []),
             json_dump(data.get("situaciones_acompanar") or []),json_dump(data.get("redes_presentes") or []),json_dump(data.get("barreras_acceso") or []),
             json_dump(data.get("enfoque_diferencial") or {}),data.get("conclusion_profesional"),data.get("recomendaciones"),user.get("id"),now,now))
            char_id=int(cur.lastrowid); self.audit(fundacion_id,user,"CREAR_CARACTERIZACION",expediente_id,{"caracterizacion_id":char_id,"version":version},conn);conn.commit()
        return next(x for x in self.expediente(fundacion_id,expediente_id)["caracterizaciones"] if x["id"]==char_id)

    def review_characterization(self,fundacion_id:int,characterization_id:int,user:dict[str,Any],approve:bool=False)->dict[str,Any]:
        now=now_iso();state="VALIDADA" if approve else "REVISADA"
        with self.connect() as conn:
            row=conn.execute("SELECT * FROM ps_caracterizaciones WHERE fundacion_id=? AND id=?",(fundacion_id,characterization_id)).fetchone()
            if not row: raise LookupError("Caracterización no encontrada.")
            conn.execute("UPDATE ps_caracterizaciones SET estado=?,revisado_por=?,fecha_revision=?,fecha_actualizacion=? WHERE fundacion_id=? AND id=?",(state,user.get("id"),now,now,fundacion_id,characterization_id))
            self.audit(fundacion_id,user,"VALIDAR_CARACTERIZACION" if approve else "REVISAR_CARACTERIZACION",row["expediente_id"],{"caracterizacion_id":characterization_id},conn);conn.commit()
        return self._characterization(dict(row)|{"estado":state,"revisado_por":user.get("id"),"fecha_revision":now})

    def create_plan(self,fundacion_id:int,expediente_id:int,data:dict[str,Any],user:dict[str,Any])->dict[str,Any]:
        current=self.expediente(fundacion_id,expediente_id);name=str(data.get("nombre") or "").strip();objective=str(data.get("objetivo_general") or "").strip()
        if not name or not objective: raise ValueError("Nombre y objetivo general son obligatorios.")
        now=now_iso()
        with self.connect() as conn:
            cur=conn.execute("""INSERT INTO ps_planes_acompanamiento
            (fundacion_id,expediente_id,caracterizacion_id,nombre,objetivo_general,fecha_inicio,fecha_fin_estimada,estado,prioridad,porcentaje,
             creado_por,actualizado_por,fecha_creacion,fecha_actualizacion)
            VALUES(?,?,?,?,?,?,?,'BORRADOR',?,0,?,?,?,?)""",
            (fundacion_id,expediente_id,data.get("caracterizacion_id"),name,objective,data.get("fecha_inicio") or date.today().isoformat(),data.get("fecha_fin_estimada"),normalize(data.get("prioridad")) or "MEDIA",user.get("id"),user.get("id"),now,now))
            plan_id=int(cur.lastrowid);self.audit(fundacion_id,user,"CREAR_PLAN",expediente_id,{"plan_id":plan_id},conn);conn.commit()
        return self.plan(fundacion_id,plan_id)

    def _plan_detail(self,conn,data:dict[str,Any])->dict[str,Any]:
        data["acciones"]=[dict(row) for row in conn.execute("SELECT * FROM ps_acciones_plan WHERE fundacion_id=? AND plan_id=? ORDER BY fecha_limite,id",(data["fundacion_id"],data["id"])).fetchall()]
        return data

    def plan(self,fundacion_id:int,plan_id:int)->dict[str,Any]:
        with self.connect() as conn:
            row=conn.execute("SELECT * FROM ps_planes_acompanamiento WHERE fundacion_id=? AND id=?",(fundacion_id,plan_id)).fetchone()
            if not row: raise LookupError("Plan no encontrado.")
            return self._plan_detail(conn,dict(row))

    def create_action(self,fundacion_id:int,plan_id:int,data:dict[str,Any],user:dict[str,Any])->dict[str,Any]:
        plan=self.plan(fundacion_id,plan_id);exp=self.expediente(fundacion_id,int(plan["expediente_id"]));title=str(data.get("titulo") or "").strip()
        if not title: raise ValueError("Título es obligatorio.")
        now=now_iso()
        with self.connect() as conn:
            cur=conn.execute("""INSERT INTO ps_acciones_plan
            (fundacion_id,plan_id,expediente_uca_id,unidad_nombre,titulo,descripcion,tipo_accion,fecha_inicio,fecha_limite,
             responsable_id,responsable_nombre,prioridad,estado,porcentaje,requiere_evidencia,fcr_actividad_id,fcr_compromiso_id,
             creado_por,actualizado_por,fecha_creacion,fecha_actualizacion)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?, 'PENDIENTE',0,?,?,?,?,?,?,?)""",
            (fundacion_id,plan_id,exp.get("expediente_uca_id"),exp.get("unidad_nombre"),title,data.get("descripcion"),normalize(data.get("tipo_accion")) or "ACOMPANAMIENTO",
             data.get("fecha_inicio") or date.today().isoformat(),data.get("fecha_limite"),data.get("responsable_id") or user.get("id"),data.get("responsable_nombre") or user.get("nombre_completo") or user.get("username"),
             normalize(data.get("prioridad")) or "MEDIA",1 if data.get("requiere_evidencia") else 0,data.get("fcr_actividad_id"),data.get("fcr_compromiso_id"),user.get("id"),user.get("id"),now,now))
            action_id=int(cur.lastrowid);self._upsert_motor_action(conn,fundacion_id,action_id,user);self.audit(fundacion_id,user,"CREAR_ACCION",exp["id"],{"plan_id":plan_id,"accion_id":action_id},conn);conn.commit()
        return next(x for x in self.plan(fundacion_id,plan_id)["acciones"] if x["id"]==action_id)

    def update_action(self,fundacion_id:int,action_id:int,data:dict[str,Any],user:dict[str,Any],allow_validate:bool=False)->dict[str,Any]:
        with self.connect() as conn:
            row=conn.execute("SELECT * FROM ps_acciones_plan WHERE fundacion_id=? AND id=?",(fundacion_id,action_id)).fetchone()
            if not row: raise LookupError("Acción no encontrada.")
            current=dict(row);state=normalize(data.get("estado") or current["estado"]);percent=float(data.get("porcentaje",current.get("porcentaje") or 0));evidence=data.get("evidencia_referencia") or current.get("evidencia_referencia")
            if state in {"VALIDADA","CERRADA"} and not allow_validate: raise PermissionError("La validación requiere coordinación.")
            if state in COMPLETED_STATES and percent<100: raise ValueError("La acción debe registrar 100% de avance.")
            if state in COMPLETED_STATES and current.get("requiere_evidencia") and not evidence: raise ValueError("La acción requiere evidencia.")
            now=now_iso();conn.execute("""UPDATE ps_acciones_plan SET estado=?,porcentaje=?,resultado=COALESCE(?,resultado),evidencia_referencia=COALESCE(?,evidencia_referencia),
            completada_por=CASE WHEN ? IN ('COMPLETADA','VALIDADA','CERRADA') THEN ? ELSE completada_por END,
            validada_por=CASE WHEN ? IN ('VALIDADA','CERRADA') THEN ? ELSE validada_por END,
            fecha_completada=CASE WHEN ? IN ('COMPLETADA','VALIDADA','CERRADA') THEN ? ELSE fecha_completada END,
            actualizado_por=?,fecha_actualizacion=? WHERE fundacion_id=? AND id=?""",
            (state,percent,data.get("resultado"),data.get("evidencia_referencia"),state,user.get("id"),state,user.get("id"),state,now,user.get("id"),now,fundacion_id,action_id))
            self._upsert_motor_action(conn,fundacion_id,action_id,user);self._recalculate_plan(conn,fundacion_id,int(current["plan_id"]));self.audit(fundacion_id,user,"ACTUALIZAR_ACCION",None,{"accion_id":action_id,"estado":state},conn);conn.commit()
        return next(x for x in self.plan(fundacion_id,int(current["plan_id"]))["acciones"] if x["id"]==action_id)

    def _recalculate_plan(self,conn,fundacion_id:int,plan_id:int)->None:
        rows=conn.execute("SELECT estado,porcentaje FROM ps_acciones_plan WHERE fundacion_id=? AND plan_id=?",(fundacion_id,plan_id)).fetchall()
        percent=round(sum(float(row["porcentaje"] or 0) for row in rows)/len(rows),2) if rows else 0
        state="EN_PROCESO" if rows and percent>0 else "BORRADOR"
        if rows and all(normalize(row["estado"]) in COMPLETED_STATES for row in rows): state="PENDIENTE_CIERRE"
        conn.execute("UPDATE ps_planes_acompanamiento SET porcentaje=?,estado=CASE WHEN estado IN ('CERRADO','CANCELADO') THEN estado ELSE ? END,fecha_actualizacion=? WHERE fundacion_id=? AND id=?",(percent,state,now_iso(),fundacion_id,plan_id))

    def close_plan(self,fundacion_id:int,plan_id:int,data:dict[str,Any],user:dict[str,Any])->dict[str,Any]:
        plan=self.plan(fundacion_id,plan_id)
        if not plan.get("acciones"): raise ValueError("El plan requiere al menos una acción.")
        if any(normalize(a.get("estado")) not in COMPLETED_STATES for a in plan["acciones"]): raise ValueError("Todas las acciones deben estar completadas y validadas.")
        result=str(data.get("resultado_final") or "").strip()
        if not result: raise ValueError("El resultado final es obligatorio.")
        now=now_iso()
        with self.connect() as conn:
            conn.execute("UPDATE ps_planes_acompanamiento SET estado='CERRADO',porcentaje=100,resultado_final=?,fecha_cierre=?,cierre_validado_por=?,actualizado_por=?,fecha_actualizacion=? WHERE fundacion_id=? AND id=?",(result,now,user.get("id"),user.get("id"),now,fundacion_id,plan_id))
            self.audit(fundacion_id,user,"CERRAR_PLAN",plan["expediente_id"],{"plan_id":plan_id},conn);conn.commit()
        return self.plan(fundacion_id,plan_id)

    def link_activity(self,fundacion_id:int,expediente_id:int,activity_id:int,user:dict[str,Any])->dict[str,Any]:
        exp=self.expediente(fundacion_id,expediente_id)
        with self.connect() as conn:
            row=conn.execute("SELECT * FROM fcr_actividades WHERE fundacion_id=? AND id=?",(fundacion_id,activity_id)).fetchone()
            if not row: raise LookupError("Actividad de Familias y Redes no encontrada.")
            if unit_key(row["unidad_nombre"])!=unit_key(exp.get("unidad_nombre")): raise ValueError("La actividad pertenece a otra UCA.")
            conn.execute("INSERT INTO ps_vinculos_actividad(fundacion_id,expediente_id,fcr_actividad_id,tipo_vinculo,observaciones,creado_por,fecha_creacion) VALUES(?,?,?,?,?,?,?) ON CONFLICT(fundacion_id,expediente_id,fcr_actividad_id) DO NOTHING",(fundacion_id,expediente_id,activity_id,"INTERVENCION",None,user.get("id"),now_iso()))
            self.audit(fundacion_id,user,"VINCULAR_ACTIVIDAD",expediente_id,{"fcr_actividad_id":activity_id},conn);conn.commit()
        return self.expediente(fundacion_id,expediente_id)

    def add_followup(self,fundacion_id:int,expediente_id:int,data:dict[str,Any],user:dict[str,Any])->dict[str,Any]:
        self.expediente(fundacion_id,expediente_id);description=str(data.get("descripcion") or "").strip()
        if not description: raise ValueError("La descripción es obligatoria.")
        now=now_iso()
        with self.connect() as conn:
            cur=conn.execute("""INSERT INTO ps_seguimientos(fundacion_id,expediente_id,plan_id,accion_id,fecha,tipo,descripcion,resultado,proxima_accion,fecha_proximo_seguimiento,evidencia_referencia,creado_por,fecha_creacion)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",(fundacion_id,expediente_id,data.get("plan_id"),data.get("accion_id"),data.get("fecha") or date.today().isoformat(),normalize(data.get("tipo")) or "SEGUIMIENTO",description,data.get("resultado"),data.get("proxima_accion"),data.get("fecha_proximo_seguimiento"),data.get("evidencia_referencia"),user.get("id"),now))
            sid=int(cur.lastrowid);self.audit(fundacion_id,user,"REGISTRAR_SEGUIMIENTO",expediente_id,{"seguimiento_id":sid},conn);conn.commit()
        return next(x for x in self.expediente(fundacion_id,expediente_id)["seguimientos"] if x["id"]==sid)

    def dashboard(self,fundacion_id:int,user:dict[str,Any],filters:dict[str,Any]|None=None)->dict[str,Any]:
        filters=dict(filters or {})
        if user.get("rol")=="PSICOSOCIAL": filters["profesional_id"]=user.get("id")
        cases=self.list_expedientes(fundacion_id,filters)
        ids=[int(x["id"]) for x in cases]
        plans=[];actions=[];followups=[]
        with self.connect() as conn:
            if ids:
                marks=','.join('?' for _ in ids)
                plans=[dict(r) for r in conn.execute(f"SELECT * FROM ps_planes_acompanamiento WHERE fundacion_id=? AND expediente_id IN ({marks}) ORDER BY fecha_creacion DESC",[fundacion_id]+ids).fetchall()]
                plan_ids=[int(x["id"]) for x in plans]
                if plan_ids:
                    pmarks=','.join('?' for _ in plan_ids);actions=[dict(r) for r in conn.execute(f"SELECT * FROM ps_acciones_plan WHERE fundacion_id=? AND plan_id IN ({pmarks}) ORDER BY fecha_limite",[fundacion_id]+plan_ids).fetchall()]
                followups=[dict(r) for r in conn.execute(f"SELECT * FROM ps_seguimientos WHERE fundacion_id=? AND expediente_id IN ({marks}) ORDER BY fecha DESC",[fundacion_id]+ids).fetchall()]
        by_unit=defaultdict(lambda:{"expedientes":0,"planes_abiertos":0,"acciones_pendientes":0})
        case_by_id={int(x["id"]):x for x in cases};plan_by_id={int(x["id"]):x for x in plans}
        for c in cases: by_unit[c.get("unidad_nombre") or "Sin UCA"]["expedientes"]+=1
        for p in plans:
            if normalize(p.get("estado")) not in {"CERRADO","CANCELADO"}: by_unit[(case_by_id.get(int(p["expediente_id"])) or {}).get("unidad_nombre") or "Sin UCA"]["planes_abiertos"]+=1
        for a in actions:
            if normalize(a.get("estado")) not in COMPLETED_STATES|{"CANCELADA"}:
                p=plan_by_id.get(int(a["plan_id"]));c=case_by_id.get(int(p["expediente_id"])) if p else None;by_unit[(c or {}).get("unidad_nombre") or "Sin UCA"]["acciones_pendientes"]+=1
        return {"vista":"COORDINACION" if user.get("rol") in COORDINATION_ROLES else "PROFESIONAL","resumen":{"expedientes":len(cases),"sin_caracterizacion":sum(1 for c in cases if not c.get("ultima_caracterizacion")),"planes_abiertos":sum(1 for p in plans if normalize(p.get("estado")) not in {"CERRADO","CANCELADO"}),"acciones_pendientes":sum(1 for a in actions if normalize(a.get("estado")) not in COMPLETED_STATES|{"CANCELADA"}),"seguimientos":len(followups)},"por_uca":[{"unidad":k,**v} for k,v in sorted(by_unit.items())],"expedientes":cases[:200],"planes":plans[:200],"acciones":actions[:300],"seguimientos":followups[:200]}

    def prepare_report(self,fundacion_id:int,expediente_id:int,user:dict[str,Any],include_restricted:bool=False)->dict[str,Any]:
        exp=self.expediente(fundacion_id,expediente_id,user);folder=tenant_storage_root(self.data_dir,fundacion_id).resolve()/"psicosocial"/"documentos";folder.mkdir(parents=True,exist_ok=True);token=datetime.now().strftime("%Y%m%d_%H%M%S");path=folder/f"informe_psicosocial_exp_{expediente_id}_{token}.pdf"
        styles=getSampleStyleSheet();story=[Paragraph("INFORME PSICOSOCIAL — BORRADOR PARA REVISIÓN HUMANA",styles["Title"]),Spacer(1,.3*cm)]
        info=[["Participante",exp.get("nombre_participante") or ""],["Documento",exp.get("documento_participante") or ""],["UCA",exp.get("unidad_nombre") or ""],["Profesional referente",exp.get("profesional_referente_nombre") or ""],["Estado",exp.get("estado") or ""]]
        table=Table(info,colWidths=[4*cm,12*cm]);table.setStyle(TableStyle([("BACKGROUND",(0,0),(0,-1),colors.HexColor("#7c3aed")),("TEXTCOLOR",(0,0),(0,-1),colors.white),("GRID",(0,0),(-1,-1),.4,colors.grey),("VALIGN",(0,0),(-1,-1),"TOP")]))
        story.append(table);story.append(Spacer(1,.4*cm))
        latest=exp.get("ultima_caracterizacion") or {}
        sections=[("Síntesis de caracterización",latest.get("conclusion_profesional") if include_restricted else "Contenido restringido: consultar expediente con permisos autorizados."),("Factores protectores",", ".join(latest.get("factores_protectores") or []) if include_restricted else "Resumen disponible para el profesional autorizado."),("Situaciones a acompañar",", ".join(latest.get("situaciones_acompanar") or []) if include_restricted else "Resumen restringido."),("Planes de acompañamiento",f"{len(exp.get('planes') or [])} plan(es) registrados."),("Seguimientos",f"{len(exp.get('seguimientos') or [])} seguimiento(s) registrados."),("Conclusiones profesionales","Pendiente de revisión, firma y aprobación humana.")]
        for title,text in sections: story.append(Paragraph(f"<b>{title}</b>",styles["Heading3"]));story.append(Paragraph(str(text or "Sin registro."),styles["BodyText"]));story.append(Spacer(1,.25*cm))
        SimpleDocTemplate(str(path),pagesize=A4,rightMargin=1.5*cm,leftMargin=1.5*cm,topMargin=1.5*cm,bottomMargin=1.5*cm).build(story)
        now=now_iso();digest=file_sha256(path)
        with self.connect() as conn:
            cur=conn.execute("""INSERT INTO ps_documentos(fundacion_id,expediente_id,tipo_documento,nombre_archivo,ruta_archivo,mime_type,tamano_bytes,sha256,estado,contiene_datos_restringidos,generado_por,fecha_generacion)
            VALUES(?,?, 'INFORME_PSICOSOCIAL',?,?,?,?,?,'BORRADOR',?,?,?)""",(fundacion_id,expediente_id,path.name,str(path),"application/pdf",path.stat().st_size,digest,1 if include_restricted else 0,user.get("id"),now))
            doc_id=int(cur.lastrowid);self.audit(fundacion_id,user,"GENERAR_INFORME",expediente_id,{"documento_id":doc_id,"restringido":include_restricted},conn);conn.commit()
        return self.document(fundacion_id,doc_id)

    def document(self,fundacion_id:int,document_id:int)->dict[str,Any]:
        with self.connect() as conn:
            row=conn.execute("SELECT d.*,p.unidad_nombre FROM ps_documentos d JOIN ps_expedientes p ON p.id=d.expediente_id WHERE d.fundacion_id=? AND d.id=?",(fundacion_id,document_id)).fetchone()
        if not row: raise LookupError("Documento no encontrado.")
        return dict(row)

    def document_path(self,fundacion_id:int,document_id:int)->tuple[Path,str,str]|None:
        row=self.document(fundacion_id,document_id);path=Path(row["ruta_archivo"]).resolve();root=tenant_storage_root(self.data_dir,fundacion_id).resolve()
        try:path.relative_to(root)
        except ValueError:return None
        if not path.is_file() or file_sha256(path)!=row["sha256"]:return None
        return path,row["nombre_archivo"],row.get("mime_type") or mimetypes.guess_type(path.name)[0] or "application/octet-stream"

    def _upsert_motor_action(self,conn,fundacion_id:int,action_id:int,user:dict[str,Any])->None:
        if not self._table_exists(conn,"mgp_tareas"):return
        row=conn.execute("SELECT * FROM ps_acciones_plan WHERE fundacion_id=? AND id=?",(fundacion_id,action_id)).fetchone()
        if not row:return
        item=dict(row);key=mgp_source_key("ps_acciones_plan",action_id);now=now_iso();score=90 if normalize(item.get("prioridad"))=="CRITICA" else 70 if normalize(item.get("prioridad"))=="ALTA" else 40
        conn.execute("""INSERT INTO mgp_tareas
        (fundacion_id,expediente_id,unidad_nombre,unidad_clave,fuente_modulo,fuente_tabla,fuente_id,fuente_clave,tipo_tarea,componente,titulo,descripcion,
         fecha_inicio,fecha_limite,fecha_finalizacion,estado,prioridad,puntaje_prioridad,responsable_id,responsable_nombre,requiere_evidencia,
         evidencias_total,bloqueada,metadata_json,activa,creada_por,actualizada_por,fecha_creacion,fecha_actualizacion)
        VALUES(?,?,?,?, 'PSICOSOCIAL','ps_acciones_plan',?,?, 'ACCION_PSICOSOCIAL','FAMILIA_COMUNIDAD_REDES',?,?,?,?,?,?,?,?,?,?,?,0,0,?,1,?,?,?,?)
        ON CONFLICT(fundacion_id,fuente_tabla,fuente_clave) DO UPDATE SET unidad_nombre=excluded.unidad_nombre,unidad_clave=excluded.unidad_clave,
        titulo=excluded.titulo,descripcion=excluded.descripcion,fecha_inicio=excluded.fecha_inicio,fecha_limite=excluded.fecha_limite,
        fecha_finalizacion=excluded.fecha_finalizacion,estado=excluded.estado,prioridad=excluded.prioridad,puntaje_prioridad=excluded.puntaje_prioridad,
        responsable_id=excluded.responsable_id,responsable_nombre=excluded.responsable_nombre,requiere_evidencia=excluded.requiere_evidencia,
        metadata_json=excluded.metadata_json,activa=1,actualizada_por=excluded.actualizada_por,fecha_actualizacion=excluded.fecha_actualizacion""",
        (fundacion_id,item.get("expediente_uca_id"),item.get("unidad_nombre"),unit_key(item.get("unidad_nombre")),action_id,key,item.get("titulo"),item.get("descripcion"),item.get("fecha_inicio"),item.get("fecha_limite"),item.get("fecha_completada"),item.get("estado"),item.get("prioridad"),score,item.get("responsable_id"),item.get("responsable_nombre"),item.get("requiere_evidencia"),json_dump({"plan_id":item.get("plan_id"),"origen":"psicosocial"}),user.get("id"),user.get("id"),now,now))
