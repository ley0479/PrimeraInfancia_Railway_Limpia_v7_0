"""Validaciones puras del runner Docker externo de LIAM."""
from pathlib import Path
import hashlib,json,sys,tempfile
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
from liam_dev_sandbox_runner import load_plan,patch_paths,safe_path

with tempfile.TemporaryDirectory() as tmp:
    content={'request_id':'DEV-20260914-ABC12345','architecture':{'files':['backend/app.py']},'tests':['backend/tests/test_app.py'],'generated_test_path':'backend/tests/generated/test_dev_20260914_abc12345.py'}
    canonical=json.dumps(content,ensure_ascii=False,sort_keys=True,separators=(',',':'));artifact={**content,'sha256':hashlib.sha256(canonical.encode()).hexdigest(),'artifact_id':'ART-1','type':'SANDBOX_PLAN','status':'READY'};path=Path(tmp)/'plan.json';path.write_text(json.dumps({'artifact':artifact}),encoding='utf-8');loaded,digest=load_plan(path);assert loaded==content and digest==artifact['sha256']
    diff='diff --git a/backend/app.py b/backend/app.py\n--- a/backend/app.py\n+++ b/backend/app.py\n';assert patch_paths(diff)==['backend/app.py'];assert safe_path('backend/tests/test_app.py')=='backend/tests/test_app.py'
    for invalid in ('../.env','C:/secret','.git/config','.env'):
        try:safe_path(invalid)
        except ValueError:pass
        else:raise AssertionError('El runner aceptó una ruta prohibida.')
    artifact['sha256']='0'*64;path.write_text(json.dumps(artifact),encoding='utf-8')
    try:load_plan(path)
    except ValueError:pass
    else:raise AssertionError('El runner aceptó un plan alterado.')
print('LIAM_EXTERNAL_SANDBOX_RUNNER_V7_PASS')
