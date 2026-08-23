from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import json

from modules.dbapi_compat import sqlite3


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


class CentroDocumentalRepository:
    def __init__(self, database_path: str):
        self.database_path = str(database_path)

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
        finally:
            connection.close()

    def audit(self, tenant: int, entity: str, entity_id: int | None, action: str, user_id=None, detail=None) -> None:
        with self.connect() as connection:
            connection.execute("INSERT INTO doc_auditoria(fundacion_id,entidad,entidad_id,accion,usuario_id,detalle_json,creado_en) VALUES(?,?,?,?,?,?,?)", (tenant,entity,entity_id,action,user_id,json.dumps(detail or {},ensure_ascii=False),now_iso()))
            connection.commit()

    def list_templates(self, tenant: int) -> list[dict]:
        with self.connect() as connection:
            rows = connection.execute("SELECT * FROM doc_plantillas WHERE (scope='GLOBAL' AND fundacion_id IS NULL) OR fundacion_id=? ORDER BY tipo_documento,nombre",(tenant,)).fetchall()
            result=[]
            for row in rows:
                item=dict(row)
                version=connection.execute(
                    "SELECT id,version,estado,mapa_version FROM doc_plantilla_versiones WHERE plantilla_id=? AND (fundacion_id=? OR fundacion_id IS NULL) ORDER BY id DESC LIMIT 1",
                    (item["id"],tenant),
                ).fetchone()
                item["plantilla_version_id"]=int(version["id"]) if version else None
                item["version"]=version["version"] if version else None
                item["version_estado"]=version["estado"] if version else "SIN_VERSION"
                item["mapa_version"]=version["mapa_version"] if version else 0
                result.append(item)
        return result

    def capture_status(self, tenant: int, generation_enabled: bool = False) -> dict:
        """Return the real CAPTURE status for the active foundation."""
        with self.connect() as connection:
            row = connection.execute(
                """SELECT v.estado, v.id plantilla_version_id, v.version
                     FROM doc_plantilla_versiones v
                     JOIN doc_plantillas p ON p.id=v.plantilla_id
                    WHERE (v.fundacion_id=? OR (v.fundacion_id IS NULL AND p.scope='GLOBAL'))
                      AND (UPPER(p.tipo_documento)='CAPTURE' OR UPPER(p.codigo)='CAPTURE')
                    ORDER BY CASE WHEN v.estado IN ('APROBADA','ACTIVA') THEN 0 ELSE 1 END, v.id DESC
                    LIMIT 1""",
                (tenant,),
            ).fetchone()
        if not row:
            return {"estado": "PLANTILLA_PENDIENTE", "generacion_habilitada": False}
        status = str(row["estado"] or "PLANTILLA_PENDIENTE").upper()
        ready = status in {"APROBADA", "ACTIVA"}
        return {
            "estado": "ACTIVA" if ready and generation_enabled else status,
            "generacion_habilitada": bool(ready and generation_enabled),
            "plantilla_version_id": int(row["plantilla_version_id"]),
            "version": row["version"],
        }

    def create_template_version(self, template: dict, version: dict, user_id=None) -> dict:
        tenant = int(template["fundacion_id"])
        with self.connect() as connection:
            row = connection.execute("SELECT id FROM doc_plantillas WHERE fundacion_id=? AND codigo=?",(tenant,template["codigo"])).fetchone()
            if row:
                template_id = int(row["id"])
            else:
                cursor = connection.execute("INSERT INTO doc_plantillas(codigo,nombre,componente,tipo_documento,scope,fundacion_id,estado,protegida,creado_por,creado_en,actualizado_en) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(template["codigo"],template["nombre"],template["componente"],template["tipo_documento"],template.get("scope","FUNDACION"),tenant,"CARGADA",1,user_id,now_iso(),now_iso()))
                template_id = int(cursor.lastrowid)
            duplicate = connection.execute("SELECT id FROM doc_plantilla_versiones WHERE fundacion_id=? AND hash_sha256=?",(tenant,version["hash_sha256"])).fetchone()
            if duplicate:
                raise ValueError("Esta plantilla ya fue cargada anteriormente.")
            cursor = connection.execute("INSERT INTO doc_plantilla_versiones(plantilla_id,fundacion_id,version,nombre_original,nombre_seguro,ruta_privada,mime_type,extension,hash_sha256,estado,inspeccion_json,mapa_version,usuario_creador_id,creado_en,actualizado_en) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(template_id,tenant,version["version"],version["nombre_original"],version["nombre_seguro"],version["ruta_privada"],version.get("mime_type"),version["extension"],version["hash_sha256"],version.get("estado","MAPEO_PROPUESTO"),json.dumps(version.get("inspeccion") or {},ensure_ascii=False),0,user_id,now_iso(),now_iso()))
            version_id = int(cursor.lastrowid)
            connection.execute("UPDATE doc_plantillas SET estado='MAPEO_PROPUESTO',actualizado_en=? WHERE id=?",(now_iso(),template_id))
            connection.commit()
        self.audit(tenant,"PLANTILLA_VERSION",version_id,"CARGADA",user_id,{"hash":version["hash_sha256"],"codigo":template["codigo"]})
        return self.get_version(version_id,tenant)

    def get_version(self, version_id: int, tenant: int) -> dict | None:
        with self.connect() as connection:
            row=connection.execute("SELECT v.*,p.codigo,p.nombre,p.componente,p.tipo_documento,p.scope FROM doc_plantilla_versiones v JOIN doc_plantillas p ON p.id=v.plantilla_id WHERE v.id=? AND (v.fundacion_id=? OR (v.fundacion_id IS NULL AND p.scope='GLOBAL'))",(version_id,tenant)).fetchone()
        item=dict(row) if row else None
        if item: item["inspeccion"]=json.loads(item.get("inspeccion_json") or "{}")
        return item

    def save_mapping(self, version_id: int, tenant: int, mapping: dict, user_id=None) -> dict:
        with self.connect() as connection:
            owner=connection.execute("SELECT id FROM doc_plantilla_versiones WHERE id=? AND fundacion_id=?",(version_id,tenant)).fetchone()
            if not owner: raise KeyError("Plantilla no encontrada.")
            count=connection.execute("SELECT COALESCE(MAX(version),0) n FROM doc_mapeos WHERE plantilla_version_id=?",(version_id,)).fetchone()["n"]
            cursor=connection.execute("INSERT INTO doc_mapeos(plantilla_version_id,fundacion_id,version,estado,mapa_json,usuario_creador_id,creado_en) VALUES(?,?,?,?,?,?,?)",(version_id,tenant,int(count)+1,"PROPUESTO",json.dumps(mapping,ensure_ascii=False),user_id,now_iso()))
            mapping_id=int(cursor.lastrowid); connection.commit()
        self.audit(tenant,"MAPEO",mapping_id,"PROPUESTO",user_id)
        return {"id":mapping_id,"version":int(count)+1,"estado":"PROPUESTO","mapeo":mapping}

    def approve_mapping(self, version_id: int, tenant: int, user_id=None) -> dict:
        with self.connect() as connection:
            mapping=connection.execute("SELECT * FROM doc_mapeos WHERE plantilla_version_id=? AND fundacion_id=? ORDER BY version DESC LIMIT 1",(version_id,tenant)).fetchone()
            if not mapping: raise ValueError("No existe un mapa propuesto para aprobar.")
            connection.execute("UPDATE doc_mapeos SET estado='APROBADO',usuario_aprobador_id=?,aprobado_en=? WHERE id=?",(user_id,now_iso(),mapping["id"]))
            connection.execute("UPDATE doc_plantilla_versiones SET estado='APROBADA',usuario_aprobador_id=?,mapa_version=?,actualizado_en=? WHERE id=? AND fundacion_id=?",(user_id,mapping["version"],now_iso(),version_id,tenant)); connection.commit()
        self.audit(tenant,"MAPEO",mapping["id"],"APROBADO",user_id)
        return {"id":mapping["id"],"estado":"APROBADO","version":mapping["version"]}

    def list_catalogs(self, tenant: int, component: str = "") -> list[dict]:
        with self.connect() as connection:
            where="((c.scope='GLOBAL' AND c.fundacion_id IS NULL) OR c.fundacion_id=?) AND c.activo=1"
            params=[tenant]
            if component: where+=" AND c.componente=?"; params.append(component.upper())
            catalogs=connection.execute(f"SELECT c.* FROM doc_catalogos_respuesta c WHERE {where} ORDER BY c.componente,c.categoria,c.codigo",params).fetchall()
            result=[]
            for row in catalogs:
                item=dict(row); options=connection.execute("SELECT * FROM doc_opciones_respuesta WHERE catalogo_id=? AND activo=1 ORDER BY orden,codigo",(item["id"],)).fetchall()
                item["opciones"]=[dict(option) for option in options]; result.append(item)
        return result

    def create_instance(self, tenant: int, data: dict, user_id=None) -> dict:
        with self.connect() as connection:
            cursor=connection.execute("INSERT INTO doc_instancias(fundacion_id,tipo_documento,componente,plantilla_version_id,actividad_id,uds,periodo,modo,estado,tema,datos_json,planeacion_json,hechos_json,creado_por,actualizado_por,creado_en,actualizado_en) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(tenant,data["tipo_documento"],data["componente"],data.get("plantilla_version_id"),data.get("actividad_id"),data.get("uds"),data.get("periodo"),data.get("modo","PLANEACION"),"BORRADOR",data.get("tema"),json.dumps(data.get("datos") or {},ensure_ascii=False),json.dumps(data.get("planeacion") or {},ensure_ascii=False),"{}",user_id,user_id,now_iso(),now_iso()))
            instance_id=int(cursor.lastrowid); connection.commit()
        self.audit(tenant,"DOCUMENTO",instance_id,"CREADO",user_id)
        return self.get_instance(instance_id,tenant)

    def list_instances(self, tenant: int, limit: int = 25, offset: int = 0, component: str = "", status: str = "") -> dict:
        take=max(1,min(int(limit or 25),100)); skip=max(0,int(offset or 0))
        where=["fundacion_id=?"]; params=[tenant]
        if component: where.append("componente=?"); params.append(component.upper())
        if status: where.append("estado=?"); params.append(status.upper())
        clause=" AND ".join(where)
        with self.connect() as connection:
            total=int(connection.execute(f"SELECT COUNT(*) total FROM doc_instancias WHERE {clause}",params).fetchone()["total"])
            rows=connection.execute(
                f"SELECT id,tipo_documento,componente,uds,periodo,modo,estado,tema,version_actual,creado_en,actualizado_en FROM doc_instancias WHERE {clause} ORDER BY actualizado_en DESC,id DESC LIMIT ? OFFSET ?",
                (*params,take,skip),
            ).fetchall()
        return {"documentos":[dict(row) for row in rows],"total":total,"limit":take,"offset":skip}

    def document_audit(self, instance_id: int, tenant: int) -> list[dict]:
        with self.connect() as connection:
            if not connection.execute("SELECT id FROM doc_instancias WHERE id=? AND fundacion_id=?",(instance_id,tenant)).fetchone(): raise KeyError("Documento no encontrado.")
            rows=connection.execute(
                "SELECT a.id,a.accion,a.usuario_id,a.detalle_json,a.creado_en FROM doc_auditoria a LEFT JOIN doc_versiones v ON a.entidad='DOCUMENTO_VERSION' AND v.id=a.entidad_id AND v.fundacion_id=a.fundacion_id WHERE a.fundacion_id=? AND ((a.entidad='DOCUMENTO' AND a.entidad_id=?) OR (a.entidad='DOCUMENTO_VERSION' AND v.documento_id=?)) ORDER BY a.id DESC LIMIT 100",
                (tenant,instance_id,instance_id),
            ).fetchall()
        result=[]
        for row in rows:
            item=dict(row); item["detalle"]=json.loads(item.pop("detalle_json") or "{}"); result.append(item)
        return result

    def document_history(self, instance_id: int, tenant: int) -> dict:
        with self.connect() as connection:
            if not connection.execute("SELECT id FROM doc_instancias WHERE id=? AND fundacion_id=?",(instance_id,tenant)).fetchone(): raise KeyError("Documento no encontrado.")
            versions=connection.execute(
                "SELECT id,version,estado,CASE WHEN archivo_word IS NULL THEN 0 ELSE 1 END word_disponible,CASE WHEN archivo_pdf IS NULL THEN 0 ELSE 1 END pdf_disponible,hash_sha256,creado_por,creado_en FROM doc_versiones WHERE documento_id=? AND fundacion_id=? ORDER BY version DESC",
                (instance_id,tenant),
            ).fetchall()
            reviews=connection.execute(
                "SELECT id,accion,observacion,usuario_id,creado_en FROM doc_revisiones WHERE documento_id=? AND fundacion_id=? ORDER BY id DESC",
                (instance_id,tenant),
            ).fetchall()
        return {"versiones":[dict(row) for row in versions],"revisiones":[dict(row) for row in reviews],"eventos":self.document_audit(instance_id,tenant)}

    def get_instance(self, instance_id: int, tenant: int) -> dict | None:
        with self.connect() as connection:
            row=connection.execute("SELECT * FROM doc_instancias WHERE id=? AND fundacion_id=?",(instance_id,tenant)).fetchone()
            if not row: return None
            item=dict(row)
            selections=connection.execute("SELECT s.*,o.codigo,o.texto FROM doc_selecciones s LEFT JOIN doc_opciones_respuesta o ON o.id=s.opcion_id WHERE s.documento_id=? AND s.fundacion_id=? ORDER BY s.id",(instance_id,tenant)).fetchall()
            reviews=connection.execute("SELECT * FROM doc_revisiones WHERE documento_id=? AND fundacion_id=? ORDER BY id",(instance_id,tenant)).fetchall()
        for key in ("datos_json","planeacion_json","hechos_json"):
            item[key[:-5]]=json.loads(item.get(key) or "{}")
        item["selecciones"]=[dict(value) for value in selections]; item["revisiones"]=[dict(value) for value in reviews]
        return item

    def replace_selections(self, instance_id: int, tenant: int, selections: list[dict], user_id=None) -> list[dict]:
        with self.connect() as connection:
            if not connection.execute("SELECT id FROM doc_instancias WHERE id=? AND fundacion_id=?",(instance_id,tenant)).fetchone(): raise KeyError("Documento no encontrado.")
            connection.execute("DELETE FROM doc_selecciones WHERE documento_id=? AND fundacion_id=?",(instance_id,tenant))
            for item in selections:
                option_id=item.get("opcion_id")
                if option_id:
                    allowed=connection.execute("SELECT o.id FROM doc_opciones_respuesta o JOIN doc_catalogos_respuesta c ON c.id=o.catalogo_id WHERE o.id=? AND o.activo=1 AND ((c.scope='GLOBAL' AND c.fundacion_id IS NULL) OR c.fundacion_id=?)",(option_id,tenant)).fetchone()
                    if not allowed: raise ValueError("La opción seleccionada no pertenece a la fundación o no está activa.")
                connection.execute("INSERT INTO doc_selecciones(documento_id,fundacion_id,categoria,opcion_id,texto_personalizado,estado_especial,justificacion,confirmado_por,confirmado_en) VALUES(?,?,?,?,?,?,?,?,?)",(instance_id,tenant,str(item.get("categoria") or "").upper(),item.get("opcion_id"),item.get("texto_personalizado"),item.get("estado_especial"),item.get("justificacion"),user_id,now_iso()))
            connection.execute("UPDATE doc_instancias SET hechos_json=?,actualizado_por=?,actualizado_en=? WHERE id=? AND fundacion_id=?",(json.dumps({"confirmados":True,"cantidad":len(selections)},ensure_ascii=False),user_id,now_iso(),instance_id,tenant)); connection.commit()
        self.audit(tenant,"DOCUMENTO",instance_id,"SELECCIONES_CONFIRMADAS",user_id,{"cantidad":len(selections)})
        return self.get_instance(instance_id,tenant)["selecciones"]

    def save_narrative(self, instance_id: int, tenant: int, narrative: str, user_id=None) -> dict:
        with self.connect() as connection:
            cursor=connection.execute("UPDATE doc_instancias SET narrativa=?,modo='INFORME_FINAL',estado='EN_ELABORACION',actualizado_por=?,actualizado_en=? WHERE id=? AND fundacion_id=?",(narrative,user_id,now_iso(),instance_id,tenant))
            if not cursor.rowcount: raise KeyError("Documento no encontrado.")
            connection.commit()
        self.audit(tenant,"DOCUMENTO",instance_id,"NARRATIVA_GUARDADA",user_id)
        return self.get_instance(instance_id,tenant)

    def transition(self, instance_id: int, tenant: int, action: str, user_id=None, observation: str = "") -> dict:
        transitions={"ENVIAR_REVISION":("EN_ELABORACION","EN_REVISION"),"DEVOLVER":("EN_REVISION","DEVUELTO"),"REENVIAR":("DEVUELTO","EN_REVISION"),"APROBAR":("EN_REVISION","APROBADO"),"ARCHIVAR":("APROBADO","ARCHIVADO")}
        if action not in transitions: raise ValueError("Acción documental no permitida.")
        source,target=transitions[action]
        if action=="DEVOLVER" and not observation.strip(): raise ValueError("La devolución requiere una observación.")
        with self.connect() as connection:
            row=connection.execute("SELECT estado FROM doc_instancias WHERE id=? AND fundacion_id=?",(instance_id,tenant)).fetchone()
            if not row: raise KeyError("Documento no encontrado.")
            if row["estado"]!=source: raise ValueError(f"La acción {action} requiere estado {source}.")
            connection.execute("UPDATE doc_instancias SET estado=?,actualizado_por=?,actualizado_en=? WHERE id=? AND fundacion_id=?",(target,user_id,now_iso(),instance_id,tenant))
            connection.execute("INSERT INTO doc_revisiones(documento_id,fundacion_id,accion,observacion,usuario_id,creado_en) VALUES(?,?,?,?,?,?)",(instance_id,tenant,action,observation,user_id,now_iso())); connection.commit()
        self.audit(tenant,"DOCUMENTO",instance_id,action,user_id,{"estado":target})
        return self.get_instance(instance_id,tenant)

    def record_version(self, instance_id: int, tenant: int, content: dict, word_path: str | None, pdf_path: str | None, digest: str | None, user_id=None) -> dict:
        with self.connect() as connection:
            if not connection.execute("SELECT id FROM doc_instancias WHERE id=? AND fundacion_id=?",(instance_id,tenant)).fetchone(): raise KeyError("Documento no encontrado.")
            number=int(connection.execute("SELECT COALESCE(MAX(version),0)+1 n FROM doc_versiones WHERE documento_id=? AND fundacion_id=?",(instance_id,tenant)).fetchone()["n"])
            cursor=connection.execute("INSERT INTO doc_versiones(documento_id,fundacion_id,version,estado,contenido_json,archivo_word,archivo_pdf,hash_sha256,creado_por,creado_en) VALUES(?,?,?,?,?,?,?,?,?,?)",(instance_id,tenant,number,"GENERADA",json.dumps(content,ensure_ascii=False),word_path,pdf_path,digest,user_id,now_iso()))
            version_id=int(cursor.lastrowid)
            connection.execute("UPDATE doc_instancias SET version_actual=?,actualizado_en=? WHERE id=? AND fundacion_id=?",(number,now_iso(),instance_id,tenant)); connection.commit()
        self.audit(tenant,"DOCUMENTO_VERSION",version_id,"GENERADA",user_id,{"documento_id":instance_id,"version":number})
        return {"id":version_id,"version":number,"archivo_word":word_path,"archivo_pdf":pdf_path,"sha256":digest}

    def get_generated_version(self, instance_id: int, tenant: int, number: int | None = None) -> dict | None:
        with self.connect() as connection:
            if number is None: row=connection.execute("SELECT * FROM doc_versiones WHERE documento_id=? AND fundacion_id=? ORDER BY version DESC LIMIT 1",(instance_id,tenant)).fetchone()
            else: row=connection.execute("SELECT * FROM doc_versiones WHERE documento_id=? AND fundacion_id=? AND version=?",(instance_id,tenant,number)).fetchone()
        return dict(row) if row else None

    def replace_participants(self, instance_id: int, tenant: int, participants: list[dict]) -> list[dict]:
        with self.connect() as connection:
            if not connection.execute("SELECT id FROM doc_instancias WHERE id=? AND fundacion_id=?",(instance_id,tenant)).fetchone(): raise KeyError("Documento no encontrado.")
            resolved=[]
            for item in participants:
                source=str(item.get("origen_tipo") or "BENEFICIARIO").upper(); source_id=str(item.get("origen_id") or "").strip()
                if source=="BENEFICIARIO": row=connection.execute("SELECT id,nombre_completo nombre,documento,nui,unidad_servicio unidad FROM master_ninos WHERE id=? AND fundacion_id=? AND activo=1",(source_id,tenant)).fetchone()
                elif source=="TALENTO_HUMANO": row=connection.execute("SELECT id,nombre,documento,NULL nui,unidad FROM th_personas WHERE id=? AND fundacion_id=? AND COALESCE(activo,1)=1",(source_id,tenant)).fetchone()
                else: raise ValueError("Origen de participante no permitido.")
                if not row: raise ValueError("Un participante no existe en la fuente maestra de la fundación.")
                resolved.append((source,source_id,dict(row)))
            connection.execute("DELETE FROM doc_participantes WHERE documento_id=? AND fundacion_id=?",(instance_id,tenant))
            for source,source_id,row in resolved: connection.execute("INSERT INTO doc_participantes(documento_id,fundacion_id,origen_tipo,origen_id,nombre_mostrado,creado_en) VALUES(?,?,?,?,?,?)",(instance_id,tenant,source,source_id,row.get("nombre"),now_iso()))
            connection.commit()
        self.audit(tenant,"DOCUMENTO",instance_id,"PARTICIPANTES_CONFIRMADOS",None,{"cantidad":len(resolved)})
        return [{"origen_tipo":source,"origen_id":source_id,**row} for source,source_id,row in resolved]

    def participants(self, instance_id: int, tenant: int) -> list[dict]:
        with self.connect() as connection:
            links=connection.execute("SELECT * FROM doc_participantes WHERE documento_id=? AND fundacion_id=? ORDER BY id",(instance_id,tenant)).fetchall(); result=[]
            for link in links:
                item=dict(link)
                if item["origen_tipo"]=="BENEFICIARIO": source=connection.execute("SELECT nombre_completo nombre,documento,nui,unidad_servicio unidad FROM master_ninos WHERE id=? AND fundacion_id=?",(item["origen_id"],tenant)).fetchone()
                else: source=connection.execute("SELECT nombre,documento,NULL nui,unidad FROM th_personas WHERE id=? AND fundacion_id=?",(item["origen_id"],tenant)).fetchone()
                if source: result.append({**item,**dict(source)})
        return result

    def add_evidence(self, instance_id: int, tenant: int, data: dict, user_id=None) -> dict:
        with self.connect() as connection:
            if not connection.execute("SELECT id FROM doc_instancias WHERE id=? AND fundacion_id=?",(instance_id,tenant)).fetchone(): raise KeyError("Documento no encontrado.")
            number=int(connection.execute("SELECT COALESCE(MAX(version),0)+1 n FROM doc_evidencias WHERE documento_id=? AND fundacion_id=? AND nombre_original=?",(instance_id,tenant,data["nombre_original"])).fetchone()["n"])
            cursor=connection.execute("INSERT INTO doc_evidencias(documento_id,fundacion_id,actividad_id,requisito,nombre_original,nombre_seguro,ruta_privada,mime_type,tamano_bytes,hash_sha256,version,estado,usuario_id,creado_en) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(instance_id,tenant,data.get("actividad_id"),data.get("requisito"),data["nombre_original"],data["nombre_seguro"],data["ruta_privada"],data.get("mime_type"),data.get("tamano_bytes"),data["hash_sha256"],number,"CARGADA",user_id,now_iso()))
            evidence_id=int(cursor.lastrowid); connection.commit()
        self.audit(tenant,"EVIDENCIA",evidence_id,"CARGADA",user_id,{"documento_id":instance_id,"hash":data["hash_sha256"]})
        return self.get_evidence(evidence_id,tenant)

    def get_evidence(self, evidence_id: int, tenant: int) -> dict | None:
        with self.connect() as connection: row=connection.execute("SELECT * FROM doc_evidencias WHERE id=? AND fundacion_id=?",(evidence_id,tenant)).fetchone()
        return dict(row) if row else None

    def list_evidence(self, instance_id: int, tenant: int) -> list[dict]:
        with self.connect() as connection: rows=connection.execute("SELECT id,documento_id,actividad_id,requisito,nombre_original,mime_type,tamano_bytes,hash_sha256,version,estado,usuario_id,creado_en FROM doc_evidencias WHERE documento_id=? AND fundacion_id=? ORDER BY id DESC",(instance_id,tenant)).fetchall()
        return [dict(row) for row in rows]

    def calendar_requirements(self, instance_id: int, tenant: int) -> dict:
        with self.connect() as connection:
            doc=connection.execute("SELECT actividad_id FROM doc_instancias WHERE id=? AND fundacion_id=?",(instance_id,tenant)).fetchone()
            if not doc: raise KeyError("Documento no encontrado.")
            if not doc["actividad_id"]: return {"vinculada":False,"requisitos":[]}
            try:
                assignment=connection.execute("SELECT * FROM calendario_asignaciones WHERE id=? AND fundacion_id=?",(doc["actividad_id"],tenant)).fetchone()
                requirements=connection.execute("SELECT * FROM calendario_requisitos WHERE obligacion_id=? AND fundacion_id=? ORDER BY orden,id",(assignment["obligacion_id"],tenant)).fetchall() if assignment else []
            except Exception: assignment=None; requirements=[]
        return {"vinculada":bool(assignment),"actividad":dict(assignment) if assignment else None,"requisitos":[dict(row) for row in requirements]}
