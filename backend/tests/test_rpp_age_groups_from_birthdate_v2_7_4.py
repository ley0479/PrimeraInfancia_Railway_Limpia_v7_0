"""Regresión: los RPP de 1–2 y 3–5 usan fecha de nacimiento canónica."""
from __future__ import annotations

import ast
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP_PATH = ROOT / "backend" / "app.py"


def _load_functions(*names: str):
    source = APP_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    namespace = {
        "parse_fecha_cuentame": lambda value: datetime.fromisoformat(str(value)[:10]),
        "calcular_edad_meses": lambda value: (2026 - value.year) * 12 + (8 - value.month),
        "inferir_edad_meses_desde_valor": lambda value: None,
        "normalizar_texto_clave": lambda value: str(value or "").lower().replace("ñ", "n"),
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(APP_PATH), "exec"), namespace)
    return namespace


def main() -> None:
    ns = _load_functions("_alpha59_edad_meses", "_alpha59_filtrar_rpp_grupo")
    edad = ns["_alpha59_edad_meses"]
    filtrar = ns["_alpha59_filtrar_rpp_grupo"]

    # Reproduce el defecto productivo: edad_meses contenía años, pero la fecha
    # correcta permite recuperar 24 y 48 meses respectivamente.
    uno_dos = {"EdadMeses": 2, "FechaNacimiento": "2024-08-01"}
    tres_cinco = {"EdadMeses": 4, "FechaNacimiento": "2022-08-01"}
    assert edad(uno_dos) == 24
    assert edad(tres_cinco) == 48
    assert filtrar([uno_dos], "rpp_1_2") == [uno_dos]
    assert filtrar([tres_cinco], "rpp_3_5") == [tres_cinco]

    # También admite etiquetas institucionales normalizadas sin la preposición.
    assert filtrar([{"GrupoEdad": "1 2 ANOS 11 MESES"}], "rpp_1_2")
    assert filtrar([{"GrupoEdad": "3 5 ANOS 11 MESES"}], "rpp_3_5")
    print("RPP rangos 1-2 y 3-5 desde fecha de nacimiento: PASS")


if __name__ == "__main__":
    main()
