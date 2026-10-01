"""Extrae catálogos oficiales desde la hoja Listados de F23.MO12.PP v2."""
from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "seed_data" / "caracterizacion_f23" / "F23_MO12_PP_v2.xlsm"
TARGET = ROOT / "seed_data" / "caracterizacion_f23" / "catalogos_ui_v2.json"


def clean(value) -> str:
    return " ".join(str(value or "").strip().split())


def column_name(number: int) -> str:
    result = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result
    return result


def read_listados() -> dict[str, str]:
    main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rel_doc = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    package = "http://schemas.openxmlformats.org/package/2006/relationships"
    with zipfile.ZipFile(SOURCE) as archive:
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(node.text or "" for node in item.iter(f"{{{main}}}t")) for item in root.findall(f"{{{main}}}si")]
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {item.attrib["Id"]: item.attrib["Target"] for item in relationships.findall(f"{{{package}}}Relationship")}
        sheet_path = ""
        for sheet in workbook.findall(f".//{{{main}}}sheet"):
            if sheet.attrib.get("name") == "Listados":
                sheet_path = "xl/" + targets[sheet.attrib[f"{{{rel_doc}}}id"]].lstrip("/")
                break
        root = ET.fromstring(archive.read(sheet_path))
    values = {}
    for cell in root.findall(f".//{{{main}}}c"):
        coordinate = cell.attrib.get("r", "")
        value = cell.find(f"{{{main}}}v")
        inline = cell.find(f"{{{main}}}is")
        if cell.find(f"{{{main}}}f") is not None:
            continue
        if inline is not None:
            text = "".join(node.text or "" for node in inline.iter(f"{{{main}}}t"))
        elif value is None:
            text = ""
        elif cell.attrib.get("t") == "s":
            text = shared[int(value.text or 0)]
        else:
            text = value.text or ""
        if text:
            values[coordinate] = text
    return values


def column_values(cells: dict[str, str], column: int, start: int, end: int) -> list[str]:
    values = []
    for row in range(start, end + 1):
        value = clean(cells.get(f"{column_name(column)}{row}"))
        if value and not value.startswith("="):
            values.append(value)
    return values


def main() -> None:
    cells = read_listados()
    regional_centros = {}
    for column in range(2, 35):
        regional = clean(cells.get(f"{column_name(column)}2"))
        if regional:
            regional_centros[regional] = column_values(cells, column, 3, 35)
    departamento_municipios = {}
    for column in range(2, 35):
        raw = clean(cells.get(f"{column_name(column)}37"))
        department = raw.split(" ", 1)[1] if " " in raw else raw
        if department:
            departamento_municipios[department] = column_values(cells, column, 38, 163)
    languages = []
    for column in (19, 20):
        for value in column_values(cells, column, 165, 296):
            label = value.split(". ", 1)[1] if ". " in value else value
            if label and label not in languages:
                languages.append(label)
    option_columns = {
        "grupo_etnico": (6, 165, 171),
        "duerme": (7, 165, 171),
        "no_afiliado": (10, 165, 170),
        "esquema_incompleto": (13, 165, 171),
        "sin_salud_bucal": (16, 165, 170),
        "razones_no_cita": (18, 165, 169),
        "no_recibe_leche": (23, 165, 172),
        "edad_otros_alimentos": (26, 165, 170),
        "no_leche_exclusiva": (29, 165, 172),
        "tiempo_complementaria": (30, 165, 177),
    }
    options = {key: column_values(cells, column, start, end) for key, (column, start, end) in option_columns.items()}
    payload = {
        "source": "F23.MO12.PP v2 / hoja Listados",
        "regional_centros": regional_centros,
        "departamento_municipios": departamento_municipios,
        "lenguas": languages,
        "opciones": options,
    }
    TARGET.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS {TARGET}: {len(regional_centros)} regionales, {sum(map(len, regional_centros.values()))} centros, {len(departamento_municipios)} departamentos, {sum(map(len, departamento_municipios.values()))} municipios, {len(languages)} lenguas, {len(options)} listas de respuesta")


if __name__ == "__main__":
    main()
