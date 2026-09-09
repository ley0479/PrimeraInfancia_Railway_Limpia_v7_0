"""Frontera opcional del modelo; la clave nunca sale del servidor."""
from __future__ import annotations
from abc import ABC, abstractmethod
import json, os
import requests

class AssistantProvider(ABC):
    @abstractmethod
    def respond(self,*,messages:list[dict],context:dict,tools:list[dict])->dict: ...

class ProviderUnavailable(RuntimeError): pass

def provider_status()->dict:
    configured=bool(os.getenv('OPENAI_API_KEY','').strip() and os.getenv('LIAM_OPENAI_MODEL','').strip())
    enabled=os.getenv('LIAM_AI_ENABLED','').strip().lower() in {'1','true','yes','on','si','sí'}
    return {'configured':configured,'ready':configured and enabled,'reason':None if configured and enabled else 'Configure OPENAI_API_KEY, LIAM_OPENAI_MODEL y LIAM_AI_ENABLED en el servidor.'}

class OpenAIResponsesProvider(AssistantProvider):
    endpoint='https://api.openai.com/v1/responses'
    def __init__(self):
        status=provider_status()
        if not status['ready']: raise ProviderUnavailable(status['reason'])
        self.key=os.environ['OPENAI_API_KEY'].strip();self.model=os.environ['LIAM_OPENAI_MODEL'].strip()
    def respond(self,*,messages:list[dict],context:dict,tools:list[dict])->dict:
        instructions=("Eres LIAM, asistente virtual femenina de la plataforma Primera Infancia. "
          "Responde en español colombiano, con calidez y pasos concretos. Usa exclusivamente el contexto autorizado. "
          "No inventes funciones, normas o datos. No solicites datos personales. No ejecutes acciones. "
          "El borrador verificado tiene prioridad. Si su confianza es insufficient, puedes reorganizar el manual para orientar, "
          "pero debes declarar lo que no esté confirmado y pedir el nombre del botón o código del error.")
        payload={'model':self.model,'instructions':instructions,'input':[
          {'role':'developer','content':'CONTEXTO AUTORIZADO:\n'+json.dumps(context,ensure_ascii=False,default=str)},
          *messages[-6:],
        ],'max_output_tokens':500,'store':False}
        try:
            response=requests.post(self.endpoint,json=payload,headers={'Authorization':f'Bearer {self.key}','Content-Type':'application/json'},timeout=(5,25))
            response.raise_for_status();data=response.json()
        except (requests.RequestException,ValueError) as exc: raise ProviderUnavailable(type(exc).__name__) from exc
        text=data.get('output_text')
        if not text:
            text=''.join(part.get('text','') for item in data.get('output',[]) for part in item.get('content',[]) if part.get('type')=='output_text')
        if not text.strip(): raise ProviderUnavailable('El proveedor no devolvió texto.')
        return {'message':text.strip()[:6000],'provider':'openai_responses','model':self.model,'response_id':data.get('id')}
