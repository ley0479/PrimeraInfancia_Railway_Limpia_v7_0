"""El runner E2E solo usa GET tras autenticarse y no persiste secretos."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
import liam_authenticated_e2e as runner

app_source=(ROOT/'backend/app.py').read_text(encoding='utf-8')
assert "@app.route('/api/rpp/descargar', methods=['GET'])" in app_source
assert "@app.route('/api/descargar/<unidad>/<formato>', methods=['GET'])" in app_source
assert "@app.route('/api/bienestarina/auditoria', methods=['GET'])" in app_source
probe_names={item[0] for item in runner.PROBES};assert {'rpp','ram','ran','rran','bienestarina'}<=probe_names

class Response:
    def __init__(self,status,data=None):self.status_code=status;self._data=data or {};self.headers={'X-Trace-ID':'trace-test'}
    def json(self):return self._data
class Session:
    last=None
    def __init__(self):self.headers={};self.calls=[];Session.last=self
    def post(self,url,**kwargs):self.calls.append(('POST',url,kwargs));return Response(200,{'token':'opaque-secret','usuario':{'rol':'SUPERADMIN','fundacion_id':7}})
    def get(self,url,**kwargs):
        self.calls.append(('GET',url,kwargs));probe=next((item for item in runner.PROBES if url.endswith(item[1])),None);return Response(probe[2][0] if probe else 200,{'data':[]})

original=runner.requests.Session;runner.requests.Session=Session
try:
    report=runner.run('https://example.test','tester','private-password',1);calls=Session.last.calls
    assert calls[0][0]=='POST' and calls[0][1].endswith('/api/auth/login')
    assert all(method=='GET' for method,_,_ in calls[1:]) and len(calls[1:])==len(runner.PROBES)
    serialized=str(report);assert 'private-password' not in serialized and 'opaque-secret' not in serialized
    assert report['read_only'] is True and report['credentials_stored'] is False and report['summary']['failed']==0
    for invalid in ('http://example.test','ftp://example.test','https://user:pass@example.test'):
        try:runner.validate_base_url(invalid)
        except ValueError:pass
        else:raise AssertionError('Se aceptó una URL insegura.')
    assert runner.validate_base_url('http://127.0.0.1:5000')=='http://127.0.0.1:5000'
finally:runner.requests.Session=original
print('LIAM_AUTHENTICATED_E2E_RUNNER_V7_PASS')
