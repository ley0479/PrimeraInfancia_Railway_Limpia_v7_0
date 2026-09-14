"""Relación del Mes consultable y visualizable por Lía."""
from pathlib import Path
import sys,tempfile

BACKEND=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BACKEND))
from modules.dbapi_compat import sqlite3
from modules.asistente_capacitacion.action_intents import propose_action
from modules.asistente_capacitacion.tool_registry import execute

assert propose_action('Explica la Relación del Mes de septiembre de 2026')['server_tool']=='get_monthly_relation_summary'
with tempfile.TemporaryDirectory() as tmp:
    db=str(Path(tmp)/'relation.db');conn=sqlite3.connect(db)
    conn.execute('''CREATE TABLE master_ninos(unidad_servicio TEXT,grupo_etario TEXT,edad_meses INTEGER,fecha_nacimiento TEXT,estado TEXT,docente TEXT,datos_json TEXT,activo INTEGER,fundacion_id INTEGER)''')
    conn.executemany('INSERT INTO master_ninos VALUES(?,?,?,?,?,?,?,?,?)',[
        ('UDS UNO','3 A 5 AÑOS',48,'2022-09-01','ACTIVO','DOCENTE UNO','{}',1,1),
        ('UDS UNO','6 A 11 MESES',8,'2026-01-01','ACTIVO','DOCENTE UNO','{}',1,1),
        ('UDS AJENA','3 A 5 AÑOS',48,'2022-09-01','ACTIVO','OTRO','{}',1,2),
    ]);conn.commit();conn.close()
    result=execute('get_monthly_relation_summary',args={'period':'2026-09'},database_path=db,tenant_id=1,user={'rol':'DOCENTE'})
    assert len(result['columns'])==19 and len(result['relation_rows'])==1
    assert result['relation_rows'][0][0]=='UDS UNO' and result['relation_rows'][0][8]==2
    assert result['relation_rows'][0][11]==45 and result['relation_rows'][0][12]==2
    assert result['total_row'][8]==2 and result['scope']['cross_foundation'] is False
print('LIA_MONTHLY_RELATION_UI_V7_PASS')
