"""Frontera de proveedor. La integración externa permanece desactivada."""
from __future__ import annotations
from abc import ABC, abstractmethod

class AssistantProvider(ABC):
    @abstractmethod
    def respond(self, *, messages: list[dict], context: dict, tools: list[dict]) -> dict: ...

class ProviderUnavailable(RuntimeError): pass

def provider_status() -> dict:
    # No se declara listo hasta validar SDK, API oficial, credencial de servidor,
    # modelo configurado, timeouts, salida estructurada y function calling.
    return {'configured':False,'ready':False,'reason':'Proveedor externo pendiente de configuración y validación oficial.'}
