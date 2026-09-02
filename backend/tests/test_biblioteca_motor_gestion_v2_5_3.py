#!/usr/bin/env python3
"""Pruebas de Biblioteca Oficial ICBF y Motor de Gestión 2.5.3."""
from __future__ import annotations
import importlib.util
import json
import os
import sqlite3
import tempfile
import zipfile
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
BACKEND=ROOT/'backend'
sys.path.insert(0,str(BACKEND))
from modules.gestion_integral_uca.repository import GestionIntegralRepository
from modules.gestion_integral_uca.schema import SCHEMA_VERSION as GIU_SCHEMA_VERSION
from modules.motor_gestion_proyecto.repository import MotorGestionRepository
from modules.motor_gestion_proyecto.schema import SCHEMA_VERSION as MGP_SCHEMA_VERSION
from modules.motor_gestion_proyecto.services import file_sha256
from modules.gestion_integral_uca.library_updates import fetch_authorized_catalog, LibraryUpdateError

spec=importlib.util.spec_from_file_location('v252test',BACKEND/'tests'/'test_expediente_uca_central_v2_5_2.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
prepare_database=mod.prepare_database

def require(value,msg):
    if not value: raise AssertionError(msg)

def run():
    require(GIU_SCHEMA_VERSION==3,'GIU debe usar esquema 3')
    require(MGP_SCHEMA_VERSION==1,'MGP debe usar esquema 1')
    with tempfile.TemporaryDirectory(prefix='pi-v253-') as temp:
        root=Path(temp);db=root/'db.sqlite3';data=root/'data';out=root/'out'
        prepare_database(db,data)
        giu=GestionIntegralRepository(str(db),str(data),str(out));giu.init_schema()
        ua={'id':11,'username':'gerente.a','rol':'SUPERADMIN','fundacion_id':1}
        ub={'id':22,'username':'gerente.b','rol':'SUPERADMIN','fundacion_id':2}
        expa=giu.sync_all_units(1,'2026','CONTRATO-A',ua)[0]
        giu.sync_all_units(2,'2026','CONTRATO-B',ub)
        motor=MotorGestionRepository(str(db),str(data),str(out));motor.init_schema()
        first=motor.synchronize(1,ua); second=motor.synchronize(1,ua)
        period_tasks=motor.list_tasks(1,{'periodo':'2026-08'},limit=5000)
        all_tasks=motor.list_tasks(1,{},limit=5000)
        require(period_tasks,'El motor no consolidó fuentes del período')
        require(first['creadas']>0 and second['creadas']==0 and len(all_tasks)==first['fuentes_leidas'],'Sincronización no idempotente')
        require(all(t['fundacion_id']==1 for t in all_tasks),'Se cruzaron tareas de otra fundación')
        require(any(t['fuente_modulo']=='GESTION_INTEGRAL_UCA' for t in all_tasks),'Falta Ruta Operativa')
        require(any(t['fuente_modulo']=='GESTION_PEDAGOGICA' for t in all_tasks),'Falta Gestión Pedagógica')
        require(any(t['fuente_modulo']=='SALUD_NUTRICION' for t in all_tasks),'Falta Salud y Nutrición')
        require(any(t.get('vencida') for t in motor.list_tasks(1,{},limit=5000)),'No se detectó vencimiento')
        require(motor.reminders(1,unread_only=True),'No se generaron recordatorios')
        products=motor.prepare_monthly_products(1,'2026-08',expa['id'],ua)
        require(len(products['productos'])==3,'Deben generarse Excel, PDF y ZIP')
        require(all(p['estado']=='BORRADOR' for p in products['productos']),'Productos no quedaron en borrador')
        for p in products['productos']:
            found=motor.product_path(1,p['id']);require(found and found[0].is_file(),'Producto no verificable')
            require(file_sha256(found[0])==p['sha256'],'SHA incorrecto')
        zip_product=next(p for p in products['productos'] if p['tipo_producto']=='PAQUETE_MENSUAL')
        with zipfile.ZipFile(motor.product_path(1,zip_product['id'])[0]) as z:
            require({'01_TAREAS.csv','02_RESUMEN.json','03_BIBLIOTECA_APLICABLE.json','LEEME.txt'}<=set(z.namelist()),'Paquete mensual incompleto')
        closure=products['cierre'];require(closure['estado']=='BORRADOR','Cierre no quedó en borrador')
        dashboard=motor.dashboard(1,'2026-08',user=ua);require(dashboard['resumen']['total']>0,'Dashboard vacío')

        sources=giu.list_library_sources(1);require(sources,'No se sembró fuente controlada')
        require(all(not x['habilitada'] or not x['autorizada'] for x in sources),'No debe habilitarse una fuente remota por defecto')
        try:
            fetch_authorized_catalog({**sources[0], 'mecanismo':'CATALOGO_JSON', 'habilitada':1, 'autorizada':1})
            raise AssertionError('La consulta remota no debe habilitarse por defecto')
        except LibraryUpdateError:
            pass
        os.environ.pop('BIBLIOTECA_REMOTE_CHECKS_ENABLED',None)
        candidate=giu.import_library_candidates(1,None,[{
            'codigo':'MT3.PP','nombre':'Manual técnico de prueba','version':'3','fecha_documento':'2026-08-05',
            'componente':'TRANSVERSAL','tipo_documento':'DOCUMENTO_TECNICO','fuente_url':'https://www.icbf.gov.co/documento-prueba'
        }],ua)
        require(candidate['detectadas']==1,'No se detectó candidato manual')
        cid=candidate['candidatos'][0]
        approved=giu.decide_library_candidate(1,cid,'APROBAR',ua,'Metadatos revisados; archivo oficial pendiente')
        require(approved['estado']=='APROBADA','Candidato no aprobado')
        docs=giu.list_library_documents(1,include_versions=True)
        doc=next(d for d in docs if d['codigo']=='MT3_PP')
        version=next(v for v in doc['versiones'] if v['version']=='3')
        require(version['estado']=='APROBADA' and version['estado']!='VIGENTE','La detección no debe activar automáticamente')
        relations=giu.list_library_relations(1,doc['id']);require(relations,'No se sugirieron relaciones')
        require(giu.list_library_notifications(1),'Faltan notificaciones')
        require(giu.list_library_history(1,doc['id']),'Falta historial')
        require(not giu.list_library_candidates(2),'Se cruzaron candidatos entre fundaciones')
        conn=sqlite3.connect(db)
        require(conn.execute("SELECT COUNT(*) FROM mgp_tareas WHERE fundacion_id=1").fetchone()[0]==len(motor.list_tasks(1,{},limit=5000)),'Tareas duplicadas')
        require(conn.execute("SELECT COUNT(*) FROM biblioteca_icbf_versiones WHERE fundacion_id=1 AND estado='VIGENTE' AND version='3'").fetchone()[0]==0,'Versión candidata se volvió vigente')
        conn.close()
    html=(ROOT/'frontend'/'index.html').read_text(encoding='utf-8')
    js=(ROOT/'frontend'/'js'/'modules'/'motor-gestion-proyecto.js').read_text(encoding='utf-8')
    giujs=(ROOT/'frontend'/'js'/'modules'/'gestion-integral-uca.js').read_text(encoding='utf-8')
    require('motor-gestion-proyecto' in html and 'Motor Inteligente de Gestión del Proyecto' in html,'Falta UI motor')
    require('prepareProducts' in js and 'prepareClosure' in js,'UI motor incompleta')
    require('loadLibraryOperations' in giujs and 'verifyLibrarySource' in giujs,'UI biblioteca avanzada incompleta')
    print(json.dumps({'ok':True,'giu_schema':GIU_SCHEMA_VERSION,'mgp_schema':MGP_SCHEMA_VERSION,'pruebas':['biblioteca versionada','aprobación manual','fuentes remotas cerradas','motor idempotente','productos borrador','cierres humanos','aislamiento multi-fundación']},ensure_ascii=False,indent=2))

if __name__=='__main__':run()
