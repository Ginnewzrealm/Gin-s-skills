#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tacit_miner.py — 执行 STAR 隐性知识挖掘对话。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mining.evidence_store import EvidenceStore


class TacitMiner:
    """控制 5-8 轮追问，产出结构化 STAR。"""

    METHODS = ["critical_incident", "contrast", "laddering", "counterfactual", "metaphor"]

    def __init__(self, root, domain, source):
        self.store = EvidenceStore(root)
        self.domain = domain
        self.source = source
        self.star = {
            "Background": "",
            "Task": "",
            "Action": [],
            "Result": "",
            "Key Insight": "",
            "Boundary": "",
        }
        self.verbatim = []
        self.round = 0
        self.max_rounds = 8

    def is_complete(self):
        return all([
            self.star["Background"],
            self.star["Task"],
            self.star["Action"],
            self.star["Result"],
        ])

    def should_continue(self):
        return self.round < self.max_rounds and not self.is_complete()

    def next_question(self, user_last_msg):
        """根据当前 STAR 完整度选择下一个问题。"""
        self.round += 1
        if not self.star["Background"]:
            return "当时是什么情况？最大的压力或问题是什么？"
        if not self.star["Task"]:
            return "你的具体任务或目标是什么？"
        if not self.star["Action"]:
            return "你具体做了哪几步？最难的一步是什么？"
        if not self.star["Result"]:
            return "最后结果怎么衡量？有没有数字？"
        if not self.star["Key Insight"]:
            return "如果总结成一条关键判断，那会是什么？"
        if not self.star["Boundary"]:
            return "什么情况下这条判断不适用？"
        return "还有没有其他细节能补充？"

    def ingest(self, user_msg):
        """解析用户回答，用启发式规则更新 star（SKILL.md 中的 Agent 负责真实语义解析）。"""
        self.verbatim.append(user_msg)
        # 简单启发式填充，用于命令行骨架测试
        if "当时" in user_msg and not self.star["Background"]:
            self.star["Background"] = user_msg
        elif "目标" in user_msg or "任务" in user_msg and not self.star["Task"]:
            self.star["Task"] = user_msg
        elif ("做了" in user_msg or "步骤" in user_msg) and not self.star["Action"]:
            self.star["Action"] = [user_msg]
        elif ("结果" in user_msg or "%" in user_msg or "万" in user_msg) and not self.star["Result"]:
            self.star["Result"] = user_msg
        elif ("判断" in user_msg or "因为" in user_msg) and not self.star["Key Insight"]:
            self.star["Key Insight"] = user_msg
        elif ("除非" in user_msg or "如果" in user_msg) and not self.star["Boundary"]:
            self.star["Boundary"] = user_msg

    def teachback(self):
        return "所以当时的情况是：%s，任务是：%s，你做了：%s，结果是：%s。对吗？" % (
            self.star["Background"] or "（待补充）",
            self.star["Task"] or "（待补充）",
            "；".join(self.star["Action"]) or "（待补充）",
            self.star["Result"] or "（待补充）",
        )

    def save(self, description, confidence="confirmed"):
        return self.store.save(
            domain=self.domain,
            description=description,
            source=self.source,
            star=self.star,
            confidence=confidence,
            verbatim="\n".join(self.verbatim[-3:]),
        )


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb", default=None)
    ap.add_argument("--domain", default="work_experience")
    ap.add_argument("--source", default="测试")
    args = ap.parse_args()
    import common
    root = common.kb_root(args.kb)
    miner = TacitMiner(root, args.domain, args.source)
    print(miner.next_question(""))


if __name__ == "__main__":
    main()
