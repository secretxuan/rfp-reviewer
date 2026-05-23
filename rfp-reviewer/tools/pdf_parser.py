#!/usr/bin/env python3
"""Parse text from PDF files with optional pypdf/PyPDF2 fallback."""
from __future__ import annotations

from pathlib import Path
from common import default_arg_parser, element_id, jsonl_write, normalize_ws


def extract_pdf(path: Path):
    errors = []
    for mod_name in ('pypdf', 'PyPDF2'):
        try:
            mod = __import__(mod_name)
            reader = mod.PdfReader(str(path))
            rows = []
            idx = 1
            for page_num, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ''
                for para in text.split('\n'):
                    para = normalize_ws(para)
                    if para:
                        rows.append({'element_id': element_id(idx), 'file': str(path), 'file_name': path.name, 'type': 'paragraph', 'locator': f'page {page_num}', 'page': page_num, 'section': '', 'text': para, 'confidence': 0.9})
                        idx += 1
            return rows
        except Exception as e:  # optional dependency or parse failure
            errors.append(f'{mod_name}: {e}')
    return [{'element_id': element_id(1), 'file': str(path), 'file_name': path.name, 'type': 'parse_error', 'locator': 'file', 'page': None, 'section': '', 'text': 'PDF text extraction unavailable. Install pypdf or provide OCR/text export.', 'confidence': 0.0, 'errors': errors}]


def main():
    ap = default_arg_parser('Parse PDF into document elements JSONL')
    args = ap.parse_args()
    rows = extract_pdf(Path(args.input).resolve())
    jsonl_write(rows, Path(args.out))
    print(args.out)


if __name__ == '__main__':
    main()
