#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麦门军师 · 凑单/用券优化引擎 (meal_optimizer.py)
================================================

在「餐品组合 × 优惠券」空间中搜索最优订单。纯标准库实现，无网络依赖——
麦当劳 MCP 负责提供真实菜单/券/价格数据，本引擎负责算账。

算法: 多模板 + Beam Search(束搜索)
  1. 按人数生成「阵法模板」(饱腹/丰盛/简约/分享/轻食/团圆)，确定各分类件数
  2. 每个模板按槽位逐槽填充餐品，每步保留 Top-K 候选(beam)，按三种目标
     (最便宜/最性价比/最贴近预算) 分别搜索，避免组合爆炸
  3. 对每个完整组合枚举最优用券方案(不叠化取单张最大减免，可叠化贪心叠加)
  4. 官方核价(calculate-price)前，本引擎输出均为候选，以官方返回为准

输入 JSON 格式（MCP 真实返回按此结构组装）:
{
  "budget": 80.0,                 # 预算（元），可选
  "people": 2,                    # 人数，默认 1
  "max_kcal": 1200,               # 热量上限（千卡），可选
  "must_have": ["BIG_MAC"],       # 必吃品编码，可选
  "exclude": ["COKE_ZERO"],       # 忌口编码，可选
  "delivery_fee": 0.0,            # 配送费，可选
  "items": [                      # 菜单（query-meals 返回组装）
    {"code": "BIG_MAC", "name": "巨无霸", "category": "main",
     "price": 23.5, "kcal": 520, "tags": ["burger"]}
  ],
  "coupons": [                    # 优惠券（query-my-coupons / query-store-coupons 组装）
    {"id": "c1", "name": "满39减10", "type": "threshold",
     "threshold": 39.0, "value": 10.0, "scope": "all", "stackable": false}
  ],
  "coupon_stacking": false        # 优惠券是否可叠加（以官方规则为准）
}

category 取值: main(主食) / side(小食) / drink(饮品) / dessert(甜品)
coupon.type 取值:
  threshold  满 threshold 减 value（scope=all 全场，或分类/编码列表）
  percent    全场/分类折扣，value 为折扣率(0.85 = 85折)
  item       单品券，scope 为餐品编码列表，value 为立减金额或 {"price": 新价}
  fixed_bundle 固定价任选券，scope 为适用餐品编码列表，
             value={"price": 任选总价, "count": 需选件数}
             （例: 19.9元王牌炸鸡任选2 → price=19.9, count=2）
  delivery   免配送费，value 为配送费减免额

输出 JSON: {"plans": [...], "suggestion": {...}, "stats": {...}}
"""
import argparse
import json
import sys
from itertools import combinations

BEAM_WIDTH = 160          # 束宽：每步保留的候选数
COUPON_MARGIN = 30.0      # 束搜索预算余量（凑券门槛可能高于预算）
CAT_TOP_N = 12            # 每个分类最多参与搜索的单品数（按价格升序，必吃品强制保留）


# ---------------------------------------------------------------- 模板
def build_templates(people):
    """按人数生成阵法模板: [ {分类: 件数}, ... ]
    每个基础模板再派生一个「套餐变体」(combo 槽位替换一个 main 槽位)，
    让套餐类餐品(如三件套)能进入搜索空间。"""
    P = people
    bases = [
        {"main": P, "side": P, "drink": P},                                    # 饱腹型
        {"main": P, "drink": P},                                               # 简约型
        {"main": P, "side": 1, "drink": P},                                    # 轻食型
        {"main": P + 1, "side": P + 1, "drink": P, "dessert": 1},              # 丰盛型
    ]
    if P >= 2:
        bases.append({"main": P, "side": P + 1, "drink": P + 1, "dessert": 1})  # 分享型
    if P >= 3:
        bases.append({"main": P + 1, "side": P + 1, "drink": P + 1, "dessert": 1})  # 团圆型

    templates = []
    for t in bases:
        templates.append(dict(t))
        # 套餐变体: 用 1 个 combo 槽替换 1 个 main 槽
        variant = dict(t)
        if variant.get("main", 0) >= 1:
            variant["main"] = variant["main"] - 1
            variant["combo"] = variant.get("combo", 0) + 1
            templates.append(variant)
        else:
            variant["combo"] = variant.get("combo", 0) + 1
            templates.append(variant)
    return templates


# ---------------------------------------------------------------- 用券
def applicable_coupons(coupons, items, delivery_fee):
    """把券按作用域展开成 (coupon, 适用商品原价合计, 减免额) 候选。"""
    out = []
    for c in coupons:
        ctype = c.get("type")
        scope = c.get("scope", "all")
        if ctype in ("threshold", "percent"):
            if scope == "all":
                base = sum(i["price"] * i["qty"] for i in items)
            else:
                base = sum(
                    i["price"] * i["qty"] for i in items
                    if i["category"] in scope or i["code"] in scope
                )
            if ctype == "threshold":
                if base >= c["threshold"]:
                    out.append((c, base, c["value"]))
            elif base > 0:
                out.append((c, base, round(base * (1 - c["value"]), 2)))
        elif ctype == "item":
            codes = scope if isinstance(scope, list) else [scope]
            disc = 0.0
            for i in items:
                if i["code"] in codes:
                    if isinstance(c["value"], dict) and "price" in c["value"]:
                        disc += max(0.0, i["price"] - c["value"]["price"]) * i["qty"]
                    else:
                        disc += c["value"] * i["qty"]
            if disc > 0:
                out.append((c, 0.0, disc))
        elif ctype == "fixed_bundle":
            # 固定价任选券: scope 为适用餐品编码, value={"price": 总价, "count": 需选件数}
            # 例: 19.9元王牌炸鸡任选2 -> 订单内含>=2件 scope 商品时,
            # 减免 = (scope 内最便宜的 count 件原价合计) - price
            codes = scope if isinstance(scope, list) else [scope]
            need = int(c.get("value", {}).get("count", 2))
            target = c.get("value", {}).get("price")
            if target is None:
                continue
            pool = []
            for i in items:
                if i["code"] in codes:
                    pool.extend([i["price"]] * i["qty"])
            if len(pool) >= need:
                disc = sum(sorted(pool)[:need]) - target
                if disc > 0:
                    out.append((c, 0.0, round(disc, 2)))
        elif ctype == "delivery":
            if delivery_fee > 0:
                out.append((c, 0.0, min(c["value"], delivery_fee)))
    return out


def best_coupon_combo(coupons, items, delivery_fee, stacking):
    """返回最优用券方案: (券列表, 减免总额)。不叠加时取单张最大减免。"""
    cands = applicable_coupons(coupons, items, delivery_fee)
    if not cands:
        return [], 0.0
    if not stacking:
        c, _, disc = max(cands, key=lambda x: x[2])
        return [c], disc
    # 叠加：贪心取不互斥的券（简化模型：按减免额降序，累计不超商品原价+配送费）
    cands.sort(key=lambda x: x[2], reverse=True)
    chosen, total_disc = [], 0.0
    base = sum(i["price"] * i["qty"] for i in items) + delivery_fee
    for c, _, disc in cands:
        if total_disc + disc <= base:
            chosen.append(c)
            total_disc += disc
    return chosen, round(total_disc, 2)


# ---------------------------------------------------------------- 束搜索
def _state_key(chosen):
    return tuple(sorted((c["code"], c.get("qty", 1)) for c in chosen))


def _merge(chosen):
    """把槽位选择合并成带数量的商品列表。"""
    merged = {}
    for it in chosen:
        if it["code"] in merged:
            merged[it["code"]]["qty"] += 1
        else:
            merged[it["code"]] = dict(it, qty=it.get("qty", 1))
    return list(merged.values())


def _make_plan(chosen, ctx):
    """把一组槽位选择评估成完整方案（含用券），不满足约束返回 None。"""
    budget = ctx["budget"]
    items = _merge(chosen)
    kcal = sum(i.get("kcal", 0) * i["qty"] for i in items)
    if ctx["max_kcal"] and kcal > ctx["max_kcal"]:
        return None
    if ctx["must_have"] and not ctx["must_have"].issubset({i["code"] for i in items}):
        return None
    base = round(sum(i["price"] * i["qty"] for i in items), 2)
    if budget and base > budget * 1.5:
        return None
    chosen_c, disc = best_coupon_combo(ctx["coupons"], items, ctx["delivery_fee"], ctx["stacking"])
    final = round(max(0.0, base - disc) + ctx["delivery_fee"], 2)
    if budget and final > budget:
        return None
    return {
        "items": items,
        "base_price": base,
        "delivery_fee": ctx["delivery_fee"],
        "coupons": [
            {"id": c["id"], "name": c["name"], "type": c["type"]} for c in chosen_c
        ],
        "discount": disc,
        "final_price": final,
        "total_kcal": kcal,
    }


def anchored_plans(template, ctx, coupon):
    """
    券锚定方案: 束搜索按价格截断可能把高价券商品挤出 beam,
    这里对每张单品/任选券确定性地生成「锁定券商品 + 最便宜配齐」的方案,
    保证用券方案一定进入候选池。生成 2 个变体(纯省钱/略升级)。
    """
    ctype = coupon.get("type")
    scope = coupon.get("scope")
    if ctype not in ("item", "fixed_bundle") or not isinstance(scope, list) or not scope:
        return []
    if ctype == "item":
        anchors = scope[:1]
    else:
        n = int(coupon.get("value", {}).get("count", 2))
        anchors = scope[:n]
    anchor_items = [ctx["item_by_code"][c] for c in anchors if c in ctx["item_by_code"]]
    if not anchor_items:
        return []
    used = {}
    for it in anchor_items:
        used[it["category"]] = used.get(it["category"], 0) + 1
    remaining = {}
    for cat, n in template.items():
        left = n - used.get(cat, 0)
        if left > 0:
            remaining[cat] = left

    plans = []
    for variant in (0, 1):  # 0=每槽最便宜, 1=部分槽往贵选一档
        chosen = [dict(it, qty=1) for it in anchor_items]
        for cat, n in remaining.items():
            cands = ctx["cand_by_cat"].get(cat, [])
            if not cands:
                continue
            for k in range(n):
                idx = min(k + variant, len(cands) - 1)
                chosen.append(dict(cands[idx]))
        p = _make_plan(chosen, ctx)
        if p:
            plans.append(p)
    return plans


def beam_search(template, ctx, objective, beam_width=BEAM_WIDTH):
    """
    单模板束搜索。
    ctx: {by_cat, budget, people, max_kcal, must_have, exclude, coupons,
          delivery_fee, stacking}
    objective: cheapest | value | closest
    """
    budget = ctx["budget"]
    slots = []
    for cat, n in template.items():
        slots.extend([cat] * n)

    # 必吃品预处理: 从对应分类槽位中扣除
    must = list(ctx["must_have"])
    forced = {}
    remaining_slots = list(slots)
    for code in must:
        item = ctx["item_by_code"].get(code)
        if not item:
            continue
        cat = item["category"]
        if cat in remaining_slots:
            remaining_slots.remove(cat)
            forced[code] = item
        else:
            return []  # 模板装不下必吃品

    forced_items = [dict(v, qty=1) for v in forced.values()]
    forced_base = sum(i["price"] for i in forced_items)

    # 每槽候选: 对应分类 Top-N（价格升序）
    cand_by_cat = ctx["cand_by_cat"]

    # 初始束（含强制必吃品）
    beam = [(forced_items, forced_base)]

    for cat in remaining_slots:
        nxt = []
        cands = cand_by_cat.get(cat, [])
        if not cands:
            return []
        for chosen, base in beam:
            for it in cands:
                nb = base + it["price"]
                if budget and nb > budget + COUPON_MARGIN:
                    continue
                nxt.append((chosen + [dict(it)], nb))
        if not nxt:
            return []
        # 去重 + 排序 + 截断
        seen, uniq = set(), []
        for chosen, base in nxt:
            k = _state_key(chosen)
            if k in seen:
                continue
            seen.add(k)
            uniq.append((chosen, base))
        uniq.sort(key=lambda s: _objective_key(s, objective, budget))
        beam = uniq[:beam_width]

    # 生成完整方案
    plans = []
    for chosen, base in beam:
        p = _make_plan(chosen, ctx)
        if p:
            plans.append(p)
    return plans


def _objective_key(state, objective, budget):
    chosen, base = state
    kcal = sum(i.get("kcal", 0) for i in chosen)
    if objective == "cheapest":
        return (base, -kcal)
    if objective == "value":
        cats = len({i["category"] for i in chosen})
        n = len(chosen)
        codes = [i["code"] for i in chosen]
        dup = len(codes) - len(set(codes))  # 重复单品惩罚，保证阵法有排面
        score = 0.0
        if base > 0:
            score = (
                0.45 * min(kcal / base / 30.0, 1.0)
                + 0.25 * (cats / 4.0)
                + 0.30 * min(n / 8.0, 1.0)
                - 0.06 * dup
            )
        return (-score, base)
    # closest
    return (abs(base - budget) if budget else 0.0, base)


def plan_score(plan, budget):
    if plan["final_price"] <= 0:
        return 0.0
    cats = len({i["category"] for i in plan["items"]})
    n_items = sum(i["qty"] for i in plan["items"])
    closeness = 1.0 - abs(plan["final_price"] - budget) / max(budget, 1.0) if budget else 0.0
    if plan["total_kcal"] > 0:
        term1 = 0.45 * min(plan["total_kcal"] / plan["final_price"] / 30.0, 1.0)
    else:
        # 无热量数据(如券探测补入的组合餐): 退化为「件数性价比」评分
        term1 = 0.30 * min(n_items / plan["final_price"] / 0.08, 1.0)
    return round(
        term1
        + 0.25 * (cats / 4.0)
        + 0.20 * min(n_items / 8.0, 1.0)
        + 0.10 * max(closeness, 0.0),
        4,
    )


def enumerate_plans(data):
    budget = data.get("budget")
    people = max(1, int(data.get("people", 1)))
    max_kcal = data.get("max_kcal")
    must_have = set(data.get("must_have", []))
    exclude = set(data.get("exclude", []))
    delivery_fee = float(data.get("delivery_fee", 0.0))
    stacking = bool(data.get("coupon_stacking", False))
    items_all = [i for i in data.get("items", []) if i["code"] not in exclude]

    by_cat = {}
    for it in items_all:
        by_cat.setdefault(it["category"], []).append(it)
    for cat in by_cat:
        by_cat[cat].sort(key=lambda x: (x["price"], -x.get("kcal", 0)))

    # 每分类取 Top-N（必吃品 + 券适用商品强制入池——否则高价券商品会被价格截断挡在门外）
    coupon_codes = set()
    for c in data.get("coupons", []):
        scope = c.get("scope", "all")
        if isinstance(scope, list):
            coupon_codes.update(scope)
    force_in = must_have | coupon_codes
    cand_by_cat = {}
    for cat, lst in by_cat.items():
        picked = lst[:CAT_TOP_N]
        codes = {i["code"] for i in picked}
        for it in lst:
            if it["code"] in force_in and it["code"] not in codes:
                picked.append(it)
                codes.add(it["code"])
        cand_by_cat[cat] = picked

    ctx = {
        "budget": budget,
        "people": people,
        "max_kcal": max_kcal,
        "must_have": must_have,
        "exclude": exclude,
        "coupons": data.get("coupons", []),
        "delivery_fee": delivery_fee,
        "stacking": stacking,
        "cand_by_cat": cand_by_cat,
        "item_by_code": {i["code"]: i for i in items_all},
    }

    all_plans = []
    for template in build_templates(people):
        for objective in ("cheapest", "value", "closest"):
            all_plans.extend(beam_search(template, ctx, objective))
        # 券锚定方案（保证用券方案进入候选池）
        for coupon in ctx["coupons"]:
            all_plans.extend(anchored_plans(template, ctx, coupon))

    # 去重（同组商品只保留最优惠方案）
    best_by_key = {}
    for p in all_plans:
        key = tuple(sorted((i["code"], i["qty"]) for i in p["items"]))
        if key not in best_by_key or p["final_price"] < best_by_key[key]["final_price"]:
            best_by_key[key] = p
    plans = list(best_by_key.values())
    for p in plans:
        p["score"] = plan_score(p, budget) if budget else None

    by_price = sorted(plans, key=lambda p: (p["final_price"], -p["total_kcal"]))
    by_score = sorted(plans, key=lambda p: -(p["score"] or 0))
    by_budget = sorted(
        plans,
        key=lambda p: (abs(p["final_price"] - budget) if budget else 0, p["final_price"]),
    )
    # 最大优惠视角: 省钱助手的核心视角——券减最多, 并列时实付更低者胜
    by_save = sorted(plans, key=lambda p: (-p["discount"], p["final_price"], -p["total_kcal"]))
    return by_price, by_score, by_budget, by_save


# ---------------------------------------------------------------- 凑单提示
def suggest_addon(plan, data):
    """凑单提示: 若加一件低价品就能跨过券门槛且净省，给出建议。"""
    items_all = [i for i in data.get("items", []) if i["code"] not in set(data.get("exclude", []))]
    in_plan = {i["code"] for i in plan["items"]}
    best = None
    for c in data.get("coupons", []):
        if c.get("type") != "threshold":
            continue
        gap = c["threshold"] - plan["base_price"]
        if gap <= 0:
            continue
        for it in sorted(items_all, key=lambda x: x["price"]):
            if it["code"] in in_plan:
                continue
            # 加这件能跨门槛，且券面额 > 加购价 → 净省
            if it["price"] >= gap and it["price"] < c["value"]:
                cand = {
                    "coupon": c["name"],
                    "gap": round(gap, 2),
                    "add": {"code": it["code"], "name": it["name"], "price": it["price"]},
                    "net_save": round(c["value"] - it["price"], 2),
                }
                if best is None or cand["net_save"] > best["net_save"]:
                    best = cand
    return best


# ---------------------------------------------------------------- 输出
def print_report(by_price, by_score, by_budget, data, top=3):
    budget = data.get("budget")
    people = data.get("people", 1)
    print("=" * 46)
    print("麦门军师 · 锦囊出炉")
    print(f"人数 {people} 人 | 预算 {f'{budget:.2f} 元' if budget else '不限'}")
    print("=" * 46)
    for view_name, plans in [
        ("最便宜", by_price), ("最性价比", by_score), ("最贴近预算", by_budget)
    ]:
        print(f"\n【{view_name}】")
        for rank, p in enumerate(plans[:top], 1):
            item_str = " + ".join(f"{i['name']}x{i['qty']}" for i in p["items"])
            print(f"  {rank}. {item_str}")
            print(
                f"     原价 {p['base_price']:.2f} | 券减 {p['discount']:.2f}"
                f" | 实付 {p['final_price']:.2f} 元 | {p['total_kcal']} kcal"
            )
            if p["coupons"]:
                print(f"     用券: {', '.join(c['name'] for c in p['coupons'])}")
    if by_price:
        sug = suggest_addon(by_price[0], data)
        if sug:
            print(
                f"\n💡 凑单提示: 再加 {sug['add']['name']}（{sug['add']['price']:.2f} 元）"
                f"即可用「{sug['coupon']}」，净省 {sug['net_save']:.2f} 元，值得冲！"
            )
    print()


def main():
    ap = argparse.ArgumentParser(description="麦门军师 · 凑单/用券优化引擎")
    ap.add_argument("--input", required=True, help="菜单+券+约束 JSON 文件")
    ap.add_argument("--budget", type=float, help="覆盖 JSON 中的预算")
    ap.add_argument("--people", type=int, help="覆盖 JSON 中的人数")
    ap.add_argument("--max-kcal", type=float, help="覆盖 JSON 中的热量上限")
    ap.add_argument("--top", type=int, default=3, help="每个视角输出前 N 个方案")
    ap.add_argument("--json", action="store_true", help="输出 JSON 而非文本报告")
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)
    if args.budget is not None:
        data["budget"] = args.budget
    if args.people is not None:
        data["people"] = args.people
    if args.max_kcal is not None:
        data["max_kcal"] = args.max_kcal

    by_price, by_score, by_budget = enumerate_plans(data)
    if args.json:
        print(json.dumps({
            "cheapest": by_price[: args.top],
            "best_value": by_score[: args.top],
            "closest_to_budget": by_budget[: args.top],
            "suggestion": suggest_addon(by_price[0], data) if by_price else None,
            "stats": {"total_plans": len(by_price)},
        }, ensure_ascii=False, indent=2))
    else:
        print_report(by_price, by_score, by_budget, data, args.top)


if __name__ == "__main__":
    sys.exit(main())
