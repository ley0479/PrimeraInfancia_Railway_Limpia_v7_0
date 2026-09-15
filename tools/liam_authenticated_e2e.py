#!/usr/bin/env python3
"""Regresión E2E autenticada y estrictamente de solo lectura para LIAM."""
from __future__ import annotations

from datetime import datetime, timezone
import argparse,json,os,re,sys,time
from pathlib import Path
from urllib.parse import urljoin,urlparse
import requests

PROBES=(
 ('auth','/api/auth/me',(200,)),('base_maestra','/api/base-maestra/resumen',(200,)),('unidades','/api/unidades',(200,)),
 ('calendario','/api/calendario-inteligente/dashboard',(200,)),('entregables','/api/calendario-inteligente/entregables',(200,)),
 ('salud_nutricion','/api/salud-nutricion/dashboard',(200,)),('motor_plantillas','/api/motor-plantillas/dashboard',(200,)),
 ('ram','/api/motor-plantillas/ram-v3/estado',(200,)),('documentos','/api/documentos/estado',(200,)),
 ('facturacion','/api/facturacion/mi-suscripcion',(200,404)),('usuarios','/api/usuarios',(200,)),('fundaciones','/api/fundaciones',(200,)),
 ('formatos','/api/formatos/diagnostico',(200,)),('liam_config','/api/asistente-capacitacion/config',(200,)),
 ('liam_tools','/api/asistente-capacitacion/tools',(200,)),('liam_health','/api/asistente-capacitacion/health',(200,)),
 ('backups','/api/backups/estado',(200,403)),('bienestarina','/api/bienestarina/auditoria',(200,400,404)),
)


def validate_base_url(value):
    value=str(value or '').strip().rstrip('/');parsed=urlparse(value)
    if parsed.scheme not in {'https','http'} or not parsed.netloc or parsed.username or parsed.password:raise ValueError('LIAM_E2E_BASE_URL no es una URL HTTP(S) segura.')
    if parsed.scheme!='https' and parsed.hostname not in {'127.0.0.1','localhost'}:raise ValueError('El E2E remoto exige HTTPS.')
    return value


def evidence(response,name,path,allowed,elapsed):
    try:data=response.json()
    except Exception:data={}
    keys=sorted(str(key)[:80] for key in data.keys()) if isinstance(data,dict) else []
    return {'module':name,'path':path,'status':response.status_code,'allowed_statuses':list(allowed),'passed':response.status_code in allowed,'duration_ms':elapsed,'trace_id':str(response.headers.get('X-Trace-ID') or response.headers.get('X-Request-ID') or '')[:100] or None,'response_keys':keys}


def run(base_url,username,password,timeout=20):
    session=requests.Session();session.headers.update({'User-Agent':'LIAM-Authenticated-E2E/1.0','Accept':'application/json'})
    login=session.post(urljoin(base_url+'/', 'api/auth/login'),json={'username':username,'password':password},timeout=timeout,allow_redirects=False)
    if login.status_code!=200:raise RuntimeError(f'Login E2E rechazado con HTTP {login.status_code}.')
    body=login.json();token=str(body.get('token') or '')
    if not token:raise RuntimeError('El login no devolvió una sesión opaca.')
    session.headers['Authorization']='Bearer '+token
    results=[]
    for name,path,allowed in PROBES:
        started=time.monotonic();response=session.get(base_url+path,timeout=timeout,allow_redirects=False);elapsed=int((time.monotonic()-started)*1000);results.append(evidence(response,name,path,allowed,elapsed))
    user=body.get('usuario') if isinstance(body.get('usuario'),dict) else {}
    return {'schema':'liam-authenticated-e2e-v1','generated_at':datetime.now(timezone.utc).isoformat(),'target_host':urlparse(base_url).hostname,'authenticated_role':str(user.get('rol') or '')[:40],'foundation_id':user.get('fundacion_id'),'read_only':True,'credentials_stored':False,'probes':results,'summary':{'total':len(results),'passed':sum(x['passed'] for x in results),'failed':sum(not x['passed'] for x in results)}}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);parser.add_argument('--timeout',type=int,default=20);args=parser.parse_args()
    base=validate_base_url(os.environ.get('LIAM_E2E_BASE_URL'));username=os.environ.get('LIAM_E2E_USERNAME','');password=os.environ.get('LIAM_E2E_PASSWORD','')
    if not username or not password:raise ValueError('Faltan LIAM_E2E_USERNAME y LIAM_E2E_PASSWORD de una cuenta de prueba autorizada.')
    report=run(base,username,password,max(5,min(args.timeout,60)));output=Path(args.output).resolve();output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(report['summary']));return 0 if report['summary']['failed']==0 else 1


if __name__=='__main__':sys.exit(main())
