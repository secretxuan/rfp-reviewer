#!/usr/bin/env python3
"""Write Markdown RFP review report from requirements and judgements."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from common import jsonl_read


def esc(s):
    return str(s or '').replace('|', '\\|').replace('\n', '<br>')


def main():
    ap = argparse.ArgumentParser(description='Generate RFP review report markdown')
    ap.add_argument('--requirements', required=True)
    ap.add_argument('--judgements', required=True)
    ap.add_argument('--file-gaps')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    reqs = {r['requirement_id']: r for r in jsonl_read(Path(args.requirements))}
    judgements = jsonl_read(Path(args.judgements))
    gaps = {}
    if args.file_gaps and Path(args.file_gaps).exists():
        gaps = json.loads(Path(args.file_gaps).read_text(encoding='utf-8'))
    high = [j for j in judgements if j.get('risk_level') in {'P0 致命风险', 'P1 高风险'}]
    lines = []
    lines.append('# RFP 合规预审报告')
    lines.append('')
    lines.append('## 审查范围')
    lines.append(f'- 条款数量：{len(reqs)}')
    lines.append(f'- 判定数量：{len(judgements)}')
    if gaps:
        summary = gaps.get('summary', {})
        lines.append(f'- 文件数量：{summary.get("total_files", 0)}，可处理：{summary.get("ready_files", 0)}，不支持：{summary.get("unsupported_files", 0)}，加密：{summary.get("encrypted_files", 0)}，企业资料库文件：{summary.get("kb_files", 0)}')
        candidates = gaps.get('main_rfp_candidates', [])
        if candidates:
            lines.append('- 疑似主招标文件：' + '、'.join(c.get('name', '') for c in candidates[:5]))
        else:
            lines.append('- 疑似主招标文件：未识别')
    lines.append('- 说明：本报告为 Agent 预审结果，不能替代法务或投标负责人的最终确认。')
    lines.append('')
    if gaps:
        lines.append('## 文件缺失与限制')
        missing = gaps.get('missing_materials', [])
        if missing:
            for m in missing:
                lines.append(f'- {m.get("severity")}: 缺少{m.get("label")}；影响：{"、".join(m.get("blocking_for", []))}；建议：{m.get("ask")}')
        else:
            lines.append('- 未识别到关键材料缺失。')
        unsupported = gaps.get('unsupported_files', [])
        if unsupported:
            lines.append('')
            lines.append('### 不支持文件')
            for f in unsupported[:20]:
                lines.append(f'- {f.get("name")} ({f.get("extension")}): {"; ".join(f.get("notes", []))}')
        questions = gaps.get('questions_for_user', [])
        if questions:
            lines.append('')
            lines.append('### 建议追问用户')
            for q in questions[:20]:
                lines.append(f'- {q}')
        lines.append('')
    lines.append('## 高危风险')
    if not high:
        lines.append('- 暂未识别到 P0/P1 风险；仍需人工复核强制项、签章、报价和资质材料。')
    else:
        for j in high:
            r = reqs.get(j['requirement_id'], {})
            src = r.get('source', {})
            lines.append(f'- 风险：{esc(j.get("risk_level"))} / {esc(j.get("judgement"))}')
            lines.append(f'  来源：{esc(src.get("file"))} {esc(src.get("locator"))}')
            lines.append(f'  条款：{esc(r.get("text"))[:260]}')
            lines.append(f'  原因：{esc(j.get("reason"))}')
            lines.append(f'  建议：{esc(j.get("suggested_action"))}')
    lines.append('')
    lines.append('## 合规偏离表')
    lines.append('| 条款 | 来源 | 招标要求 | 判定 | 风险 | 建议 |')
    lines.append('| --- | --- | --- | --- | --- | --- |')
    for j in judgements:
        r = reqs.get(j['requirement_id'], {})
        src = r.get('source', {})
        lines.append(f'| {esc(j["requirement_id"])} | {esc(src.get("file"))} {esc(src.get("locator"))} | {esc(r.get("text"))[:180]} | {esc(j.get("judgement"))} | {esc(j.get("risk_level"))} | {esc(j.get("suggested_action"))} |')
    lines.append('')
    lines.append('## 补料清单')
    missing = [j for j in judgements if j.get('judgement') == '未发现证明材料']
    if not missing:
        lines.append('- 暂未生成缺失证明清单；请人工确认所有证据是否可披露、有效且覆盖本项目。')
    else:
        for j in missing[:50]:
            r = reqs.get(j['requirement_id'], {})
            lines.append(f'- {j["requirement_id"]}: 需补充 {", ".join(r.get("required_evidence") or ["直接证明材料"])}')
    lines.append('')
    lines.append('## 待人工确认')
    for j in judgements:
        if j.get('human_review_required'):
            lines.append(f'- {j["requirement_id"]}: {j.get("risk_level")}，{j.get("reason")}')
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(args.out)

if __name__ == '__main__':
    main()
