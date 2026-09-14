"""Favoritos persistentes, aislados y ejecutables solo mediante herramientas seguras."""
from pathlib import Path
import os,sys,tempfile
BACKEND=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BACKEND))
from flask import Flask,g,request
from modules.asistente_capacitacion.routes import register_asistente_capacitacion
from modules.asistente_capacitacion.orchestrator import LiamOrchestrator
from modules.dbapi_compat import sqlite3

controller=(BACKEND.parent/'frontend/js/liam/liam-controller.js').read_text(encoding='utf-8')
assert 'data-action="favorite-save"' in controller and 'data-action="favorite-list"' in controller
assert 'data-favorite-run' in controller and 'data-favorite-delete' in controller

os.environ['ENABLE_LIA_ASSISTANT']='true';os.environ['ENABLE_LIAM_ASSISTANT']='true'
with tempfile.TemporaryDirectory() as tmp:
    db=str(Path(tmp)/'favorites.db');app=Flask(__name__)
    @app.before_request
    def identity():
        key=request.headers.get('X-Test-Identity','u1');g.current_user={'u1':{'id':10,'fundacion_id':1,'rol':'GERENTE','username':'u1'},'u2':{'id':11,'fundacion_id':1,'rol':'GERENTE','username':'u2'},'u3':{'id':10,'fundacion_id':2,'rol':'GERENTE','username':'u3'}}[key]
    register_asistente_capacitacion(app,db);client=app.test_client()
    first=client.post('/api/asistente-capacitacion/command-favorites',json={'name':'Pendientes docentes','command':'Muéstrame los pendientes de mi equipo'},headers={'X-Test-Identity':'u1'});assert first.status_code==201
    second=client.post('/api/asistente-capacitacion/command-favorites',json={'name':'Reporte mensual','command':'Genera el RAM de Bajo Pacurita para septiembre de 2026'},headers={'X-Test-Identity':'u1'});assert second.status_code==201
    client.post('/api/asistente-capacitacion/command-favorites',json={'name':'Privado','command':'Abre calendario'},headers={'X-Test-Identity':'u2'})
    client.post('/api/asistente-capacitacion/command-favorites',json={'name':'Otro tenant','command':'Abre calendario'},headers={'X-Test-Identity':'u3'})
    listed=client.get('/api/asistente-capacitacion/command-favorites',headers={'X-Test-Identity':'u1'}).get_json()['favorites'];assert [x['nombre'] for x in listed]==['Pendientes docentes','Reporte mensual']
    updated=client.post('/api/asistente-capacitacion/command-favorites',json={'name':'pendientes docentes','command':'Muéstrame los pendientes de mi equipo de septiembre de 2026'},headers={'X-Test-Identity':'u1'});assert updated.status_code==200 and updated.get_json()['created'] is False
    forbidden_delete=client.delete(f"/api/asistente-capacitacion/command-favorites/{first.get_json()['favorite']['id']}",headers={'X-Test-Identity':'u2'});assert forbidden_delete.status_code==404
    conn=sqlite3.connect(db);conn.execute('''CREATE TABLE calendario_entregables(id INTEGER PRIMARY KEY,fundacion_id INTEGER,titulo TEXT,fecha_limite TEXT,modulo TEXT,responsable_nombre TEXT,coordinador TEXT,unidad TEXT,estado TEXT,prioridad TEXT,requiere_evidencia INTEGER,archivo_evidencia TEXT,fecha_entrega TEXT,clave_unica TEXT)''');conn.commit();conn.close()
    run=LiamOrchestrator(db).run('run_command_favorite',args={'name':'Pendientes docentes'},tenant_id=1,user={'id':10,'rol':'GERENTE','username':'u1'}).result
    assert run['executed'] is True and run['resolved_action']=='get_pending_activities_summary'
    mutable=LiamOrchestrator(db).run('run_command_favorite',args={'name':'Reporte mensual'},tenant_id=1,user={'id':10,'rol':'GERENTE','username':'u1'}).result
    assert mutable['executed'] is False and mutable['confirmation_required'] is True
    assert mutable['proposal']['id']=='download_ram'
    protected=client.post('/api/asistente-capacitacion/command-favorites',json={'name':'Consulta protegida','command':'Busca documento 1234567890 token=private-favorite-token'},headers={'X-Test-Identity':'u2'});assert protected.status_code==201
    saved_command=protected.get_json()['favorite']['command'];assert 'private-favorite-token' not in saved_command and '1234567890' in saved_command
    conn=sqlite3.connect(db);raw=conn.execute('SELECT comando FROM lia_command_favorites WHERE id=?',(protected.get_json()['favorite']['id'],)).fetchone()[0];conn.close()
    assert 'private-favorite-token' not in raw and '1234567890' in raw

print('LIAM_COMMAND_FAVORITES_V7_PASS')
