import os
from unittest.mock import patch

from modules.salud_nutricion.routes import health_themes_enabled


with patch.dict(os.environ,{},clear=False):
    os.environ.pop('ENABLE_HEALTH_THEMES',None)
    assert health_themes_enabled() is True
with patch.dict(os.environ,{'ENABLE_HEALTH_THEMES':'false'}):
    assert health_themes_enabled() is False
with patch.dict(os.environ,{'ENABLE_HEALTH_THEMES':'true'}):
    assert health_themes_enabled() is True
print('SALUD_TEMATICAS_FEATURE_FLAG_V1_PASS')
