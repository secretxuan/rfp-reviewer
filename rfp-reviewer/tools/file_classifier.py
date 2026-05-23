#!/usr/bin/env python3
"""Heuristic file role classifier for RFP packages."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from common import json_dump

ROLE_KEYWORDS = [
    ('deviation_template', ['偏离', '响应表', 'deviation', 'matrix']),
    ('quotation', ['报价', '分项报价', '价格', 'quote', 'quotation', 'price']),
    ('qualification', ['资质', '证书', '营业执照', '授权', '社保', '纳税', 'qualification', 'certificate']),
    ('product', ['白皮书', '产品', '技术参数', '规格', 'whitepaper', 'spec']),
    ('bid_response', ['投标文件', '应标', '响应文件', 'bid response', 'proposal']),
    ('rfp', ['招标文件', '采购文件', '招标公告', 'rfp', 'tender', 'procurement']),
    ('contract', ['合同', 'contract']),
    ('case', ['案例', '业绩', 'case', 'reference']),
]


def guess_role(name: str) -> str:
    low = name.lower()
    for role, keys in ROLE_KEYWORDS:
        if any(k.lower() in low for k in keys):
            return role
    return 'other'


def main() -> None:
    ap = argparse.ArgumentParser(description='Classify manifest file roles')
    ap.add_argument('manifest')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    data = json.loads(Path(args.manifest).read_text(encoding='utf-8'))
    for f in data.get('files', []):
        if f.get('status') == 'ready':
            f['role'] = guess_role(f.get('name', ''))
    json_dump(data, Path(args.out))
    print(args.out)


if __name__ == '__main__':
    main()
