#!/usr/bin/env python3
"""Parse DOCX paragraphs and tables using stdlib zip/xml."""
from __future__ import annotations

import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from common import default_arg_parser, element_id, jsonl_write, normalize_ws

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}


def texts(el):
    return ''.join(t.text or '' for t in el.findall('.//w:t', NS))


def parse_docx(path: Path):
    rows = []
    try:
        with zipfile.ZipFile(path) as zf:
            xml = zf.read('word/document.xml')
        root = ET.fromstring(xml)
        idx = 1
        for child in root.findall('.//w:body/*', NS):
            tag = child.tag.rsplit('}', 1)[-1]
            if tag == 'p':
                txt = normalize_ws(texts(child))
                if txt:
                    rows.append({'element_id': element_id(idx), 'file': str(path), 'file_name': path.name, 'type': 'paragraph', 'locator': f'paragraph {idx}', 'page': None, 'section': '', 'text': txt, 'confidence': 0.95})
                    idx += 1
            elif tag == 'tbl':
                table_rows = []
                for tr in child.findall('.//w:tr', NS):
                    cells = [normalize_ws(texts(tc)) for tc in tr.findall('./w:tc', NS)]
                    if any(cells):
                        table_rows.append(' | '.join(cells))
                if table_rows:
                    rows.append({'element_id': element_id(idx), 'file': str(path), 'file_name': path.name, 'type': 'table', 'locator': f'table {idx}', 'page': None, 'section': '', 'text': '\n'.join(table_rows), 'confidence': 0.9})
                    idx += 1
    except Exception as e:
        rows.append({'element_id': element_id(1), 'file': str(path), 'file_name': path.name, 'type': 'parse_error', 'locator': 'file', 'page': None, 'section': '', 'text': f'DOCX parse failed: {e}', 'confidence': 0.0})
    return rows


def main():
    ap = default_arg_parser('Parse DOCX into document elements JSONL')
    args = ap.parse_args()
    jsonl_write(parse_docx(Path(args.input).resolve()), Path(args.out))
    print(args.out)


if __name__ == '__main__':
    main()
