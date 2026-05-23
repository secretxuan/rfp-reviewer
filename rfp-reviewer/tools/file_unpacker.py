#!/usr/bin/env python3
"""Recursively unpack ZIP files and create a source manifest."""
from __future__ import annotations

import argparse
import shutil
import zipfile
from pathlib import Path
from common import SUPPORTED_EXTS, file_id, guess_mime, json_dump, sha256_file


def unpack_zip(src: Path, dst: Path, notes: list[str]) -> None:
    try:
        with zipfile.ZipFile(src) as zf:
            encrypted = [i.filename for i in zf.infolist() if i.flag_bits & 0x1]
            if encrypted:
                notes.append(f'encrypted entries skipped: {encrypted[:5]}')
                return
            zf.extractall(dst)
    except zipfile.BadZipFile:
        notes.append('bad zip file or unsupported archive')


def main() -> None:
    ap = argparse.ArgumentParser(description='Unpack ZIP archives and create manifest')
    ap.add_argument('input')
    ap.add_argument('--out', required=True, help='Output directory')
    args = ap.parse_args()
    src = Path(args.input).resolve()
    out = Path(args.out).resolve()
    raw = out / 'raw'
    raw.mkdir(parents=True, exist_ok=True)
    notes: list[str] = []

    if not src.exists():
        json_dump({
            'input': str(src),
            'work_dir': str(out),
            'notes': [f'input path does not exist: {src}'],
            'files': [],
            'missing_input': True,
        }, out / 'manifest.json')
        print(out / 'manifest.json')
        return

    if src.is_dir():
        target = raw / src.name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(src, target)
    elif src.suffix.lower() == '.zip':
        unpack_zip(src, raw / src.stem, notes)
    else:
        shutil.copy2(src, raw / src.name)

    # One-level recursive ZIP expansion for nested packages.
    for z in list(raw.rglob('*.zip')):
        nested_out = z.with_suffix('')
        nested_notes: list[str] = []
        unpack_zip(z, nested_out, nested_notes)
        notes.extend([f'{z.name}: {n}' for n in nested_notes])

    manifest = []
    idx = 1
    for p in sorted(raw.rglob('*')):
        if not p.is_file():
            continue
        ext = p.suffix.lower()
        status = 'ready' if ext in SUPPORTED_EXTS else 'unsupported'
        item_notes = [] if status == 'ready' else [f'unsupported extension: {ext or "<none>"}']
        manifest.append({
            'file_id': file_id(idx),
            'path': str(p),
            'name': p.name,
            'extension': ext,
            'mime_guess': guess_mime(p),
            'size_bytes': p.stat().st_size,
            'sha256': sha256_file(p),
            'role': 'unknown',
            'status': status,
            'notes': item_notes,
        })
        idx += 1
    json_dump({'input': str(src), 'work_dir': str(out), 'notes': notes, 'files': manifest, 'missing_input': False}, out / 'manifest.json')
    print(out / 'manifest.json')


if __name__ == '__main__':
    main()
