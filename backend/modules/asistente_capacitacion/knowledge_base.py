"""Fuente única del Manual Maestro y conocimiento contextual de LIAM."""
from __future__ import annotations

from functools import lru_cache
from io import BytesIO
import json
from pathlib import Path
import textwrap


KNOWLEDGE_ROOT = Path(__file__).resolve().parents[3] / "knowledge" / "liam"


def _read_json(relative_path: str) -> dict:
    with (KNOWLEDGE_ROOT / relative_path).open("r", encoding="utf-8") as stream:
        return json.load(stream)


@lru_cache(maxsize=1)
def load_knowledge() -> dict:
    index = _read_json("index.json")
    result = {"metadata": {key: value for key, value in index.items() if key != "sources"}}
    for source in index["sources"]:
        document = _read_json(source)
        kind = document.get("kind", "identity")
        result[kind] = document.get("items", document)
    return result


def manual_for_role(role: str, *, module_id: str = "", screen_id: str = "", help_id: str = "") -> dict:
    """Entrega exclusivamente conocimiento compatible con el rol autenticado."""
    data = load_knowledge()
    normalized_role = str(role or "").upper()
    modules = [item for item in data.get("modules", []) if normalized_role in item.get("roles", [])]
    workflows = [item for item in data.get("workflows", []) if normalized_role in item.get("roles", [])]
    if module_id:
        modules = [item for item in modules if item.get("module_id") == module_id]
        workflows = [item for item in workflows if item.get("module_id") == module_id]
    controls = [control | {"module_id": module["module_id"], "screen_id": module["screen_id"]}
                for module in modules for control in module.get("controls", [])]
    active_control = next((item for item in controls if item.get("help_id") == help_id), None) if help_id else None
    # Durante la cobertura piloto, un módulo con una única acción documentada puede
    # contextualizar a LIAM aun antes de que el usuario enfoque el control.
    if active_control is None and module_id and len(controls) == 1:
        active_control = controls[0]
    if screen_id:
        modules = [item for item in modules if item.get("screen_id") == screen_id or
                   any(control.get("help_id") == help_id for control in item.get("controls", []))]
    role_guide = next((item for item in data.get("roles", []) if item.get("role_id") == normalized_role), None)
    error_codes = {code for module in modules for code in module.get("common_errors", [])}
    if active_control:
        error_codes.update(active_control.get("common_errors", []))
    errors = [item for item in data.get("errors", []) if not error_codes or item.get("code") in error_codes]
    return {
        "metadata": data["metadata"], "identity": data.get("identity", {}), "role": normalized_role,
        "role_guide": role_guide, "modules": modules, "workflows": workflows, "controls": controls,
        "active_control": active_control, "errors": errors, "read_only": True,
    }


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_manual_pdf(manual: dict) -> bytes:
    """Genera un PDF simple y portable, sin depender de binarios externos."""
    lines = [manual["identity"].get("title", "Manual de usuario"),
             f"Rol: {manual.get('role') or 'usuario'} · Versión: {manual['metadata'].get('guide_version', '')}", ""]
    if manual.get("role_guide"):
        lines.extend([manual["role_guide"]["title"], "Enfoque: " + ", ".join(manual["role_guide"].get("focus", [])), ""])
    for module in manual.get("modules", []):
        lines.extend([module["title"], module["objective"], "Ubicación: " + module["location"],
                      "Requisitos: " + "; ".join(module.get("prerequisites", [])),
                      "Proceso: " + " → ".join(module.get("process", [])),
                      "Resultado: " + module.get("result", ""), "Siguiente: " + module.get("next_step", ""), ""])
        for control in module.get("controls", []):
            lines.extend(["  Botón: " + control["title"], "  ID: " + control["help_id"],
                          "  " + control["purpose"], "  Siguiente: " + control.get("next_step", ""), ""])
    for workflow in manual.get("workflows", []):
        lines.append("Guía rápida: " + workflow["title"])
        lines.extend([f"  {number}. {step}" for number, step in enumerate(workflow.get("steps", []), 1)])
        lines.extend(["Resultado: " + workflow.get("result", ""), ""])
    wrapped = []
    for line in lines:
        wrapped.extend(textwrap.wrap(line, width=92, replace_whitespace=True) or [""])
    pages = [wrapped[index:index + 48] for index in range(0, len(wrapped), 48)] or [["Manual sin contenido"]]
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b""]
    page_ids, content_ids = [], []
    next_id = 4
    for _ in pages:
        page_ids.append(next_id); content_ids.append(next_id + 1); next_id += 2
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(f'{item} 0 R' for item in page_ids)}] /Count {len(pages)} >>".encode()
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    for page_number, page in enumerate(pages, 1):
        commands = ["BT /F1 10 Tf 48 790 Td 14 TL"]
        for line in page:
            safe = _pdf_escape(line.encode("cp1252", "replace").decode("cp1252"))
            commands.append(f"({safe}) Tj T*")
        commands.extend([f"ET BT /F1 8 Tf 520 28 Td (Página {page_number}) Tj ET"])
        stream = "\n".join(commands).encode("cp1252")
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_ids[page_number-1]} 0 R >>".encode())
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")
    output = BytesIO(); output.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"); offsets = [0]
    for object_id, obj in enumerate(objects, 1):
        offsets.append(output.tell()); output.write(f"{object_id} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = output.tell(); output.write(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]: output.write(f"{offset:010d} 00000 n \n".encode())
    output.write(f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return output.getvalue()
