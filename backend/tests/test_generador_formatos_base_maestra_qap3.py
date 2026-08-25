import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))

from generador_formatos import GeneradorFormatos


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        db = root / 'qap3.db'
        conn = sqlite3.connect(db)
        conn.executescript('''
            CREATE TABLE master_versiones(id INTEGER PRIMARY KEY,fundacion_id INTEGER,activa INTEGER);
            CREATE TABLE master_ninos(id INTEGER PRIMARY KEY,activo INTEGER,fundacion_id INTEGER,
                documento TEXT,nombre_completo TEXT,unidad_servicio TEXT,datos_json TEXT);
            CREATE TABLE beneficiarios(id INTEGER PRIMARY KEY,fundacion_id INTEGER,documento TEXT,
                nombres TEXT,unidad TEXT,estado TEXT);
            INSERT INTO master_versiones VALUES(1,1,1);
            INSERT INTO master_ninos VALUES(10,1,1,'M-1','PERSONA MAESTRA','UDS UNO','{}');
            INSERT INTO beneficiarios VALUES(20,1,'L-1','PERSONA ANTIGUA','UDS UNO','ACTIVO');
        ''')
        conn.commit(); conn.close()
        gen = GeneradorFormatos(str(db), str(root), str(root))
        rows = gen._participantes_unidad('UDS UNO')
        assert [r['documento'] for r in rows] == ['M-1']

        conn = sqlite3.connect(db)
        conn.execute('UPDATE master_versiones SET activa=0')
        conn.commit(); conn.close()
        rows = gen._participantes_unidad('UDS UNO')
        assert [r['documento'] for r in rows] == ['L-1']
    print('GENERADOR_FORMATOS_BASE_MAESTRA_QAP3_PASS')


if __name__ == '__main__':
    main()
