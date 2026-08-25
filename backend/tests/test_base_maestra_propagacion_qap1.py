from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def main():
    base = (ROOT / 'backend/modules/base_maestra/services.py').read_text(encoding='utf-8')
    talento_service = (ROOT / 'backend/modules/talento_humano/services.py').read_text(encoding='utf-8')
    talento_repo = (ROOT / 'backend/modules/talento_humano/repository.py').read_text(encoding='utf-8')
    schema = (ROOT / 'backend/modules/base_maestra/schema.py').read_text(encoding='utf-8')
    app = (ROOT / 'backend/app.py').read_text(encoding='utf-8')

    assert "fuente='base_maestra'" in base
    assert "master_projection_status" in base
    assert "master_projection_status" in schema
    assert "filas = self.repo.list_master_talento" in talento_service
    assert "FROM master_talento_humano" in talento_repo
    assert "WHERE fundacion_id=? AND activo=1" in talento_repo
    assert "AND COALESCE(fundacion_id,1) = ?" in talento_repo
    assert "fuente='base_maestra'" in app
    print('BASE_MAESTRA_PROPAGACION_QAP1_PASS')


if __name__ == '__main__':
    main()
