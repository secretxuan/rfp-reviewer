#!/usr/bin/env python3
"""Produce conservative compliance judgements from requirements and evidence."""
from __future__ import annotations

import argparse
from pathlib import Path
from common import jsonl_read, jsonl_write


def risk_for(req, has_ev: bool):
    lvl = req.get('mandatory_level')
    cat = req.get('category')
    if has_ev:
        if lvl in {'fatal', 'high'}:
            return 'P2 中风险'
        return 'P3 低风险'
    if lvl == 'fatal' or cat == 'invalid_bid':
        return 'P0 致命风险'
    if lvl == 'high' or cat in {'qualification', 'form', 'price'}:
        return 'P1 高风险'
    if lvl == 'medium':
        return 'P2 中风险'
    return 'INFO 提示'


def main():
    ap = argparse.ArgumentParser(description='Check compliance from requirement/evidence JSONL')
    ap.add_argument('requirements')
    ap.add_argument('--evidence')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    reqs = jsonl_read(Path(args.requirements))
    ev_by_id = {}
    if args.evidence:
        for e in jsonl_read(Path(args.evidence)):
            ev_by_id[e['requirement_id']] = e
    rows = []
    for r in reqs:
        ev = ev_by_id.get(r['requirement_id'], {'evidence': []})
        evidence_items = ev.get('evidence') or []
        has_ev = bool(evidence_items)
        risk = risk_for(r, has_ev)
        if has_ev:
            judgement = '需人工复核' if r.get('mandatory_level') in {'fatal', 'high'} else '存疑'
            reason = '已找到可能相关的证明材料，但仍需人工确认语义覆盖范围、材料有效性和应标表述是否充分。'
            confidence = max([x.get('confidence', 0.4) for x in evidence_items])
        else:
            judgement = '未发现证明材料'
            reason = '当前材料中未检索到直接证明，不能在缺少补充证据的情况下判定为满足。'
            confidence = 0.55 if risk in {'P0 致命风险', 'P1 高风险'} else 0.45
        rows.append({
            'requirement_id': r['requirement_id'],
            'judgement': judgement,
            'risk_level': risk,
            'confidence': round(confidence, 2),
            'human_review_required': risk in {'P0 致命风险', 'P1 高风险'} or judgement in {'需人工复核', '存疑'},
            'reason': reason,
            'suggested_action': '补充直接证明材料或修改应标响应；高风险项需法务/商务/投标负责人确认。' if not has_ev else '复核证据覆盖范围，并将证据绑定到响应内容或偏离表中。',
            'evidence_refs': [x.get('file', '') for x in evidence_items[:3]],
        })
    jsonl_write(rows, Path(args.out))
    print(args.out)

if __name__ == '__main__':
    main()
