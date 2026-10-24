#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麦门军师 · 一键演示（无需 MCP Token）
用法: python3 scripts/demo.py
基于 data/menu_sample.json 示例数据跑通「解析需求 → 优化 → 实算占位 → 献锦囊」全流程。
接入麦当劳 MCP 后，menu_sample.json 可替换为 query-meals / query-my-coupons 的真实返回。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from meal_optimizer import enumerate_plans, suggest_addon  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE = os.path.join(HERE, "..", "data", "menu_sample.json")

RANKS = [(10.0, "麦门学徒"), (20.0, "麦门道友"), (30.0, "麦门长老")]


def rank_of(saved):
    if saved >= 30.0:
        return "麦门巨佬"
    for threshold, name in RANKS:
        if saved < threshold:
            return name
    return "麦门学徒"


def main():
    with open(SAMPLE, "r", encoding="utf-8") as f:
        data = json.load(f)

    by_price, by_score, by_budget, by_save = enumerate_plans(data)
    if not by_price:
        print("没有找到满足约束的阵法，请放宽预算或忌口。")
        return

    print("🧙 麦门军师上线。需求：2 人用餐，预算 80 元（示例数据）\n")
    for view, plans in [("最便宜", by_price), ("最性价比", by_score), ("最贴近预算", by_budget), ("最大优惠", by_save)]:
        print(f"【{view}】")
        for i, p in enumerate(plans[:3], 1):
            items = " + ".join(f"{x['name']}x{x['qty']}" for x in p["items"])
            print(f"  锦囊{i}: {items}")
            print(
                f"    原价 ¥{p['base_price']:.2f} | 券减 ¥{p['discount']:.2f}"
                f" | 实付 ¥{p['final_price']:.2f} | {p['total_kcal']} kcal"
                + (f" | 用券: {', '.join(c['name'] for c in p['coupons'])}" if p["coupons"] else "")
            )
        print()

    best = by_price[0]
    saved = best["discount"]
    print(
        f"🏆 麦门段位: {rank_of(saved)}（省下 ¥{saved:.2f}，"
        f"约等于多吃 {saved / 12.5:.1f} 个麦香鸡）"
    )
    sug = suggest_addon(best, data)
    if sug:
        print(
            f"💡 凑单提示: 再加 {sug['add']['name']}（¥{sug['add']['price']:.2f}）"
            f"即可用「{sug['coupon']}」，净省 ¥{sug['net_save']:.2f}，值得冲！"
        )


if __name__ == "__main__":
    main()
