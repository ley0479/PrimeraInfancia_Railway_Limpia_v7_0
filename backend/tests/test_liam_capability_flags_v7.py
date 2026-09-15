"""Banderas granulares y compuerta ADMIN/DEV apagada por defecto."""
from pathlib import Path
import os,sys
BACKEND=Path(__file__).resolve().parents[1];ROOT=BACKEND.parent;sys.path.insert(0,str(BACKEND))
from modules.asistente_capacitacion.config import public_liam_flags

names=('ENABLE_LIAM_ASSISTANT','LIAM_VISUAL_PANEL_ENABLED','LIAM_SEARCH_ENABLED','LIAM_ACTIONS_ENABLED','LIAM_ADMIN_ENABLED','LIAM_DEV_ENABLED','LIAM_REPAIR_ENABLED')
saved={name:os.environ.get(name) for name in names}
try:
    os.environ['ENABLE_LIAM_ASSISTANT']='true'
    for name in names[1:]:os.environ.pop(name,None)
    flags=public_liam_flags()
    assert flags['visual_panel_enabled'] is True and flags['search_enabled'] is True
    assert flags['actions_enabled'] is True and flags['admin_enabled'] is True
    assert flags['dev_enabled'] is False and flags['repair_enabled'] is False
    os.environ['LIAM_DEV_ENABLED']='true';os.environ['LIAM_REPAIR_ENABLED']='true'
    flags=public_liam_flags();assert flags['dev_enabled'] is True and flags['repair_enabled'] is True
finally:
    for name,value in saved.items():
        if value is None:os.environ.pop(name,None)
        else:os.environ[name]=value

routes=(BACKEND/'modules'/'asistente_capacitacion'/'routes.py').read_text(encoding='utf-8')
env=(ROOT/'.env.example').read_text(encoding='utf-8')
assert "'dev_enabled':{'prepare_dev_change_request','list_dev_change_requests','get_dev_change_review','prepare_dev_sandbox_plan'}" in routes
assert 'require_tool_feature(tool_name)' in routes
for name in ('LIAM_VISUAL_PANEL_ENABLED','LIAM_SEARCH_ENABLED','LIAM_ACTIONS_ENABLED','LIAM_ADMIN_ENABLED','LIAM_DEV_ENABLED','LIAM_REPAIR_ENABLED'):assert name in env
print('LIAM_CAPABILITY_FLAGS_V7_PASS')
