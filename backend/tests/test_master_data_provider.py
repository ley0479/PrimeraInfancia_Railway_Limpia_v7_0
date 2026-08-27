import sqlite3
import unittest

from backend.services.master_data_provider import MasterDataProvider


def connection():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE master_versiones(id INTEGER PRIMARY KEY, fundacion_id INTEGER, activa INTEGER);
        CREATE TABLE master_ninos(id INTEGER PRIMARY KEY, fundacion_id INTEGER, documento TEXT, nombre_completo TEXT, activo INTEGER);
        CREATE TABLE beneficiarios(id INTEGER PRIMARY KEY, fundacion_id INTEGER, documento TEXT, nombre TEXT);
        """
    )
    return conn


class MasterDataProviderTests(unittest.TestCase):
    def test_published_master_blocks_legacy_fallback_and_promotes_historical_reference(self):
        conn = connection()
        conn.execute("INSERT INTO master_versiones VALUES(1,7,1)")
        conn.execute("INSERT INTO master_ninos VALUES(20,7,'ABC','Nombre maestro',1)")
        conn.execute("INSERT INTO beneficiarios VALUES(9,7,'ABC','Nombre antiguo')")

        self.assertIsNone(MasterDataProvider.allowed_participant_source(conn, 7, "beneficiarios"))
        row, source = MasterDataProvider.resolve_historical_participant(conn, 7, "beneficiarios", 9)
        self.assertEqual(source, "master_ninos")
        self.assertEqual(row["id"], 20)
        self.assertEqual(row["nombre_completo"], "Nombre maestro")

    def test_published_master_never_exposes_orphaned_legacy_record(self):
        conn = connection()
        conn.execute("INSERT INTO master_versiones VALUES(1,7,1)")
        conn.execute("INSERT INTO beneficiarios VALUES(9,7,'NO-MASTER','Nombre antiguo')")

        row, source = MasterDataProvider.resolve_historical_participant(conn, 7, "beneficiarios", 9)
        self.assertIsNone(row)
        self.assertIsNone(source)

    def test_legacy_is_available_only_before_first_master_publication(self):
        conn = connection()
        conn.execute("INSERT INTO beneficiarios VALUES(9,7,'LEGACY','Nombre antiguo')")

        self.assertEqual(MasterDataProvider.allowed_participant_source(conn, 7, "beneficiarios"), "beneficiarios")
        row, source = MasterDataProvider.resolve_historical_participant(conn, 7, "beneficiarios", 9)
        self.assertEqual(source, "beneficiarios")
        self.assertEqual(row["id"], 9)


if __name__ == "__main__":
    unittest.main()
