"""Contrato de identidad, comportamiento y seguridad del prompt central de Lía."""
from modules.asistente_capacitacion.system_prompt import LIA_SYSTEM_PROMPT, SYSTEM_PROMPT_VERSION, realtime_instructions

def test_system_prompt_covers_institutional_behavior():
    prompt = LIA_SYSTEM_PROMPT.casefold()
    assert SYSTEM_PROMPT_VERSION == "lia-institucional-v1"
    for expected in ("eres lía", "claridad absoluta", "dominio verificable de la interfaz", "diagnóstico resolutivo", "fundación", "sesión activa", "manual maestro", "herramientas autorizadas", "no generes sql libre", "confirmación"):
        assert expected in prompt

def test_realtime_uses_same_prompt_and_session_context():
    prompt = realtime_instructions(action_policy="publicar=alto/expresa", authorized_context='{"rol":"ADMIN"}')
    assert LIA_SYSTEM_PROMPT in prompt
    assert "publicar=alto/expresa" in prompt
    assert '"rol":"ADMIN"' in prompt
    assert "multitarea" in prompt

if __name__ == "__main__":
    test_system_prompt_covers_institutional_behavior()
    test_realtime_uses_same_prompt_and_session_context()
    print("LIA_SYSTEM_PROMPT_V7_PASS")
