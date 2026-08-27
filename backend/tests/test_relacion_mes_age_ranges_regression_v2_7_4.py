"""Regresión de los cinco rangos de la Relación del mes."""
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from services.relacion_mes_service import clasificar_participante, consolidar_por_unidad, cantidades  # noqa: E402


def main() -> None:
    rows = [
        {"unidad_servicio": "UDS PRUEBA", "estado": "ACTIVO", "tipo_beneficiario": "GESTANTE"},
        {"unidad_servicio": "UDS PRUEBA", "estado": "ACTIVO", "fecha_nacimiento": "2026-05-01", "edad_meses": 0},
        {"unidad_servicio": "UDS PRUEBA", "estado": "ACTIVO", "fecha_nacimiento": "2025-12-01", "edad_meses": 7},
        # Reproduce los datos defectuosos: el campo dice 2/4, pero son años.
        {"unidad_servicio": "UDS PRUEBA", "estado": "ACTIVO", "fecha_nacimiento": "2024-08-01", "edad_meses": 2},
        {"unidad_servicio": "UDS PRUEBA", "estado": "ACTIVO", "fecha_nacimiento": "2022-08-01", "edad_meses": 4},
    ]
    assert clasificar_participante(rows[3], 2026, 8) == "uno_2"
    assert clasificar_participante(rows[4], 2026, 8) == "tres_5"

    result = consolidar_por_unidad(rows, 2026, 8)["UDS PRUEBA"]
    assert [result[key] for key in ("gestantes", "menores_6", "seis_11", "uno_2", "tres_5")] == [1, 1, 1, 1, 1]
    assert result["sin_clasificar"] == 0

    qty = cantidades(result)
    assert qty["total"] == 5
    assert qty["huevos_15"] == 15
    assert qty["huevos_30"] == 120
    print("Relación del mes: cinco rangos y fórmulas preservados: PASS")


if __name__ == "__main__":
    main()
