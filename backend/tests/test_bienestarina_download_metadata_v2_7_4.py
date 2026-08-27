"""La descarga directa conserva fecha, lote, cantidad y periodo ingresados."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
frontend = (ROOT / "frontend/js/app.js").read_text(encoding="utf-8")
backend = (ROOT / "backend/app.py").read_text(encoding="utf-8")

start = frontend.index("async function descargarBienestarinaAlpha62")
end = frontend.index("async function descargarRppCategoria", start)
helper = frontend[start:end]

for contract in (
    "periodoFormatosSeleccionado()",
    "fecha-entrega-bienestarina",
    "lote-bienestarina",
    "cantidad-bienestarina",
    "fecha_entrega: fechaEntrega",
    "mes: String(periodo.mes)",
    "anio: String(periodo.anio)",
):
    assert contract in helper, f"Falta enviar {contract} en descarga de Bienestarina"

endpoint_start = backend.index("def descargar_bienestarina_alpha57")
endpoint_end = backend.index("def descargar_rpp_por_categoria", endpoint_start)
endpoint = backend[endpoint_start:endpoint_end]
assert "_alpha75_actualizar_archivo_bienestarina" in endpoint
assert "request.args.get('mes')" in endpoint
assert "request.args.get('anio')" in endpoint

metadata_start = backend.index("def _alpha59_metadata_formato")
metadata_end = backend.index("def _alpha59_generar_oficial_desde_template", metadata_start)
metadata = backend[metadata_start:metadata_end]
assert "request.args.get('fecha_entrega')" in metadata
assert "request.args.get('lote')" in metadata
assert "request.args.get('cantidad')" in metadata

print("Bienestarina descarga con fecha/lote/cantidad/periodo: PASS")
