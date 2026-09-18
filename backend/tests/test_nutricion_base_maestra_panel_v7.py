from pathlib import Path
import json

from modules.base_maestra.services import fila_nino_panel


root = Path(__file__).resolve().parents[2]
index = (root / "frontend" / "index.html").read_text(encoding="utf-8")
app_js = (root / "frontend" / "js" / "app.js").read_text(encoding="utf-8")

assert "Actualizar desde Base Maestra" in index
assert "Imprimir informe" in index
assert "nutricion-base-estado" in index
assert "2.7.6-nutricion-base-maestra-1" in index
assert "/api/base-maestra/resumen-panel" in app_js
assert "abrirFichaNutricion" in app_js
assert "imprimirFichaNutricion" in app_js

item = fila_nino_panel({
    "nombre_completo": "Pepito Pérez", "documento": "123", "tipo_documento": "RC",
    "unidad_servicio": "UCA 1", "peso": 12.4, "talla": 88.0, "perimetro_braquial": 13.1,
    "diagnostico_nutricional": "RIESGO DE DESNUTRICIÓN AGUDA", "carne_salud": "SI",
    "control_crecimiento": "SI", "carne_crecimiento": "SI", "vacunas": "SI",
    "datos_json": json.dumps({"nombre_madre": "Ana Pérez", "cedula_acudiente": "456", "control_prenatal": "SI", "eps": "Nueva EPS"}),
    "alertas_json": "[]", "estado": "ACTIVO", "sexo": "M",
})
assert item["Peso"] == 12.4 and item["Talla"] == 88.0 and item["PerimetroBraquial"] == 13.1
assert item["Madre"] == "Ana Pérez"
assert item["DocumentoAcudiente"] == "456"
assert item["ControlPrenatal"] == "SI"
assert item["AfiliacionSalud"] == "Nueva EPS"

print("NUTRICION_BASE_MAESTRA_PANEL_V7_PASS")
