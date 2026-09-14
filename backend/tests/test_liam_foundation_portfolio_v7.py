"""Portafolio global: permiso elevado, estados, actividad y créditos."""
from datetime import date, timedelta
from pathlib import Path
import sys
import tempfile

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from modules.asistente_capacitacion.orchestrator import LiamOrchestrator
from modules.dbapi_compat import sqlite3

with tempfile.TemporaryDirectory() as tmp:
    db=str(Path(tmp)/'portfolio.db');conn=sqlite3.connect(db)
    conn.execute('CREATE TABLE fundaciones(id INTEGER PRIMARY KEY,nombre TEXT,estado TEXT,plan TEXT,eliminado_en TEXT)')
    conn.execute('CREATE TABLE usuarios_app(id INTEGER PRIMARY KEY,fundacion_id INTEGER,activo INTEGER)')
    conn.execute('CREATE TABLE sesiones_usuario(id INTEGER PRIMARY KEY,fundacion_id INTEGER,fecha_creacion TEXT)')
    conn.execute('CREATE TABLE planes_suscripcion(id INTEGER PRIMARY KEY,nombre TEXT)')
    conn.execute('''CREATE TABLE suscripciones_fundacion(id INTEGER PRIMARY KEY,fundacion_id INTEGER,plan_id INTEGER,
      estado TEXT,fecha_vencimiento TEXT,creditos_disponibles INTEGER,creditos_incluidos_periodo INTEGER)''')
    today=date.today();soon=(today+timedelta(days=10)).isoformat();past=(today-timedelta(days=1)).isoformat();future=(today+timedelta(days=100)).isoformat()
    conn.executemany('INSERT INTO fundaciones VALUES(?,?,?,?,?)',[(1,'A','ACTIVA','',None),(2,'B','ACTIVA','',None),(3,'C','ACTIVA','',None),(4,'ELIMINADA','ACTIVA','',today.isoformat())])
    conn.execute("INSERT INTO planes_suscripcion VALUES(1,'PREMIUM')")
    conn.executemany('INSERT INTO suscripciones_fundacion VALUES(?,?,?,?,?,?,?)',[(1,1,1,'ACTIVA',soon,10,100),(2,2,1,'VENCIDA',past,0,100),(3,3,1,'ACTIVA',future,50,100),(4,4,1,'ACTIVA',future,50,100)])
    conn.executemany('INSERT INTO usuarios_app VALUES(?,?,?)',[(1,1,1),(2,3,1)])
    conn.execute("INSERT INTO sesiones_usuario VALUES(1,1,'2026-09-14T08:00:00')")
    conn.commit();conn.close()
    orchestrator=LiamOrchestrator(db)
    data=orchestrator.run('get_foundation_portfolio',args={},tenant_id=1,user={'id':1,'rol':'SUPERADMIN'}).result
    assert data['scope']=={'type':'authorized_global','cross_foundation':True,'role':'SUPERADMIN'}
    assert data['summary']=={'total':3,'active':2,'expiring':1,'expired':1,'without_users':1,'without_activity':2,'low_credit':1,'exhausted_credit':1}
    assert {item['foundation'] for item in data['items']}=={'A','B','C'}
    assert next(x for x in data['items'] if x['foundation']=='A')['alert']=='ALTA'
    assert next(x for x in data['items'] if x['foundation']=='B')['alert']=='CRITICA'
    assert data['read_only'] is True
    try:orchestrator.run('get_foundation_portfolio',args={},tenant_id=1,user={'id':2,'rol':'GERENTE'})
    except PermissionError:pass
    else:raise AssertionError('Un rol no autorizado obtuvo información global.')

print('LIAM_FOUNDATION_PORTFOLIO_V7_PASS')
