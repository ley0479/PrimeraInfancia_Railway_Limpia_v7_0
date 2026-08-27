from pathlib import Path


def main():
    source = (Path(__file__).parents[2] / "frontend" / "js" / "modules" / "institucional-normativo.js").read_text(encoding="utf-8")
    generator = source[source.index("async function generarRecursosIdentidad"):source.index("async function aplicarLoteIdentidad")]
    restore = source[source.index("async function activarArchivoIdentidadVisual"):source.index("function bindGeneratorPreview")]
    upload = source[source.index("async function subirArchivoConfiguracion"):source.index("const assetLabels")]
    assert "/api/identidad-visual/lote/${encodeURIComponent(data.lote_id)}/aplicar" in generator
    assert "await cargarIdentidadEfectiva(true)" in generator
    assert "await cargarIdentidadEfectiva(true)" in restore
    assert "await cargarIdentidadEfectiva(true)" in upload
    print("IDENTIDAD_VISUAL_ACTIVACION_INMEDIATA_PASS")


if __name__ == "__main__":
    main()
