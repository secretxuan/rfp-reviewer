#!/usr/bin/env python3
"""Analyze missing, unsupported, and ambiguous files for RFP review."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from common import iter_files, json_dump

REQUIRED_FOR_FULL_REVIEW = {
    'rfp': {
        'label': '主招标/RFP/采购文件',
        'blocking_for': ['条款抽取', '完整合规审查', '偏离表生成'],
        'ask': '请提供主招标文件或确认哪一份文件是主招标文件。',
    },
    'qualification': {
        'label': '企业资质/证书/授权/纳税社保财务证明',
        'blocking_for': ['资格符合性判断', '废标风险证明', '偏离表满足性判断'],
        'ask': '如需判断我方是否满足资格要求，请补充企业资质材料目录。',
    },
    'product': {
        'label': '产品白皮书/技术参数/方案材料',
        'blocking_for': ['技术符合性判断', '技术应标草稿'],
        'ask': '如需判断技术条款是否满足，请补充产品白皮书、技术参数表或方案材料。',
    },
    'quotation': {
        'label': '报价表/分项报价/保证金凭证',
        'blocking_for': ['最高限价检查', '报价风险检查', '保证金检查'],
        'ask': '如需检查报价、最高限价或保证金，请补充报价表或保证金凭证。',
    },
    'deviation_template': {
        'label': '招标方偏离表模板',
        'blocking_for': ['按模板填报偏离表'],
        'ask': '如需按招标方格式生成偏离表，请补充 Excel/Word 偏离表模板。',
    },
    'bid_response': {
        'label': '我方投标/应标文件草稿',
        'blocking_for': ['已写响应内容审查', '签章/授权/格式检查'],
        'ask': '如需审查已写投标文件，请补充我方投标/应标文件草稿。',
    },
}


def severity_for_missing(role: str) -> str:
    if role == 'rfp':
        return 'P0'
    if role in {'qualification', 'product', 'quotation'}:
        return 'P1'
    return 'P2'


def guess_kb_role(name: str) -> str:
    low = name.lower()
    role_keywords = [
        ('qualification', ['资质', '证书', '营业执照', '授权', '社保', '纳税', '财务', 'qualification', 'certificate']),
        ('product', ['白皮书', '产品', '技术参数', '规格', 'whitepaper', 'spec', '方案']),
        ('quotation', ['报价', '分项报价', '价格', 'quote', 'quotation', 'price', '保证金']),
        ('deviation_template', ['偏离', '响应表', 'deviation', 'matrix']),
        ('bid_response', ['投标文件', '应标', '响应文件', 'bid response', 'proposal']),
        ('case', ['案例', '业绩', 'case', 'reference']),
    ]
    for role, keys in role_keywords:
        if any(k.lower() in low for k in keys):
            return role
    return 'other'


def main() -> None:
    ap = argparse.ArgumentParser(description='Analyze missing/unsupported files in classified manifest')
    ap.add_argument('manifest')
    ap.add_argument('--kb', help='Optional company evidence directory')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    data = json.loads(Path(args.manifest).read_text(encoding='utf-8'))
    files = data.get('files', [])
    by_role: dict[str, list[dict]] = defaultdict(list)
    unsupported = []
    encrypted = []
    errors = []

    for f in files:
        status = f.get('status')
        role = f.get('role') or 'unknown'
        if status == 'ready':
            by_role[role].append(f)
        elif status == 'unsupported':
            unsupported.append(f)
        elif status == 'encrypted':
            encrypted.append(f)
        elif status == 'error':
            errors.append(f)

    kb_files = []
    if args.kb:
        kb_path = Path(args.kb).resolve()
        if kb_path.exists():
            for p in iter_files(kb_path):
                role = guess_kb_role(p.name)
                kb_item = {
                    'name': p.name,
                    'path': str(p),
                    'role': role,
                    'status': 'ready',
                    'source': 'kb',
                }
                kb_files.append(kb_item)
                by_role[role].append(kb_item)

    missing = []
    for role, meta in REQUIRED_FOR_FULL_REVIEW.items():
        if role not in by_role:
            missing.append({
                'role': role,
                'label': meta['label'],
                'severity': severity_for_missing(role),
                'blocking_for': meta['blocking_for'],
                'ask': meta['ask'],
                'is_blocking_for_full_review': role in {'rfp', 'qualification', 'product'},
            })

    role_counts = Counter(f.get('role', 'unknown') for f in files)
    main_rfp_candidates = by_role.get('rfp', [])
    questions = []
    if not main_rfp_candidates:
        questions.append(REQUIRED_FOR_FULL_REVIEW['rfp']['ask'])
    elif len(main_rfp_candidates) > 1:
        names = ', '.join(f.get('name', '') for f in main_rfp_candidates[:5])
        questions.append(f'检测到多个疑似主招标文件（{names}），请确认以哪一份为准。')
    for m in missing:
        if m['role'] != 'rfp':
            questions.append(m['ask'])
    if unsupported:
        questions.append('存在不支持格式文件，请确认是否可提供 PDF/DOCX/XLSX/TXT 替代版本。')

    result = {
        'summary': {
            'total_files': len(files),
            'ready_files': sum(1 for f in files if f.get('status') == 'ready'),
            'unsupported_files': len(unsupported),
            'encrypted_files': len(encrypted),
            'error_files': len(errors),
            'role_counts': dict(role_counts),
            'kb_files': len(kb_files),
        },
        'main_rfp_candidates': [
            {'name': f.get('name'), 'path': f.get('path'), 'status': f.get('status')} for f in main_rfp_candidates
        ],
        'missing_materials': missing,
        'unsupported_files': [
            {'name': f.get('name'), 'path': f.get('path'), 'extension': f.get('extension'), 'notes': f.get('notes', [])}
            for f in unsupported
        ],
        'encrypted_files': [
            {'name': f.get('name'), 'path': f.get('path'), 'notes': f.get('notes', [])}
            for f in encrypted
        ],
        'error_files': [
            {'name': f.get('name'), 'path': f.get('path'), 'notes': f.get('notes', [])}
            for f in errors
        ],
        'questions_for_user': questions,
        'review_limitations': [
            '缺少企业私有证明材料时，只能抽取招标要求和公共规则风险，不能判断我方满足。',
            '不支持或加密文件未参与解析，相关章节可能遗漏。',
            '文件角色由启发式规则识别，关键文件需要用户最终确认。',
        ],
    }
    json_dump(result, Path(args.out))
    print(args.out)


if __name__ == '__main__':
    main()
