"""Contratos desacoplados para canales futuros de notificación de LIAM."""
from __future__ import annotations
from abc import ABC,abstractmethod
from dataclasses import dataclass,asdict

@dataclass(frozen=True)
class ProviderStatus:
    channel:str;configured:bool;enabled:bool;send_supported:bool;approval_required:bool=True

class NotificationProvider(ABC):
    channel='unknown'
    @abstractmethod
    def status(self)->ProviderStatus:raise NotImplementedError
    def send(self,*,recipients:list[dict],subject:str,message:str,approval:dict|None=None)->dict:
        raise PermissionError(f'El canal {self.channel} no tiene un ejecutor de envío habilitado.')

class EmailProvider(NotificationProvider):
    channel='email'
    def status(self)->ProviderStatus:return ProviderStatus(self.channel,False,False,False)

class WhatsAppProvider(NotificationProvider):
    channel='whatsapp'
    def status(self)->ProviderStatus:return ProviderStatus(self.channel,False,False,False)

_PROVIDERS:dict[str,NotificationProvider]={'email':EmailProvider(),'whatsapp':WhatsAppProvider()}

def provider_catalog()->list[dict]:return [asdict(_PROVIDERS[key].status()) for key in sorted(_PROVIDERS)]

def get_provider(channel:str)->NotificationProvider:
    provider=_PROVIDERS.get(str(channel or '').strip().lower())
    if not provider:raise LookupError('El canal de notificación no está registrado.')
    return provider
