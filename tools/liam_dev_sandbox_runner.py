#!/usr/bin/env python3
"""Runner externo de LIAM: worktree efímero + Docker sin red, nunca despliega."""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile
import time

MAX_PATCH_BYTES=120*1024


def fail(message):raise ValueError(message)


def safe_path(value):
    text=str(value or '').strip().replace('\\','/');path=PurePosixPath(text)
    if not text or path.is_absolute() or re.match(r'^[A-Za-z]:/',text) or '..' in path.parts or text.startswith(('.git/','.env')):fail('Ruta prohibida en el parche.')
    return str(path)


def patch_paths(text):
    found=[]
    for line in text.splitlines():
        if not line.startswith(('+++ ','--- ')):continue
        value=line[4:].split('\t',1)[0].strip()
        if value=='/dev/null':continue
        if value.startswith(('a/','b/')):value=value[2:]
        value=safe_path(value)
        if value not in found:found.append(value)
    if not found:fail('El parche no contiene rutas verificables.')
    return found


def load_plan(path):
    raw=json.loads(Path(path).read_text(encoding='utf-8'))
    artifact=raw.get('artifact') if isinstance(raw.get('artifact'),dict) else raw
    expected=str(artifact.get('sha256') or '')
    content={key:value for key,value in artifact.items() if key not in {'artifact_id','type','status','sha256'}}
    canonical=json.dumps(content,ensure_ascii=False,sort_keys=True,separators=(',',':'))
    if not re.fullmatch(r'[a-f0-9]{64}',expected) or hashlib.sha256(canonical.encode()).hexdigest()!=expected:fail('El plan no coincide con su checksum SHA-256.')
    return content,expected


def run(command,cwd,*,check=True):
    return subprocess.run(command,cwd=str(cwd),capture_output=True,text=True,check=check,timeout=900)


def execute(repo,plan_path,patch_path,image):
    repo=Path(repo).resolve();patch_file=Path(patch_path).resolve();content,plan_sha=load_plan(plan_path)
    patch=patch_file.read_text(encoding='utf-8')
    if len(patch.encode())>MAX_PATCH_BYTES:fail('El parche supera 120 KiB.')
    allowed=set(content.get('architecture',{}).get('files') or []);generated=safe_path(content.get('generated_test_path'));allowed.add(generated)
    changed=patch_paths(patch);outside=sorted(set(changed)-allowed)
    if outside:fail('Rutas fuera del plan: '+', '.join(outside))
    if generated not in changed:fail('El parche debe incluir la prueba generada definida en el plan.')
    tests=[safe_path(x) for x in [*(content.get('tests') or []),generated]]
    base_commit=run(['git','rev-parse','HEAD'],repo).stdout.strip().lower()
    with tempfile.TemporaryDirectory(prefix='liam-dev-sandbox-') as temp:
        workspace=Path(temp)/'workspace';run(['git','worktree','add','--detach',str(workspace),base_commit],repo)
        try:
            run(['git','apply','--check',str(patch_file)],workspace);run(['git','apply',str(patch_file)],workspace)
            results=[]
            for test in tests:
                mount=f'{workspace}:/workspace:rw'
                command=['docker','run','--rm','--network','none','--read-only','--tmpfs','/tmp:rw,noexec,nosuid,size=256m','--memory','1g','--cpus','2','--pids-limit','256','--security-opt','no-new-privileges','-v',mount,'-w','/workspace',image,'python',test]
                started=time.monotonic();completed=run(command,repo,check=False);duration=max(0,int((time.monotonic()-started)*1000));results.append({'test':test,'status':'PASS' if completed.returncode==0 else 'FAIL','duration_ms':duration})
            diff_check=run(['git','diff','--check'],workspace,check=False)
            diff=run(['git','diff','--binary'],workspace).stdout
            final_outside=sorted(set(patch_paths(diff))-allowed)
            if final_outside:fail('La ejecución alteró rutas fuera del plan: '+', '.join(final_outside))
        finally:
            run(['git','worktree','remove','--force',str(workspace)],repo,check=False)
    return {'plan_sha256':plan_sha,'base_commit':base_commit,'diff':diff,'git_diff_check':'PASS' if diff_check.returncode==0 else 'FAIL','tests':results,'runner':'liam-docker-isolated-v1'}


def main():
    parser=argparse.ArgumentParser(description='Ejecuta un plan LIAM en Docker aislado y emite evidencia firmada.')
    parser.add_argument('--repo',required=True);parser.add_argument('--plan',required=True);parser.add_argument('--patch',required=True);parser.add_argument('--output',required=True);parser.add_argument('--image',required=True,help='Imagen local previamente construida; el runner usa --network none.')
    args=parser.parse_args();key=os.environ.get('LIAM_DEV_SANDBOX_SIGNING_KEY','')
    if len(key)<24:fail('LIAM_DEV_SANDBOX_SIGNING_KEY debe existir y tener al menos 24 caracteres.')
    payload=execute(args.repo,args.plan,args.patch,args.image);raw=json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode();output=Path(args.output).resolve();output.write_bytes(raw);output.with_suffix(output.suffix+'.sig').write_text('sha256='+hmac.new(key.encode(),raw,hashlib.sha256).hexdigest(),encoding='ascii')
    print(json.dumps({'output':str(output),'signature':str(output.with_suffix(output.suffix+'.sig')),'status':'PASS' if all(x['status']=='PASS' for x in payload['tests']) and payload['git_diff_check']=='PASS' else 'FAIL','deployment_started':False}))


if __name__=='__main__':main()
