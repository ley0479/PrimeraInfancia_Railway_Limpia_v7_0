"""Migración idempotente de favoritos en el predeploy."""
from pathlib import Path
import sys,tempfile
from flask import Flask
from sqlalchemy import text
BACKEND=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BACKEND))
from database import database
from migrations.migrate_liam_command_favorites_v7 import migrate

with tempfile.TemporaryDirectory() as tmp:
    path=Path(tmp)/'migration.db';app=Flask(__name__);app.config.update(DATABASE_URL=f'sqlite:///{path.as_posix()}',DATABASE_PATH=str(path),SQLALCHEMY_ENGINE_OPTIONS={});database.configure(app)
    with app.app_context():
        assert migrate()['status']=='PASS';assert migrate()['version']==1
        with database.connection() as conn:
            conn.execute(text("INSERT INTO lia_command_favorites(fundacion_id,usuario_id,nombre,comando,created_at,updated_at) VALUES(1,2,'X','Abre calendario','x','x')"));conn.commit()
            assert conn.execute(text("SELECT COUNT(*) AS total FROM lia_command_favorites")).mappings().fetchone()['total']==1
        database.dispose()

print('LIAM_FAVORITES_MIGRATION_V7_PASS')
