#!/usr/bin/env python3
"""Heuristic requirement extractor from document elements."""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from common import jsonl_read, jsonl_write, normalize_ws

CATEGORY_RULES = [
    ('invalid_bid', ['无效', '废标', '否决', '不予受理', '实质性响应', 'invalid', 'reject']),
    ('qualification', ['资格', '资质', '营业执照', '认证', '证书', '纳税', '社保', '财务', '信用']),
    ('form', ['签字', '签章', '盖章', '授权', '密封', '正本', '副本', '加密', '电子签章']),
    ('price', ['报价', '预算', '最高限价', '控制价', '价格', '税率', '保证金']),
    ('business', ['交付', '付款', '质保', '售后', '培训', '驻场', '服务期', '履约', '验收']),
    ('technical', ['技术', '功能', '性能', '接口', '协议', '安全', '兼容', '架构', '系统', '响应时间']),
    ('contract', ['合同', '违约', '保密', '知识产权', '赔偿', '数据安全']),
    ('scoring', ['评分', '分值', '评审', '得分', '综合评估']),
    ('deadline', ['截止', '开标', '报名', '答疑', '有效期', '日历天']),
]
MANDATORY_FATAL = ['★', '☆', '▲', '无效', '废标', '否决', '不予受理', '必须', '不得', '不接受', '实质性']
MANDATORY_HIGH = ['须', '应当', '需', '要求', 'shall', 'must', 'required']
REQUIREMENT_HINTS = MANDATORY_FATAL + MANDATORY_HIGH + ['资格', '评分', '保证金', '最高限价', '签章', '报价', '技术指标']


def category(text: str) -> str:
    low = text.lower()
    for cat, keys in CATEGORY_RULES:
        if any(k.lower() in low for k in keys):
            return cat
    return 'other'


def mandatory_level(text: str, cat: str) -> str:
    if any(k in text for k in MANDATORY_FATAL):
        return 'fatal'
    if cat in {'invalid_bid', 'qualification', 'form', 'price'} and any(k in text for k in MANDATORY_HIGH):
        return 'high'
    if any(k in text for k in MANDATORY_HIGH):
        return 'medium'
    return 'info'


def required_evidence(cat: str) -> list[str]:
    return {
        'qualification': ['资质证书', '营业执照', '认证/许可', '纳税/社保/财务证明'],
        'form': ['签字盖章页', '授权委托书', '电子签章/密封证明'],
        'technical': ['产品白皮书', '技术方案', '参数表', '架构图'],
        'business': ['商务响应', '服务承诺', '交付/质保说明'],
        'price': ['报价表', '保证金凭证', '分项报价'],
        'contract': ['合同审查意见', '法务确认'],
    }.get(cat, [])


def main():
    ap = argparse.ArgumentParser(description='Extract RFP requirements from elements JSONL')
    ap.add_argument('elements')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    rows = []
    rid = 1
    for e in jsonl_read(Path(args.elements)):
        text = normalize_ws(e.get('text', ''))
        if not text or e.get('type') == 'parse_error':
            continue
        if len(text) < 8:
            continue
        # Keep likely requirement lines and table rows; skip purely decorative text.
        if not any(h.lower() in text.lower() for h in REQUIREMENT_HINTS) and not re.search(r'[一二三四五六七八九十0-9]+[、.．)]', text):
            continue
        cat = category(text)
        lvl = mandatory_level(text, cat)
        rows.append({
            'requirement_id': f'REQ-{rid:04d}',
            'category': cat,
            'mandatory_level': lvl,
            'source': {'file': e.get('file_name') or e.get('file', ''), 'locator': e.get('locator', ''), 'section': e.get('section', '')},
            'text': text[:2000],
            'required_evidence': required_evidence(cat),
            'keywords': [k for k in REQUIREMENT_HINTS if k.lower() in text.lower()][:10],
            'confidence': 0.65 if cat == 'other' else 0.78,
        })
        rid += 1
    jsonl_write(rows, Path(args.out))
    print(args.out)

if __name__ == '__main__':
    main()
