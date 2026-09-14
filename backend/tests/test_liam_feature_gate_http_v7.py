"""Las feature flags se aplican en endpoints HTTP, catálogo y panel visual."""
from pathlib import Path
import os,sys,tempfile
BACKEND=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BACKEND))
from flask import Flask,g
from modules.asistente_capacitacion.routes import register_asistente_capacitacion

names=('ENABLE_LIAM_ASSISTANT','LIAM_VISUAL_PANEL_ENABLED','LIAM_SEARCH_ENABLED','LIAM_ACTIONS_ENABLED','LIAM_ADMIN_ENABLED','LIAM_DEV_ENABLED','LIAM_REPAIR_ENABLED','LIAM_CONTEXT_GUIDE_ENABLED','LIAM_TOURS_ENABLED','LIAM_PLATFORM_PRESENTATION_ENABLED')
saved={name:os.environ.get(name) for name in names}
try:
    os.environ['ENABLE_LIAM_ASSISTANT']='true'
    for name in names[1:]:os.environ[name]='false'
    with tempfile.TemporaryDirectory() as tmp:
        app=Flask(__name__)
        @app.before_request
        def identity():g.current_user={'id':10,'fundacion_id':1,'rol':'SUPERADMIN','username':'admin'}
        register_asistente_capacitacion(app,str(Path(tmp)/'flags.db'));client=app.test_client()
        catalog=client.get('/api/asistente-capacitacion/tools');assert catalog.status_code==200
        tools=set(catalog.get_json()['tools'])
        for disabled in ('universal_search','get_system_health','propose_platform_action','get_dev_change_review'):assert disabled not in tools
        for tool,args in (('universal_search',{'query':'Juan'}),('get_system_health',{}),('propose_platform_action',{'command':'abre dashboard'}),('get_dev_change_review',{'request_id':'DEV-20260914-ABC12345'})):
            response=client.post('/api/asistente-capacitacion/tools/'+tool,json=args);assert response.status_code==403,(tool,response.get_json())
        repair=client.get('/api/asistente-capacitacion/repairs');assert repair.status_code==403 and repair.get_json()['repairs']==[]
        assert client.get('/api/asistente-capacitacion/contexto?modulo=dashboard').status_code==404
        assert client.get('/api/asistente-capacitacion/presentation').status_code==404
        assert client.get('/api/asistente-capacitacion/elian/platform-tour').status_code==404
        assert client.get('/api/asistente-capacitacion/elian/platform-tour/progress').status_code==404
        assert client.post('/api/asistente-capacitacion/progreso',json={'modulo':'dashboard'}).status_code==404
        safe=client.post('/api/asistente-capacitacion/tools/get_structured_error',json={'code':'PARTICIPANTES_REQUERIDOS'})
        assert safe.status_code==200 and safe.get_json()['ui']['disabledByFeatureFlag'] is True
finally:
    for name,value in saved.items():
        if value is None:os.environ.pop(name,None)
        else:os.environ[name]=value
print('LIAM_FEATURE_GATE_HTTP_V7_PASS')
