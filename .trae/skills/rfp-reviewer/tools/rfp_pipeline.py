#!/usr/bin/env python3
"""Convenience P0 pipeline for local RFP review artifacts."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent


def run(cmd):
    print('+', ' '.join(map(str, cmd)))
    subprocess.run([sys.executable, *map(str, cmd)], check=True)


def main():
    ap = argparse.ArgumentParser(description='Run P0 RFP review pipeline')
    ap.add_argument('input', help='RFP package file or directory')
    ap.add_argument('--kb', help='Optional company evidence directory')
    ap.add_argument('--out', required=True, help='Working/output directory')
    args = ap.parse_args()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    run([TOOLS/'file_unpacker.py', args.input, '--out', out])
    manifest = out/'manifest.json'
    classified = out/'classified_manifest.json'
    run([TOOLS/'file_classifier.py', manifest, '--out', classified])
    file_gaps = out/'file_gaps.json'
    gap_cmd = [TOOLS/'file_gap_analyzer.py', classified, '--out', file_gaps]
    if args.kb:
        gap_cmd.extend(['--kb', args.kb])
    run(gap_cmd)
    data = json.loads(classified.read_text(encoding='utf-8'))
    elem_files = []
    parsed_dir = out/'parsed'
    parsed_dir.mkdir(exist_ok=True)
    for f in data.get('files', []):
        if f.get('status') != 'ready':
            continue
        path = Path(f['path'])
        target = parsed_dir / f'{f["file_id"]}.elements.jsonl'
        ext = path.suffix.lower()
        if ext == '.pdf':
            run([TOOLS/'pdf_parser.py', path, '--out', target])
        elif ext == '.docx':
            run([TOOLS/'docx_parser.py', path, '--out', target])
        elif ext == '.xlsx':
            run([TOOLS/'excel_parser.py', path, '--out', target])
        elif ext in {'.txt', '.md', '.csv'}:
            run([TOOLS/'text_parser.py', path, '--out', target])
        else:
            continue
        elem_files.append(target)
    merged = out/'all.elements.jsonl'
    with merged.open('w', encoding='utf-8') as w:
        for ef in elem_files:
            w.write(ef.read_text(encoding='utf-8'))
    reqs = out/'requirements.jsonl'
    run([TOOLS/'requirement_extractor.py', merged, '--out', reqs])
    evidence = out/'evidence.jsonl'
    if args.kb:
        run([TOOLS/'evidence_retriever.py', reqs, '--kb', args.kb, '--out', evidence])
    else:
        evidence.write_text('', encoding='utf-8')
    judgements = out/'judgements.jsonl'
    cmd = [TOOLS/'compliance_checker.py', reqs, '--out', judgements]
    if args.kb:
        cmd.extend(['--evidence', evidence])
    run(cmd)
    run([TOOLS/'report_writer.py', '--requirements', reqs, '--judgements', judgements, '--file-gaps', file_gaps, '--out', out/'risk_report.md'])
    print(out/'risk_report.md')

if __name__ == '__main__':
    main()
