from __future__ import annotations

import sys
import tempfile
import io
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from flask import Flask,g,request
from migrations.migrate_centro_documental_v7 import migrate
from modules.centro_documental import register_centro_documental
from modules.seguridad.tenant_context import tenant_storage_root
from openpyxl import Workbook


def run():
    with tempfile.TemporaryDirectory() as folder:
        root=Path(folder); database=root/"http.sqlite"; data=root/"data"; migrate(str(database))
        app=Flask(__name__); app.config.update(TESTING=True,ENABLE_DOCUMENT_AUTOMATION=False,ENABLE_TEMPLATE_MAPPING=True,ENABLE_RESPONSE_CATALOGS=True)
        @app.before_request
        def user(): g.current_user={"id":1,"fundacion_id":int(request.headers.get("X-Tenant","1")),"rol":request.headers.get("X-Role","DOCENTE")}
        register_centro_documental(app,str(database),str(data)); client=app.test_client()
        assert client.get("/api/documentos/estado").status_code==404
        app.config["ENABLE_DOCUMENT_AUTOMATION"]=True
        state=client.get("/api/documentos/estado"); assert state.status_code==200 and state.json["capture"]["estado"]=="PLANTILLA_PENDIENTE"
        workbook=Workbook(); sheet=workbook.active; sheet.append(["Documento", "Nombre", "Peso", "Talla"]); capture_file=io.BytesIO(); workbook.save(capture_file); capture_file.seek(0)
        uploaded=client.post("/api/documentos/plantillas",headers={"X-Role":"COORDINADOR"},data={"codigo":"001","version":"1.0","componente":"SALUD_NUTRICION","tipo_documento":"FORMATO CACTURE","file":(capture_file,"capture.xlsx")},content_type="multipart/form-data")
        assert uploaded.status_code==201, uploaded.json
        version_id=uploaded.json["plantilla_version"]["id"]
        proposed=client.get("/api/documentos/estado"); assert proposed.json["capture"]["estado"]=="MAPEO_PROPUESTO"
        approved=client.post(f"/api/documentos/plantillas/{version_id}/aprobar",headers={"X-Role":"COORDINADOR"}); assert approved.status_code==200, approved.json
        active=client.get("/api/documentos/estado"); assert active.json["capture"]["estado"]=="ACTIVA" and active.json["capture"]["generacion_habilitada"] is True
        assert client.get("/api/documentos/estado",headers={"X-Role":"AUXILIAR_ADMINISTRATIVO"}).status_code==200
        planning=client.post("/api/documentos/tema/generar-planeacion",json={"tema":"Juego y vínculos","componente":"PEDAGOGICO"}); assert planning.status_code==200 and planning.json["planeacion"]["clasificacion"]=="PLANEADO"
        created=client.post("/api/documentos",json={"tipo_documento":"ACTA_HOGAR","componente":"PEDAGOGICO","tema":"Juego y vínculos"}); assert created.status_code==201; document_id=created.json["documento"]["id"]
        listed=client.get("/api/documentos?limit=10"); assert listed.status_code==200 and listed.json["total"]==1 and listed.json["documentos"][0]["id"]==document_id
        assert client.get("/api/documentos?limit=10",headers={"X-Tenant":"2"}).json["total"]==0
        assert client.get(f"/api/documentos/{document_id}").status_code==200
        assert client.get(f"/api/documentos/{document_id}",headers={"X-Tenant":"2"}).status_code==404
        participants=client.get(f"/api/documentos/{document_id}/participantes"); assert participants.status_code==200 and participants.json["participantes"]==[]
        assert client.get(f"/api/documentos/{document_id}/participantes",headers={"X-Tenant":"2"}).status_code==404
        assert client.post("/api/documentos",json={"tipo_documento":"CAPTURE","componente":"SALUD_NUTRICION"}).status_code==409
        catalogs=client.get("/api/documentos/catalogos?componente=PEDAGOGICO"); assert catalogs.status_code==200 and catalogs.json["catalogos"]
        option=catalogs.json["catalogos"][0]["opciones"][0]
        selections=client.post(f"/api/documentos/{document_id}/selecciones",json={"selecciones":[{"categoria":"PARTICIPACION","opcion_id":option["id"]}]}); assert selections.status_code==200
        draft=client.post(f"/api/documentos/{document_id}/generar-borrador"); assert draft.status_code==200 and draft.json["documento"]["estado"]=="EN_ELABORACION"
        edited=client.patch(f"/api/documentos/{document_id}",json={"narrativa":"Texto revisado por el profesional."}); assert edited.status_code==200 and edited.json["documento"]["narrativa"].startswith("Texto revisado")
        submitted=client.post(f"/api/documentos/{document_id}/enviar-revision",json={}); assert submitted.status_code==200 and submitted.json["documento"]["estado"]=="EN_REVISION"
        returned=client.post(f"/api/documentos/{document_id}/devolver",headers={"X-Role":"COORDINADOR"},json={"observacion":"Ajustar el cierre."}); assert returned.status_code==200 and returned.json["documento"]["estado"]=="DEVUELTO"
        audit=client.get(f"/api/documentos/{document_id}/auditoria"); assert audit.status_code==200 and any(item["accion"]=="DEVOLVER" for item in audit.json["eventos"]) and audit.json["revisiones"][0]["observacion"]=="Ajustar el cierre."
        assert client.get(f"/api/documentos/{document_id}/auditoria",headers={"X-Tenant":"2"}).status_code==404
        assert client.get(f"/api/documentos/{document_id}/descargar-paquete").status_code==404
        package=tenant_storage_root(data,1)/"packages"/str(document_id)/f"PAQUETE_DOCUMENTAL_{document_id}.zip"; package.parent.mkdir(parents=True); package.write_bytes(b"PK\x05\x06"+b"\x00"*18)
        downloaded=client.get(f"/api/documentos/{document_id}/descargar-paquete"); assert downloaded.status_code==200 and downloaded.mimetype=="application/zip"; downloaded.close()
        assert client.get(f"/api/documentos/{document_id}/descargar-paquete",headers={"X-Tenant":"2"}).status_code==404
        assert client.post(f"/api/documentos/{document_id}/aprobar",headers={"X-Role":"DOCENTE"}).status_code==403
        assert client.get("/api/documentos/estado",headers={"X-Role":"INVITADO"}).status_code==403
    print("PASS test_centro_documental_http_v7")


if __name__=="__main__": run()
