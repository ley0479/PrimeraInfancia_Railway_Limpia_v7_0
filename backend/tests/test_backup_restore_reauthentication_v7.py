"""Reautenticación HTTP obligatoria antes del restaurador real."""
from pathlib import Path
import os,sys,tempfile
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from flask import Flask,g
from werkzeug.security import generate_password_hash
from modules.backups.routes import register_backups
from modules.dbapi_compat import sqlite3

os.environ['APP_SCHEMA_MIGRATION_MODE']='true'
with tempfile.TemporaryDirectory() as tmp:
    db=str(Path(tmp)/'backup-auth.db');folder=str(Path(tmp)/'backups');app=Flask(__name__)
    @app.before_request
    def identity():g.current_user={'id':7,'fundacion_id':1,'rol':'SUPERADMIN','username':'admin'}
    register_backups(app,db,folder);conn=sqlite3.connect(db)
    conn.execute('CREATE TABLE usuarios_app(id INTEGER PRIMARY KEY,fundacion_id INTEGER,rol TEXT,activo INTEGER,password_hash TEXT)')
    conn.execute('INSERT INTO usuarios_app VALUES(?,?,?,?,?)',(7,1,'SUPERADMIN',1,generate_password_hash('Clave-Segura-2026!')));conn.commit();conn.close();client=app.test_client()
    missing=client.post('/api/backups/999/restaurar',json={'confirmar':'RESTAURAR'});assert missing.status_code==403
    wrong=client.post('/api/backups/999/restaurar',json={'confirmar':'RESTAURAR','password_actual':'incorrecta'});assert wrong.status_code==403
    valid=client.post('/api/backups/999/restaurar',json={'confirmar':'RESTAURAR','password_actual':'Clave-Segura-2026!'});assert valid.status_code==500
    conn=sqlite3.connect(db);events=conn.execute('SELECT accion,detalle FROM backups_auditoria ORDER BY id').fetchall();conn.close()
    assert [row[0] for row in events].count('BACKUP_RESTAURACION_REAUTENTICACION_FALLIDA')==2
    assert any(row[0]=='BACKUP_RESTAURACION_REAUTENTICADA' for row in events)
    assert 'Clave-Segura-2026!' not in str(events) and 'incorrecta' not in str(events)

index=(ROOT/'frontend'/'index.html').read_text(encoding='utf-8')
assert 'backups.js?v=2.7.5-reauth-1' in index
print('BACKUP_RESTORE_REAUTHENTICATION_V7_PASS')
