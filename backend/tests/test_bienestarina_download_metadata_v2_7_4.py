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
assert "request.args.get('fecha_entrega_bienestarina')" in metadata
assert "request.args.get('lote_bienestarina')" in metadata
assert "request.args.get('cantidad_bienestarina')" in metadata
assert "strftime('%d/%m/%Y')" in metadata

updater_start = backend.index("def _alpha75_actualizar_archivo_bienestarina")
updater_end = backend.index("def _alpha74_generar_bienestarina_garantizada", updater_start)
updater = backend[updater_start:updater_end]
assert "_alpha75_aplicar_datos_entrega_bienestarina(ws, metadata)" in updater

delivery_start = backend.index("def _alpha75_aplicar_datos_entrega_bienestarina")
delivery_end = updater_start
delivery = backend[delivery_start:delivery_end]
for contract in ("ws[f'H{row}'] = fecha", "ws[f'I{row}'] = lote", "ws[f'J{row}'] = cantidad"):
    assert contract in delivery

print("Bienestarina descarga con fecha/lote/cantidad/periodo: PASS")
