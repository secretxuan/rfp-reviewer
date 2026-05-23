#!/usr/bin/env python3
"""Simple local evidence retriever over text-like files and parsed documents."""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from common import TEXT_EXTS, iter_files, jsonl_read, jsonl_write, normalize_ws, safe_read_text

TOKEN_RE = re.compile(r'[A-Za-z0-9_\-\.]+|[\u4e00-\u9fff]{2,}')
STOP = {'必须', '应当', '不得', '要求', '提供', '具有', '进行', '符合', 'the', 'and', 'shall', 'must'}


def tokens(text: str) -> list[str]:
    out = []
    for t in TOKEN_RE.findall(text):
        if t.lower() not in STOP and len(t) >= 2:
            low = t.lower()
            out.append(low)
            # Chinese tender terms often appear as long unsegmented runs.
            # Add short n-grams so "双活容灾能力" can match "双活部署" and "容灾切换".
            if re.fullmatch(r'[\u4e00-\u9fff]{4,}', t):
                for n in (2, 3, 4):
                    out.extend(t[i:i+n].lower() for i in range(0, max(0, len(t) - n + 1)))
    seen = []
    for t in out:
        if t not in STOP and t not in seen:
            seen.append(t)
    return seen[:60]


def load_corpus(kb: Path):
    docs = []
    for p in iter_files(kb):
        ext = p.suffix.lower()
        if ext in TEXT_EXTS:
            docs.append((str(p), safe_read_text(p)))
        elif ext == '.jsonl':
            try:
                for row in jsonl_read(p):
                    docs.append((f'{p}:{row.get("locator", "")}', row.get('text', '')))
            except Exception:
                pass
    return docs


def snippet(text: str, term: str) -> str:
    low = text.lower()
    pos = low.find(term.lower())
    if pos < 0:
        return normalize_ws(text[:300])
    return normalize_ws(text[max(0, pos-120): pos+220])


def main():
    ap = argparse.ArgumentParser(description='Retrieve local evidence for requirements')
    ap.add_argument('requirements')
    ap.add_argument('--kb', required=True, help='Company evidence directory')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    reqs = jsonl_read(Path(args.requirements))
    corpus = load_corpus(Path(args.kb))
    rows = []
    for r in reqs:
        toks = tokens(r.get('text', ''))
        hits = []
        for file, body in corpus:
            body_low = body.lower()
            score_terms = [t for t in toks if t in body_low]
            if score_terms:
                hits.append((len(score_terms), file, snippet(body, score_terms[0]), score_terms))
        hits.sort(reverse=True, key=lambda x: x[0])
        ev = []
        for score, file, quote, _terms in hits[:5]:
            ev.append({'source_type': 'local_file', 'file': file, 'locator': '', 'quote': quote, 'evidence_type': 'keyword_match', 'confidence': min(0.9, 0.35 + score / max(8, len(toks)))})
        rows.append({'requirement_id': r['requirement_id'], 'status': 'found' if ev else 'not_found', 'evidence': ev, 'limitations': [] if ev else ['No keyword evidence found in provided KB.']})
    jsonl_write(rows, Path(args.out))
    print(args.out)

if __name__ == '__main__':
    main()
