"""Calidad de Base Maestra: hallazgos reales, solo lectura y alcance institucional."""
from pathlib import Path
import sys
import tempfile

BACKEND=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BACKEND))
from modules.asistente_capacitacion.orchestrator import LiamOrchestrator
from modules.dbapi_compat import sqlite3

with tempfile.TemporaryDirectory() as tmp:
    db=str(Path(tmp)/'quality.db');conn=sqlite3.connect(db)
    conn.execute('''CREATE TABLE master_ninos(id INTEGER PRIMARY KEY,fundacion_id INTEGER,activo INTEGER,documento TEXT,nombre_completo TEXT,fecha_nacimiento TEXT,grupo_etario TEXT,unidad_servicio TEXT,codigo_unidad TEXT,coordinador TEXT,docente TEXT)''')
    conn.execute('''CREATE TABLE master_unidades(id INTEGER PRIMARY KEY,fundacion_id INTEGER,activo INTEGER,nombre TEXT,codigo_unidad TEXT,coordinador TEXT)''')
    conn.execute('''CREATE TABLE master_talento_humano(id INTEGER PRIMARY KEY,fundacion_id INTEGER,activo INTEGER,rol_normalizado TEXT,cargo TEXT,unidad_servicio TEXT,coordinador TEXT)''')
    conn.execute('CREATE TABLE master_inconsistencias(id INTEGER PRIMARY KEY,fundacion_id INTEGER,resuelta INTEGER)')
    conn.executemany('INSERT INTO master_ninos VALUES(?,?,?,?,?,?,?,?,?,?,?)',[
      (1,1,1,'D1','Uno','2021-01-01','3 a 5','UDS A','A','Ana','Dora'),
      (2,1,1,'D1','Duplicado','2021-01-02','3 a 5','UDS A','A','Ana','Dora'),
      (3,1,1,'','','','','','','Ana','Dora'),
      (4,1,1,'D4','Cuatro','2021-01-04','3 a 5','UDS X','X','Ana','Dora'),
      (5,1,1,'OTRO','Otro','2021-01-05','3 a 5','UDS B','B','Bea','Diego'),
      (6,2,1,'D1','Ajeno','2021-01-06','3 a 5','UDS AJENA','Z','Ana','Dora')])
    conn.executemany('INSERT INTO master_unidades VALUES(?,?,?,?,?,?)',[(1,1,1,'UDS A','A','Ana'),(2,1,1,'UDS B','B',''),(3,2,1,'UDS AJENA','Z','Ana')])
    conn.executemany('INSERT INTO master_talento_humano VALUES(?,?,?,?,?,?,?)',[(1,1,1,'DOCENTE',None,'','Ana'),(2,1,1,'DOCENTE',None,'UDS B','Bea')])
    conn.executemany('INSERT INTO master_inconsistencias VALUES(?,?,?)',[(1,1,0),(2,2,0)])
    conn.commit();conn.close()
    data=LiamOrchestrator(db).run('analyze_master_data_quality',args={},tenant_id=1,user={'id':3,'rol':'COORDINADOR','nombre_completo':'Ana'}).result
    summary=data['summary']
    assert data['total_records']==4 and data['role_scope']=='assigned_records'
    assert summary['duplicate_document_groups']==1 and summary['duplicate_excess_records']==1
    assert summary['unregistered_units']==1 and summary['teachers_without_unit']==1
    assert summary['open_registered_inconsistencies']==1
    assert data['automatic_corrections'] is False and data['read_only'] is True
    assert data['scope']['cross_foundation'] is False
    assert all('D1' not in str(item) for item in data['findings'])

print('LIAM_MASTER_QUALITY_V7_PASS')
