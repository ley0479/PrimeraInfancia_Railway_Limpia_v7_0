import sqlite3
import sys
import tempfile
from pathlib import Path
from flask import Flask

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / 'backend'
sys.path.insert(0, str(BACKEND))
from modules.salud_nutricion.repository import SaludNutricionRepository
from database import configure_database


def main():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / 'sn.db'
        conn = sqlite3.connect(db)
        conn.executescript('''
          CREATE TABLE beneficiarios(id INTEGER PRIMARY KEY,documento TEXT,nui TEXT,fundacion_id INTEGER);
          CREATE TABLE peso_talla(id INTEGER PRIMARY KEY AUTOINCREMENT,beneficiario_id INTEGER,documento TEXT,nombre TEXT,unidad TEXT,peso REAL,talla REAL,fecha_toma TEXT,estado TEXT,fecha_medicion TEXT,responsable TEXT,estado_nutricional TEXT,fecha_proximo_control TEXT,fecha_carga TEXT,fundacion_id INTEGER,usuario_creador_id INTEGER,fecha_actualizacion TEXT);
          INSERT INTO beneficiarios VALUES(10,'DOC-1','DOC-1',1);
          INSERT INTO beneficiarios VALUES(20,'DOC-1','DOC-1',2);
        ''')
        conn.commit(); conn.close()
        app = Flask('qap5')
        app.config.update(DATABASE_URL=f'sqlite:///{db.as_posix()}', DATABASE_PATH=str(db), SQLALCHEMY_ENGINE_OPTIONS={})
        configure_database(app)
        repo = SaludNutricionRepository(str(db)); repo.init_schema()
        valoracion = {
            'documento':'DOC-1','nombre_completo':'PERSONA MAESTRA','unidad':'UDS UNO',
            'fecha_valoracion':'2026-08-25','peso_kg':12.5,'talla_cm':88,
            'diagnostico_global':'Adecuado','estado_control':'Al día','proximo_control':'2026-11-25'
        }
        repo.guardar_valoracion(valoracion, 'REGISTRO_MANUAL_BASE_MAESTRA', 'prueba')
        conn = sqlite3.connect(db)
        row = conn.execute('SELECT beneficiario_id,documento,fundacion_id FROM peso_talla').fetchone()
        assert row == (10, 'DOC-1', 1), row
        conn.close()

        app_source = (BACKEND / 'app.py').read_text(encoding='utf-8')
        assert 'SELECT * FROM master_ninos' in app_source
        assert "fuente_archivo='REGISTRO_MANUAL_BASE_MAESTRA'" in app_source
    print('NUTRICION_IDENTIDAD_MAESTRA_QAP5_PASS')


if __name__ == '__main__':
    main()
