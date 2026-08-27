from pathlib import Path


def main():
    root = Path(__file__).parents[2]
    html = (root / "frontend" / "index.html").read_text(encoding="utf-8")
    js = (root / "frontend" / "js" / "modules" / "institucional-normativo.js").read_text(encoding="utf-8")
    assert 'id="ci-preview-logo"' in html
    assert 'id="ci-preview-foto-admin"' in html
    assert 'id="ci-preview-foto-admin-fallback"' in html
    assert "setImage('ci-preview-foto-admin', 'ci-preview-foto-admin-fallback', configuracionActual.foto_admin_url" in js
    print("IDENTIDAD_PREVIEW_LOGO_ADMIN_PASS")


if __name__ == "__main__":
    main()
