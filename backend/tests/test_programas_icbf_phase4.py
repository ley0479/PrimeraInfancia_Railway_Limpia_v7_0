from __future__ import annotations

import tempfile
from pathlib import Path

from modules.programas_icbf.repository import ProgramasIcbfRepository
from modules.seguridad.services import role_allowed_for_path


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    for role in ("SUPERADMIN", "GERENTE", "COORDINADOR", "AUXILIAR_ADMINISTRATIVO", "NUTRICIONISTA"):
        require(role_allowed_for_path("/api/programas-icbf/perfiles", role), f"La barrera central bloquea el programa para {role}")
    for role in ("DOCENTE", "PSICOSOCIAL"):
        require(not role_allowed_for_path("/api/programas-icbf/perfiles", role), f"La barrera central amplió el programa a {role}")
    with tempfile.TemporaryDirectory() as temporary:
        repo = ProgramasIcbfRepository(str(Path(temporary) / "profiles.sqlite3"))
        repo.init_schema()
        primary = repo.ensure_profile(1, 11)
        synthetic = repo.register_profile(1, {"codigo": "PERFIL_SINTETICO_TERCERO", "nombre": "Perfil sintético de extensibilidad", "modalidad": "PRUEBA", "adapter_code": "SYNTHETIC_TEST_V1", "configuracion": {"solo_datos_sinteticos": True}}, 11)
        require(synthetic["estado"] == "INACTIVO" and synthetic["configuracion"]["adapter_code"] == "SYNTHETIC_TEST_V1", "El tercer perfil no inició aislado e inactivo")
        repeated = repo.register_profile(1, {"codigo": "PERFIL_SINTETICO_TERCERO", "nombre": "Perfil sintético de extensibilidad", "modalidad": "PRUEBA", "adapter_code": "SYNTHETIC_TEST_V1", "configuracion": {"solo_datos_sinteticos": True}}, 11)
        require(repeated["id"] == synthetic["id"], "Duplicó un perfil idéntico")
        pilot = repo.set_profile_state(1, synthetic["id"], "PILOTO", 11)
        require(pilot["estado"] == "PILOTO", "No habilitó el estado piloto")
        blocked = False
        try:
            repo.set_profile_state(1, synthetic["id"], "ACTIVO", 11)
        except ValueError:
            blocked = True
        require(blocked, "Permitió activar producción sin autorización independiente")
        inactive = repo.set_profile_state(1, synthetic["id"], "INACTIVO", 11)
        profiles = repo.list_profiles(1)
        require(inactive["estado"] == "INACTIVO" and any(item["id"] == synthetic["id"] for item in profiles), "No conservó el perfil al desactivarlo")
        require(any(item["id"] == primary["id"] for item in profiles), "Perdió el perfil principal")
        other = repo.register_profile(2, {"codigo": "PERFIL_SINTETICO_TERCERO", "nombre": "Perfil otra fundación", "modalidad": "PRUEBA", "adapter_code": "SYNTHETIC_TEST_V1"}, 22)
        require(all(item["id"] != other["id"] for item in repo.list_profiles(1)), "Mezcló perfiles entre fundaciones")
        blocked = False
        try:
            repo.register_profile(1, {"codigo": "NO_VALIDO", "nombre": "No válido", "modalidad": "PRUEBA", "adapter_code": "CODIGO_ARBITRARIO"}, 11)
        except ValueError:
            blocked = True
        require(blocked, "Aceptó un adaptador ejecutable no registrado")
        print("PASS test_programas_icbf_phase4")


if __name__ == "__main__":
    main()
