#!/usr/bin/env python3
"""Parse plain text-like files into document elements."""
from pathlib import Path
from common import default_arg_parser, element_id, jsonl_write, normalize_ws, safe_read_text


def main():
    ap = default_arg_parser('Parse text into document elements JSONL')
    args = ap.parse_args()
    path = Path(args.input).resolve()
    rows = []
    idx = 1
    for line_no, line in enumerate(safe_read_text(path).splitlines(), start=1):
        txt = normalize_ws(line)
        if txt:
            rows.append({'element_id': element_id(idx), 'file': str(path), 'file_name': path.name, 'type': 'paragraph', 'locator': f'line {line_no}', 'page': None, 'section': '', 'text': txt, 'confidence': 0.95})
            idx += 1
    jsonl_write(rows, Path(args.out))
    print(args.out)

if __name__ == '__main__':
    main()
