#!/usr/bin/env python3
from __future__ import annotations
import sqlite3, sys, tempfile, types
from contextlib import closing
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; BACKEND=ROOT/'backend'; sys.path.insert(0,str(BACKEND))
if 'flask' not in sys.modules:
    flask=types.ModuleType('flask')
    class BP:
        def __init__(self,*a,**k): pass
        def route(self,*a,**k): return lambda f:f
    flask.Blueprint=BP; flask.g=types.SimpleNamespace(current_user={}); flask.jsonify=lambda *a,**k:(a,k); flask.request=types.SimpleNamespace(args={},form={},files={}); flask.send_file=lambda *a,**k:a[0]
    sys.modules['flask']=flask
if 'werkzeug.utils' not in sys.modules:
    w=types.ModuleType('werkzeug'); u=types.ModuleType('werkzeug.utils'); u.secure_filename=lambda x: ''.join(c if c.isalnum() or c in '._-' else '_' for c in str(x)); sys.modules['werkzeug']=w; sys.modules['werkzeug.utils']=u
security=types.ModuleType('modules.seguridad.services'); security.require_roles=lambda *r:(lambda f:f); sys.modules['modules.seguridad.services']=security
tenant=types.ModuleType('modules.seguridad.tenant_context'); tenant.tenant_storage_root=lambda base,fid: Path(base)/'tenants'/str(fid); tenant.current_tenant_context=lambda: types.SimpleNamespace(tenant_id=None,allow_global=True,role='SYSTEM',username='test'); tenant.capture_tenant_context=tenant.current_tenant_context; tenant.tenant_context=lambda *a,**k: __import__('contextlib').nullcontext(); tenant.strict_tenant_mode=lambda: False; tenant.current_tenant_id=lambda default=None: default; tenant.tenant_path=lambda path,*parts: str(Path(path).joinpath(*parts)); tenant.resolve_tenant_path=tenant.tenant_path; sys.modules['modules.seguridad.tenant_context']=tenant
from modules.salud_nutricion.integral import SaludNutricionIntegralService
from modules.salud_nutricion.schema import SCHEMA_SQL
class TestConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc, tb):
        try: return super().__exit__(exc_type, exc, tb)
        finally: self.close()
class Repo:
    def __init__(self,path): self.path=str(path)
    def connect(self):
        c=sqlite3.connect(self.path,factory=TestConnection); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c
    def execute_script(self,s):
        with closing(self.connect()) as c:
            with c: c.executescript(s)
    def table_exists(self,t):
        with closing(self.connect()) as c:return c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(t,)).fetchone() is not None
    def columns(self,t):
        with closing(self.connect()) as c:return {r['name'] for r in c.execute(f'PRAGMA table_info({t})')}
    def fetch_all(self,s,p=()):
        with closing(self.connect()) as c:return [dict(r) for r in c.execute(s,p).fetchall()]
    def fetch_one(self,s,p=()):
        with closing(self.connect()) as c:
            r=c.execute(s,p).fetchone(); return dict(r) if r else None
    def execute_update(self,s,p=()):
        with closing(self.connect()) as c:
            with c:
                cur=c.execute(s,p); return cur.rowcount
    def log(self,*a,**k): pass
def req(ok,msg):
    if not ok: raise AssertionError(msg)
with tempfile.TemporaryDirectory() as td:
    base=Path(td); db=base/'db.sqlite3'; repo=Repo(db)
    with closing(repo.connect()) as c:
      with c:
        c.executescript(SCHEMA_SQL)
        c.executescript("""
        CREATE TABLE master_ninos(id INTEGER PRIMARY KEY AUTOINCREMENT,fundacion_id INTEGER,documento TEXT,nombres TEXT,apellidos TEXT,fecha_nacimiento TEXT,sexo TEXT,unidad_servicio TEXT,activo INTEGER DEFAULT 1,carne_salud TEXT,carne_vacunas TEXT);
        CREATE TABLE giu_expedientes_uca(id INTEGER PRIMARY KEY AUTOINCREMENT,fundacion_id INTEGER,unidad_nombre TEXT,codigo_unidad TEXT,estado TEXT DEFAULT 'ACTIVO');
        """)
        c.execute("INSERT INTO master_ninos(fundacion_id,documento,nombres,apellidos,fecha_nacimiento,sexo,unidad_servicio,carne_salud,carne_vacunas) VALUES(1,'DOC-1','Ana','Prueba','2022-01-01','F','UCA A','SI','NO')")
        c.execute("INSERT INTO master_ninos(fundacion_id,documento,nombres,apellidos,fecha_nacimiento,sexo,unidad_servicio,carne_salud,carne_vacunas) VALUES(2,'DOC-1','Otra','Prueba','2022-02-01','F','UCA B','NO','SI')")
        c.execute("INSERT INTO giu_expedientes_uca(fundacion_id,unidad_nombre,codigo_unidad) VALUES(1,'UCA A','UCA-A')")
        c.execute("INSERT INTO sn_valoraciones(fundacion_id,documento,nombre_completo,fecha_nacimiento,sexo,unidad,fecha_valoracion,peso_kg,talla_cm,perimetro_braquial_cm,diagnostico_global,periodo,activo,fecha_carga) VALUES(1,'DOC-1','Ana Prueba','2022-01-01','F','UCA A','2026-08-01',14.2,95.0,14.0,'ADECUADO','2026-08',1,'2026-08-01')")
    service=SaludNutricionIntegralService(repo,base/'data'); service.init_schema()
    user={'id':1,'username':'nutri','rol':'NUTRICIONISTA','fundacion_id':1,'unidades':['UCA A']}
    a=service.sync_expedientes(1,user,'UCA A'); b=service.sync_expedientes(1,user,'UCA A')
    req(a['creados']==1 and b['creados']==0,'sincronización no es idempotente')
    req(len(service.list_expedientes(1,user))==1,'expediente fundación 1 ausente')
    exp=service.list_expedientes(1,user)[0]; detail=service.expediente_detail(1,exp['id'],user)
    req(len(detail['documentos'])==8,'no creó los 8 documentos')
    vacc=next(x for x in detail['documentos'] if x['tipo_documento']=='VACUNACION_PAI')
    req(vacc['estado']=='PENDIENTE','estado vacuna incorrecto')
    val=repo.fetch_one("SELECT id FROM sn_valoraciones WHERE fundacion_id=1 AND documento='DOC-1'")
    service.validate_valoracion(1,val['id'],{'estado_validacion':'VALIDADA','clasificacion_profesional':'ADECUADO','observacion_profesional':'Revisada'},user)
    products=service.generate_capture(1,user,'UCA A','2026-08',('XLSX','PDF'))
    req(products['total_registros']==1 and len(products['productos'])==2,'CAPTURE no se generó')
    act=service.create_activity(1,{'unidad_nombre':'UCA A','linea_componente':'L2_EDUCACION_SALUD_ALIMENTARIA','tipo_actividad':'JORNADA','titulo':'Alimentación saludable','fecha_programada':'2026-08-10','participantes':[{'documento':'DOC-1','nombre_completo':'Ana Prueba'}]},user)
    docs=service.prepare_activity_documents(1,act['actividad']['id'],user,('ACTA','LISTADO_ASISTENCIA','INFORME'))
    req(len(docs['documentos'])==3,'productos actividad incompletos')
    period=service.save_monthly_period(1,{'anio_mes':'2026-08','temas':['Lactancia materna'],'variables':{'jornadas_desparasitacion':2}},user)
    req(period['estado']=='BORRADOR' and period['variables']['jornadas_desparasitacion']==2,'periodo mensual no se guardo')
    approved=service.approve_monthly_period(1,period['id'],user)
    req(approved['estado']=='APROBADO' and len(approved['integridad_sha256'])==64,'periodo mensual no se sello')
    reports=service.generate_monthly_report(1,period['id'],user,('XLSX','PDF'))
    req(len(reports['productos'])==2,'informe mensual no genero PDF y Excel')
    req(all(service.monthly_report_path(1,item['id']) for item in reports['productos']),'descarga mensual no valida integridad')
    req(all(service.monthly_report_path(2,item['id']) is None for item in reports['productos']),'descarga mensual cruzo fundaciones')
    try:
        service.save_monthly_period(1,{'anio_mes':'2026-08','temas':['Alteracion indebida']},user)
        raise AssertionError('permitio alterar periodo aprobado')
    except ValueError: pass
    minutes=service.create_institutional_minutes(1,{'actividad_id':act['actividad']['id'],'fecha':'2026-08-10','lugar':'UCA A','tema':'Seguimiento nutricional','puntos':['Resultados del mes'],'decisiones':['Mantener seguimiento'],'tareas':[{'descripcion':'Verificar controles','responsable_nombre':'Nutricionista','fecha_limite':'2026-08-20'}]},user)
    req(minutes['numero_acta']=='ACTA-SN-2026-0001' and len(minutes['tareas'])==1,'acta institucional incompleta')
    sealed=service.close_institutional_minutes(1,minutes['id'],user)
    req(sealed['estado']=='CERRADO' and len(sealed['integridad_sha256'])==64 and sealed['producto_id'],'acta no quedo sellada')
    second=service.create_institutional_minutes(1,{'fecha':'2026-08-11','tema':'Segunda reunion'},user)
    req(second['numero_acta']=='ACTA-SN-2026-0002','consecutivo anual incorrecto')
    req(service.list_monthly_periods(2)==[] and service.list_institutional_minutes(2)==[],'aislamiento institucional fallo')
    route=service.create_canalization(1,{'expediente_id':exp['id'],'tipo_ruta':'SALUD','motivo':'Seguimiento de prueba','entidad_destino':'IPS'},user)
    try:
        service.close_canalization(1,route['id'],{'resultado_cierre':'Atendido'},user)
        raise AssertionError('cerró sin evidencia')
    except ValueError: pass
    closed=service.close_canalization(1,route['id'],{'resultado_cierre':'Atendido','evidencia_cierre':'EV-001'},user)
    req(closed['estado']=='CERRADA','no cerró con evidencia')
    dash=service.dashboard(1,user,'UCA A'); req(dash['resumen']['expedientes']==1,'dashboard incorrecto')
    req(not repo.fetch_one("SELECT 1 FROM sn_expedientes_integrales WHERE fundacion_id=2"),'aislamiento de fundación falló')
print('Salud y Nutrición Integral: PASS')
