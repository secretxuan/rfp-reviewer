#!/usr/bin/env python3
"""Parse XLSX sheets using stdlib zip/xml."""
from __future__ import annotations

import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from common import default_arg_parser, element_id, jsonl_write, normalize_ws

MAIN_NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
NS = {'m': MAIN_NS, 'r': REL_NS}


def shared_strings(zf):
    try:
        root = ET.fromstring(zf.read('xl/sharedStrings.xml'))
    except KeyError:
        return []
    vals = []
    for si in root.findall('.//m:si', NS):
        vals.append(''.join(t.text or '' for t in si.findall('.//m:t', NS)))
    return vals


def cell_value(c, strings):
    v = c.find('m:v', NS)
    if v is None:
        return ''
    text = v.text or ''
    if c.attrib.get('t') == 's':
        try:
            return strings[int(text)]
        except Exception:
            return text
    return text


def parse_xlsx(path: Path):
    rows = []
    try:
        with zipfile.ZipFile(path) as zf:
            strings = shared_strings(zf)
            sheet_files = sorted([n for n in zf.namelist() if re.match(r'xl/worksheets/sheet\d+\.xml$', n)])
            idx = 1
            for sheet_idx, sheet_file in enumerate(sheet_files, start=1):
                root = ET.fromstring(zf.read(sheet_file))
                for r in root.findall('.//m:row', NS):
                    cells = [normalize_ws(cell_value(c, strings)) for c in r.findall('m:c', NS)]
                    if any(cells):
                        locator = f'sheet {sheet_idx} row {r.attrib.get("r", "?")}'
                        rows.append({'element_id': element_id(idx), 'file': str(path), 'file_name': path.name, 'type': 'row', 'locator': locator, 'page': None, 'section': f'sheet {sheet_idx}', 'text': ' | '.join(cells), 'confidence': 0.9})
                        idx += 1
    except Exception as e:
        rows.append({'element_id': element_id(1), 'file': str(path), 'file_name': path.name, 'type': 'parse_error', 'locator': 'file', 'page': None, 'section': '', 'text': f'XLSX parse failed: {e}', 'confidence': 0.0})
    return rows


def main():
    ap = default_arg_parser('Parse XLSX into document elements JSONL')
    args = ap.parse_args()
    jsonl_write(parse_xlsx(Path(args.input).resolve()), Path(args.out))
    print(args.out)


if __name__ == '__main__':
    main()
