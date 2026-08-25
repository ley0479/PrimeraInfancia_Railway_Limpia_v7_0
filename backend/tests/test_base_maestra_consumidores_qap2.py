import sqlite3
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / 'backend'
sys.path.insert(0, str(BACKEND))

from modules.centro_planeacion.repository import CentroPlaneacionRepository
from modules.componente_psicosocial.repository import ComponentePsicosocialRepository
from modules.familias_redes.repository import FamiliasRedesRepository


def preparar(db: Path):
    conn = sqlite3.connect(db)
    conn.executescript("""
        CREATE TABLE master_versiones(id INTEGER PRIMARY KEY,fundacion_id INTEGER,activa INTEGER);
        CREATE TABLE master_ninos(id INTEGER PRIMARY KEY,fundacion_id INTEGER,activo INTEGER,documento TEXT,nombre_completo TEXT,unidad_servicio TEXT,estado TEXT);
        CREATE TABLE beneficiarios(id INTEGER PRIMARY KEY,fundacion_id INTEGER,documento TEXT,nombres TEXT,primer_nombre TEXT,apellidos TEXT,primer_apellido TEXT,unidad TEXT,estado TEXT);
        CREATE TABLE usuarios(id INTEGER PRIMARY KEY,fundacion_id INTEGER,documento TEXT,nombre TEXT,unidad TEXT,estado TEXT);
    """)
    conn.execute("INSERT INTO master_versiones VALUES(10,1,1)")
    conn.execute("INSERT INTO master_ninos VALUES(100,1,1,'DOC-1','NOMBRE MAESTRO','UCA UNO','ACTIVO')")
    conn.execute("INSERT INTO beneficiarios VALUES(200,1,'DOC-1','NOMBRE ANTIGUO','NOMBRE','ANTIGUO','ANTIGUO','UCA UNO','ACTIVO')")
    conn.execute("INSERT INTO beneficiarios VALUES(201,1,'DOC-2','SOLO ANTIGUO','SOLO','ANTIGUO','ANTIGUO','UCA DOS','ACTIVO')")
    conn.commit(); conn.close()


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp); db = root / 'qap2.db'; preparar(db)
        planning = CentroPlaneacionRepository(str(db), str(root), str(root))
        with planning.connect() as conn:
            rows, source = planning._ram_participant_rows(conn, 1, 'UCA UNO')
            assert source == 'master_ninos' and len(rows) == 1 and rows[0]['nombre_completo'] == 'NOMBRE MAESTRO'
            rows, source = planning._ram_participant_rows(conn, 1, 'UCA DOS')
            assert source == 'master_ninos' and rows == [], 'Una versión activa no debe caer a beneficiarios antiguos'
            conn.execute("UPDATE master_versiones SET activa=0")
            rows, source = planning._ram_participant_rows(conn, 1, 'UCA DOS')
            assert source.startswith('beneficiarios_compatibilidad') and len(rows) == 1

        families = FamiliasRedesRepository(str(db), str(root), str(root))
        with families.connect() as conn:
            participant = families._participant_source(conn, 1, 'beneficiarios', 200)
            assert participant['origen'] == 'master_ninos' and participant['nombre'] == 'NOMBRE MAESTRO'

        psico = ComponentePsicosocialRepository(str(db), str(root), str(root))
        with psico.connect() as conn:
            participant = psico._participant(conn, 'beneficiarios', 200, 1)
            assert participant['origen'] == 'master_ninos' and participant['nombre'] == 'NOMBRE MAESTRO'

        cruce_source = (BACKEND / 'modules' / 'cruce_bases' / 'routes.py').read_text(encoding='utf-8')
        assert "fuente = 'master_ninos' if version_activa else 'usuarios'" in cruce_source
        assert "unidad_servicio AS unidad, nombre_completo AS nombre" in cruce_source

        app_source = (BACKEND / 'app.py').read_text(encoding='utf-8')
        assert "if version_activa else\n            (('master_ninos',), ('usuarios', 'beneficiarios'))" in app_source
    print('BASE_MAESTRA_CONSUMIDORES_QAP2_PASS')


if __name__ == '__main__':
    main()
