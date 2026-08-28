#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""claim_binder.py — 主张绑定节点（N9 管线第⑧步）。

为每条通过审计与溯源校验的 bullet 生成/更新一条 claim 记录，
写入 `原始事实/claims/`。

用法:
    python3 claim_binder.py --bullets bullets.json [--claims claims_input.json] [--kb 路径]

--claims 可选：包含 boundary / interview_details 等用户确认信息的 JSON。
未提供时，脚本使用占位符并在输出中标记「待用户补充」。
"""
import argparse
import json
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common


def _section_id(fact):
    """根据 fact 生成 section_id，如 公司名-起始年月。"""
    org = fact.get("company") or fact.get("name") or ""
    period = fact.get("period", "")
    m = re.search(r"(\d{4})[./年-]?(\d{1,2})?", period)
    start = "%s%s" % (m.group(1), m.group(2) or "01") if m else ""
    return "%s-%s" % (org, start) if org and start else org or fact.get("fact_id", "")


def _find_bullet_index(fact, source_fact):
    if not source_fact or not fact:
        return -1
    src = str(source_fact).strip()
    for idx, b in enumerate(fact.get("bullets", [])):
        if src in b or b in src:
            return idx
    return -1


def _default_interview_details():
    return {
        "decision": "（待用户补充：为什么这样做）",
        "challenge": "（待用户补充：难点是什么）",
        "verification": "（待用户补充：结果怎么验证）",
        "result": "（待用户补充：对业务的影响）",
    }


def bind_claims(bullets, facts, claim_inputs=None):
    """根据 bullets 和 facts 生成 claim 列表（不写入文件）。"""
    claim_inputs = claim_inputs or {}
    claims = []
    for idx, b in enumerate(bullets, 1):
        fact = None
        for f in facts["facts"]:
            if f["fact_id"] == b.get("fact_id"):
                fact = f
                break
        section = "work_history" if fact and fact.get("type") == "work" else "project" if fact and fact.get("type") == "project" else "advantage"
        section_id = b.get("section_id") or (fact and _section_id(fact)) or ""

        bullet_idx = _find_bullet_index(fact, b.get("source_fact")) if fact else -1
        levels = fact.get("responsibility_levels", []) if fact else []
        level = levels[bullet_idx] if fact and 0 <= bullet_idx < len(levels) else b.get("responsibility_level", "")

        cid = b.get("claim_id") or "claim-%s-%03d" % (date.today().strftime("%Y%m%d"), idx)
        inp = claim_inputs.get(cid, {})

        claim = {
            "id": cid,
            "section": section,
            "section_id": section_id,
            "source_fact": b.get("source_fact", b.get("rewritten", "")),
            "candidate_wording": b.get("rewritten", ""),
            "responsibility_level": level or "待确认",
            "verification_status": "已确认",
            "allowed_uses": inp.get("allowed_uses", b.get("allowed_uses", [])),
            "interview_details": inp.get("interview_details", _default_interview_details()),
            "boundary": inp.get("boundary", "（待用户补充：团队成果与个人贡献的分界）"),
            "risk_notes": inp.get("risk_notes", []),
            "last_verified": date.today().isoformat(),
        }
        claims.append(claim)
    return claims


def main():
    ap = argparse.ArgumentParser(description="主张绑定")
    ap.add_argument("--bullets", required=True, help="通过校验的 bullets JSON")
    ap.add_argument("--claims", default=None, help="用户补充的 claim 输入 JSON（可选）")
    ap.add_argument("--kb", default=None, help="知识库路径")
    ap.add_argument("--out", default=None, help="输出 claims.json 路径（可选，默认写入知识库）")
    args = ap.parse_args()

    root = common.kb_root(args.kb)
    facts = common.load_facts(root)

    with open(args.bullets, encoding="utf-8") as f:
        bullets = json.load(f)

    claim_inputs = {}
    if args.claims and os.path.exists(args.claims):
        with open(args.claims, encoding="utf-8") as f:
            claim_inputs = json.load(f)

    claims = bind_claims(bullets, facts, claim_inputs)

    if args.out:
        out = args.out
    else:
        out = os.path.join(root, common.CLAIMS_DIR, common.CLAIMS_AGGREGATE)

    common.write_claims(root, claims)
    print("[完成] 已生成/更新 %d 条 claim：%s" % (len(claims), out))

    pending = [c for c in claims if "待用户补充" in c["boundary"] or any("待用户补充" in v for v in c["interview_details"].values())]
    if pending:
        print("[待办] %d 条 claim 需要用户补充 boundary / interview_details" % len(pending))
        for c in pending:
            print("    - %s" % c["id"])


if __name__ == "__main__":
    main()
