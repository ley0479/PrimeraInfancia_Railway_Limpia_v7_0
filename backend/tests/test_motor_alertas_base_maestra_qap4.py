import sqlite3
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from motor_alertas import MotorAlertas


def main():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / 'alertas.db'
        conn = sqlite3.connect(db)
        conn.executescript('''
          CREATE TABLE master_ninos(id INTEGER PRIMARY KEY,version_id INTEGER,activo INTEGER,fundacion_id INTEGER,documento TEXT,nombre_completo TEXT,unidad_servicio TEXT,fecha_nacimiento TEXT);
          CREATE TABLE master_salud_nutricion(id INTEGER PRIMARY KEY,version_id INTEGER,activo INTEGER,fundacion_id INTEGER,documento TEXT,fecha_toma TEXT,estado_nutricional TEXT);
          CREATE TABLE beneficiarios(id INTEGER PRIMARY KEY,documento TEXT);
          CREATE TABLE alertas(id INTEGER PRIMARY KEY AUTOINCREMENT,beneficiario_id INTEGER,tipo_alerta TEXT,nivel TEXT,descripcion TEXT,detalles TEXT,resuelta INTEGER DEFAULT 0,fecha_generacion TEXT,fecha_resolucion TEXT);
          INSERT INTO master_ninos VALUES(10,1,1,1,'DOC1','NIÑA MAESTRA','UDS UNO','2020-01-01');
          INSERT INTO master_ninos VALUES(11,1,1,1,'DOC1','NIÑA DUPLICADA','UDS DOS','2020-01-01');
          INSERT INTO master_ninos VALUES(12,1,1,2,'OTRO','OTRO TENANT','UDS UNO','2020-01-01');
        ''')
        conn.commit(); conn.close()
        motor = MotorAlertas(str(db))
        assert motor.generar_alertas_edad() >= 1
        assert motor.generar_alertas_nutricion() >= 1
        assert motor.generar_alertas_cobertura() >= 1
        assert motor.generar_alertas_duplicados() == 1
        conn = sqlite3.connect(db)
        tipos = {r[0] for r in conn.execute('SELECT tipo_alerta FROM alertas')}
        assert {'EDAD_RETIRO','NUTRICION_VENCIDA','COBERTURA_BAJA','USUARIO_DUPLICADO'} <= tipos
        assert conn.execute('SELECT COUNT(*) FROM alertas WHERE beneficiario_id IS NOT NULL').fetchone()[0] == 0
        conn.close()
    print('MOTOR_ALERTAS_BASE_MAESTRA_QAP4_PASS')


if __name__ == '__main__':
    main()
