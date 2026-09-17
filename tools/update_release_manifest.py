#!/usr/bin/env python3
"""Regenera MANIFEST_SHA256.txt con las mismas reglas del validador."""
from __future__ import annotations

import hashlib
import io
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'MANIFEST_SHA256.txt'


def staged_entries()->list[tuple[str, str]]:
    """Lee rutas y blobs del índice; los cambios deben agregarse antes de ejecutar."""
    result = subprocess.run(
        ["git", "-c", "safe.directory=*", "ls-files", "--stage", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    entries = []
    for record in result.stdout.split(b"\0"):
        if not record:
            continue
        metadata, raw_path = record.split(b"\t", 1)
        _mode, blob, stage = metadata.decode("ascii").split()
        relative = raw_path.decode("utf-8")
        if stage == "0" and relative != "MANIFEST_SHA256.txt":
            entries.append((relative, blob))
    return sorted(entries)


def blob_hashes(entries: list[tuple[str, str]]) -> dict[str, str]:
    process = subprocess.Popen(
        ["git", "-c", "safe.directory=*", "cat-file", "--batch"],
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    request = "".join(f"{blob}\n" for _, blob in entries).encode("ascii")
    output, _ = process.communicate(input=request)
    if process.returncode != 0:
        raise RuntimeError("git cat-file falló")
    stream = io.BytesIO(output)
    hashes = {}
    for relative, expected_blob in entries:
        blob, kind, size = stream.readline().decode("ascii").split()
        if blob != expected_blob or kind != "blob":
            raise RuntimeError(f"Objeto Git inesperado para {relative}")
        content = stream.read(int(size))
        stream.read(1)
        if relative.lower().endswith(".bat"):
            content = content.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        hashes[relative] = hashlib.sha256(content).hexdigest()
    return hashes


def main()->None:
    entries = staged_entries()
    hashes = blob_hashes(entries)
    content=''.join(f"{hashes[relative]}  {relative}\n" for relative, _ in entries)
    MANIFEST.write_text(content,encoding='utf-8',newline='\n')
    print(f"MANIFEST_FILES={len(entries)}")


if __name__=='__main__':main()
