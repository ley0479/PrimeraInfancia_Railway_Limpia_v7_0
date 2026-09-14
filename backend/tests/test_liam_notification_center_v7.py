"""Centro de notificaciones: múltiples fuentes, destinatario y tenant."""
from pathlib import Path
import sys,tempfile
BACKEND=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BACKEND))
from modules.asistente_capacitacion.orchestrator import LiamOrchestrator
from modules.dbapi_compat import sqlite3

with tempfile.TemporaryDirectory() as tmp:
    db=str(Path(tmp)/'notifications.db');c=sqlite3.connect(db)
    c.execute('CREATE TABLE cpo_notificaciones(id INTEGER PRIMARY KEY,fundacion_id INTEGER,titulo TEXT,nivel TEXT,estado TEXT,fecha_programada TEXT,leida INTEGER,destinatario_id INTEGER,destinatario_rol TEXT)')
    c.executemany('INSERT INTO cpo_notificaciones VALUES(?,?,?,?,?,?,?,?,?)',[(1,1,'Mi planeación','INFO','PENDIENTE','2026-09-15',0,10,None),(2,1,'De otro usuario','INFO','PENDIENTE','2026-09-15',0,11,None),(3,2,'Otro tenant','INFO','PENDIENTE','2026-09-15',0,10,None)])
    c.execute('CREATE TABLE calendario_alertas(id INTEGER PRIMARY KEY,fundacion_id INTEGER,usuario_id INTEGER,tipo TEXT,nivel TEXT,estado TEXT,fecha_programada TEXT,fecha TEXT,created_at TEXT)')
    c.executemany('INSERT INTO calendario_alertas VALUES(?,?,?,?,?,?,?,?,?)',[(1,1,10,'VENCIMIENTO','ALTA','ACTIVA','2026-09-14',None,None),(2,1,None,'GENERAL','ADVERTENCIA','ACTIVA','2026-09-14',None,None),(3,1,11,'AJENA','ALTA','ACTIVA','2026-09-14',None,None)])
    c.execute('CREATE TABLE lia_error_incidents(id INTEGER PRIMARY KEY,fundacion_id INTEGER,usuario_id INTEGER,incident_id TEXT,error_code TEXT,severity TEXT,status TEXT,created_at TEXT)')
    c.executemany('INSERT INTO lia_error_incidents VALUES(?,?,?,?,?,?,?,?)',[(1,1,10,'INC-OWN','E1','high','OPEN','2026-09-14'),(2,1,11,'INC-OTHER','E2','high','OPEN','2026-09-14')])
    c.execute('CREATE TABLE doc_instancias(id INTEGER PRIMARY KEY,fundacion_id INTEGER,tipo_documento TEXT,estado TEXT,actualizado_en TEXT,creado_por INTEGER)')
    c.executemany('INSERT INTO doc_instancias VALUES(?,?,?,?,?,?)',[(1,1,'RPP','BORRADOR','2026-09-14',10),(2,1,'RAM','DEVUELTO','2026-09-14',11)])
    c.execute('CREATE TABLE suscripciones_fundacion(id INTEGER PRIMARY KEY,fundacion_id INTEGER,estado TEXT,fecha_vencimiento TEXT,creditos_disponibles INTEGER,creditos_incluidos_periodo INTEGER)');c.execute("INSERT INTO suscripciones_fundacion VALUES(1,1,'ACTIVA','2026-09-30',0,100)")
    c.commit();c.close()
    data=LiamOrchestrator(db).run('get_notification_center',args={},tenant_id=1,user={'id':10,'rol':'DOCENTE'}).result
    assert data['summary']=={'total':6,'critical':2,'warning':2,'information':2}
    assert data['role_scope']=='own_or_role_targeted' and data['send_actions'] is False
    serialized=str(data)
    for forbidden in ('De otro usuario','Otro tenant','INC-OTHER','RAM requiere atención','AJENA'):
        assert forbidden not in serialized
    assert all(source['available'] for source in data['sources'])
    assert data['scope']['cross_foundation'] is False and data['read_only'] is True

print('LIAM_NOTIFICATION_CENTER_V7_PASS')
