from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
ROBOTS = (ROOT / "frontend" / "robots.txt").read_text(encoding="utf-8")
SITEMAP = ROOT / "frontend" / "sitemap.xml"
APP = (ROOT / "backend" / "app.py").read_text(encoding="utf-8")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    require('<meta name="description"' in HTML, "Falta la descripción pública")
    require('<meta name="robots" content="index, follow' in HTML, "La portada no autoriza indexación")
    require('<link rel="canonical" href="https://primerainfancia.pro/">' in HTML, "Falta canonical")
    require('property="og:title"' in HTML and 'type="application/ld+json"' in HTML, "Faltan Open Graph o datos estructurados")
    require("Plataforma de gestión integral para programas de primera infancia" in HTML, "Falta contenido público descriptivo")
    require("Disallow: /api/" in ROBOTS and "Disallow: /docs/" in ROBOTS, "robots.txt no protege rutas privadas")
    require("Sitemap: https://primerainfancia.pro/sitemap.xml" in ROBOTS, "robots.txt no anuncia el sitemap")
    root = ET.parse(SITEMAP).getroot()
    namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locations = [item.text for item in root.findall("s:url/s:loc", namespace)]
    require(locations == ["https://primerainfancia.pro/"], "El sitemap debe publicar únicamente la portada")
    require("@app.route('/robots.txt')" in APP and "@app.route('/sitemap.xml')" in APP, "Faltan rutas públicas explícitas")
    print("PASS test_public_seo_contract_v2_7_6")


if __name__ == "__main__":
    main()
