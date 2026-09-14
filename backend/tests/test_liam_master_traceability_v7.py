from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[2]
text=(ROOT/'docs'/'liam'/'MASTER_REQUIREMENTS_TRACEABILITY_2026-09-14.md').read_text(encoding='utf-8')
numbers=[int(value) for value in re.findall(r'^\|\s*(\d+)\s*\|',text,re.MULTILINE)]
assert numbers==list(range(1,73)),numbers
assert 'PARCIAL' in text and 'DIFERIDO SEGURO' in text
assert 'depende del cierre de 20, 21, 43 y 64' in text
print('LIAM_MASTER_TRACEABILITY_V7_PASS')
