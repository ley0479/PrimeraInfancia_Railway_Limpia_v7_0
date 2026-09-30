"""Registro cerrado de adaptadores multiprograma revisados en código."""

ADAPTERS = {
    "SERVICIO_INTEGRADO_EXTRAMURAL_V1": {
        "input": "UNIVERSAL_TABULAR",
        "generators": ("RFPP", "F2"),
        "grouping": "COMUNIDAD",
    },
    "SYNTHETIC_TEST_V1": {
        "input": "SYNTHETIC_ONLY",
        "generators": (),
        "grouping": "SYNTHETIC_GROUP",
    },
}


def adapter_definition(code: str) -> dict:
    key = str(code or "").strip().upper()
    if key not in ADAPTERS:
        raise ValueError("El adaptador solicitado no está registrado en código.")
    return {"codigo": key, **ADAPTERS[key]}
