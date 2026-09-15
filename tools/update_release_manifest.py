#!/usr/bin/env python3
"""Regenera MANIFEST_SHA256.txt con las mismas reglas del validador."""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'MANIFEST_SHA256.txt'


def included(path:Path)->bool:
    relative=path.relative_to(ROOT)
    return path.is_file() and '.git' not in relative.parts and path!=MANIFEST


def sha256(path:Path)->str:
    digest=hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()


def main()->None:
    files=sorted((path for path in ROOT.rglob('*') if included(path)),key=lambda path:path.relative_to(ROOT).as_posix())
    content=''.join(f"{sha256(path)}  {path.relative_to(ROOT).as_posix()}\n" for path in files)
    MANIFEST.write_text(content,encoding='utf-8',newline='\n')
    print(f'MANIFEST_FILES={len(files)}')


if __name__=='__main__':main()
