#!/usr/bin/env python3
"""Shared helpers for rfp-reviewer P0 tools."""
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List

TEXT_EXTS = {'.txt', '.md', '.csv', '.json', '.jsonl'}
SUPPORTED_EXTS = {'.zip', '.pdf', '.docx', '.xlsx', '.png', '.jpg', '.jpeg', '.txt', '.md', '.csv'}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def json_dump(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def jsonl_write(rows: Iterable[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')


def jsonl_read(path: Path) -> List[Dict[str, Any]]:
    rows = []
    if not path.exists():
        return rows
    with path.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def guess_mime(path: Path) -> str:
    return mimetypes.guess_type(str(path))[0] or 'application/octet-stream'


def file_id(index: int) -> str:
    return f'FILE-{index:04d}'


def element_id(index: int) -> str:
    return f'E-{index:06d}'


def normalize_ws(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


def safe_read_text(path: Path) -> str:
    for enc in ('utf-8', 'utf-8-sig', 'gb18030', 'latin-1'):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_bytes().decode('utf-8', errors='ignore')


def iter_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
    else:
        for p in path.rglob('*'):
            if p.is_file() and not any(part.startswith('.') for part in p.parts):
                yield p


def default_arg_parser(description: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=description)
    p.add_argument('input', help='Input file or directory')
    p.add_argument('--out', required=True, help='Output file path')
    return p
