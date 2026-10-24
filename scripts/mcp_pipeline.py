#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麦门军师 · MCP 端到端流水线（真实数据版）
==========================================
MCP 真实返回 → 优化引擎 → 官方核价校验 → 献锦囊。

用法:
  python3 scripts/mcp_pipeline.py --store 1980321 --budget 60 --people 2
  python3 scripts/mcp_pipeline.py --offline   # 用 /tmp 缓存的响应离线跑

流程:
  1. query-meals          菜单(113 餐品含价格)
  2. list-nutrition-foods 营养(160 餐品热量)
  3. query-my-coupons     我的券(3 张, 含有效期)
  4. query-store-coupons  门店券(权威商品编码 + couponId/couponCode)
  5. 门店券商品若不在菜单 → calculate-price 探测官方原价后补入
  6. 按今天(2026-10-24)过滤未生效的券
  7. meal_optimizer 优化 → 官方核价校验 → 输出锦囊
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, "/tmp")

TODAY = "2026-10-24"
STORE = "1980321"  # 麦当劳天津长荣大厦餐厅（南开大悦城附近）


# ---------------- MCP 调用（可切离线缓存） ----------------
def get_mcp():
    try:
        from mcd_chain1 import call_tool, tool_result_text
        return call_tool, tool_result_text
    except ImportError:
        return None, None


def fetch_tool(name, args, cache_file, offline, call_tool, tool_result_text):
    if offline and os.path.exists(cache_file):
        return open(cache_file, encoding="utf-8").read()
    text = tool_result_text(call_tool(name, args))
    with open(cache_file, "w", encoding="utf-8") as f:
        f.write(text)
    return text


def extract_json(text):
    start = text.find('{"success"')
    if start < 0:
        return None
    obj, _ = json.JSONDecoder().raw_decode(text[start:])
    return obj


# ---------------- 解析 ----------------
CATEGORY_MAP = {
    "人气热卖": "combo", "小食拼盘": "combo", "多人餐": "combo",
    "精选单人餐": "combo", "随心配": "combo", "大堡口福": "main",
    "鸡肉汉堡": "main", "牛肉汉堡": "main", "卷": "main", "早餐": "main",
    "汉堡": "main", "蘸酱炸鸡": "side", "小食": "side", "炸鸡": "side",
    "甜品": "dessert", "新地": "dessert", "冰淇淋": "dessert", "派": "dessert",
    "饮品": "drink", "饮料": "drink", "咖啡": "drink", "麦咖啡": "drink",
}


def map_category(cat_name):
    for key, val in CATEGORY_MAP.items():
        if key in cat_name:
            return val
    return "combo"


def parse_menu(text):
    d = extract_json(text)
    data = d["data"]
    meals = data["meals"]
    code_cat = {}
    for cat in data.get("categories", []):
        for m in cat.get("meals", []):
            if m.get("code"):
                code_cat[m["code"]] = map_category(cat.get("name", ""))
    items = {}
    for code, m in meals.items():
        try:
            price = float(m.get("currentPrice") or 0)
        except (TypeError, ValueError):
            continue
        if price <= 0:
            continue
        items[code] = {
            "code": code, "name": m.get("name", code),
            "category": code_cat.get(code, "combo"),
            "price": price,
            "originalPrice": float(m.get("originalPrice") or price),
        }
    return items


def parse_nutrition(text):
    d = extract_json(text)
    kcal = {}
    for line in (d.get("data") or "").splitlines():
        line = line.strip().rstrip(",")
        if not line or line.startswith("[") or "{" in line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 4 and parts[0]:
            try:
                kcal[parts[0]] = float(parts[3])
            except ValueError:
                pass
    return kcal


def attach_kcal(items, kcal):
    for it in items.values():
        name = it["name"]
        if name in kcal:
            it["kcal"] = kcal[name]
            continue
        for food, k in kcal.items():
            if food and (name.startswith(food) or food in name):
                it["kcal"] = k
                break
        else:
            it["kcal"] = 0


def parse_my_coupons(text):
    """query-my-coupons markdown -> [{name, price, valid_from, valid_to, tags}]"""
    out = []
    for block in re.split(r"\n## ", text):
        lines = block.splitlines()
        if not lines:
            continue
        title = lines[0].strip()
        price_m = re.search(r"¥([\d.]+)\s*\(用券价格\)", block)
        if not price_m:
            continue
        validity = re.search(r"\*\*有效期\*\*:\s*(\d{4}-\d{2}-\d{2})", block)
        vfrom = validity.group(1) if validity else "2000-01-01"
        vto_m = re.search(r"(\d{4}-\d{2}-\d{2})\s+\d{2}:\d{2}-\d{2}:\d{2}", block)
        out.append({
            "name": title,
            "price": float(price_m.group(1)),
            "valid_from": vfrom,
            "valid_to": vto_m.group(1) if vto_m else "2999-12-31",
            "tags": block,
        })
    return out


def parse_store_coupons(text):
    d = extract_json(text)
    out = []
    for c in d.get("data", []):
        out.append({
            "title": c.get("title"),
            "couponId": c.get("couponId"),
            "couponCode": c.get("couponCode"),
            "products": [p.get("productCode") for p in c.get("products", []) if p.get("productCode")],
        })
    return out


# ---------------- 主流程 ----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default=STORE)
    ap.add_argument("--budget", type=float, default=60.0)
    ap.add_argument("--people", type=int, default=2)
    ap.add_argument("--offline", action="store_true", help="用 /tmp 缓存离线跑")
    args = ap.parse_args()

    call_tool, tool_result_text = get_mcp()
    if not args.offline and call_tool is None:
        print("[警告] 无 MCP 直连模块，自动切离线模式")
        args.offline = True

    # 1-4. 拉数据
    menu_text = fetch_tool("query-meals",
                           {"storeCode": args.store, "orderType": 1, "beType": 1},
                           "/tmp/mcd_menu.json", args.offline, call_tool, tool_result_text)
    nut_text = fetch_tool("list-nutrition-foods", {}, "/tmp/mcd_nutrition.json",
                          args.offline, call_tool, tool_result_text)
    my_text = fetch_tool("query-my-coupons", {"page": "1", "pageSize": "200"},
                         "/tmp/mcd_my_coupons.json", args.offline, call_tool, tool_result_text)
    store_text = fetch_tool("query-store-coupons",
                            {"storeCode": args.store, "orderType": 1, "beType": 1},
                            "/tmp/mcd_store_coupons.json", args.offline, call_tool, tool_result_text)

    items = parse_menu(menu_text)
    kcal = parse_nutrition(nut_text)
    attach_kcal(items, kcal)
    my_coupons = parse_my_coupons(my_text)
    store_coupons = parse_store_coupons(store_text)
    print(f"[数据] 菜单 {len(items)} 餐品 | 营养 {len(kcal)} 条 | 我的券 {len(my_coupons)} 张 | 门店券 {len(store_coupons)} 张")

    # 5. 门店券商品不在菜单 → 官方核价探测补入
    for sc in store_coupons:
        for code in sc["products"]:
            if code in items:
                continue
            if args.offline:
                continue
            text = tool_result_text(call_tool("calculate-price", {
                "storeCode": args.store, "orderType": 1, "beType": 1,
                "items": [{"productCode": code, "quantity": 1,
                           "couponId": sc["couponId"], "couponCode": sc["couponCode"]}]}))
            d = extract_json(text)
            data = d.get("data", {}) if d else {}
            orig = (data.get("productOriginalPrice") or 0) / 100.0
            if orig > 0:
                items[code] = {
                    "code": code, "name": sc["title"], "category": "combo",
                    "price": orig, "originalPrice": orig, "kcal": 0,
                    "_via": "store-coupon-probe",
                }
                print(f"[探测] {sc['title']} 不在菜单，官方原价 ¥{orig:.2f}，已补入")

    # 6. 组装引擎输入（按今天过滤 + 权威 scope）
    engine_coupons = []
    for sc in store_coupons:
        # 门店券: 权威商品编码 + 券后价来自我的券(同标题)或标题解析
        mine = next((c for c in my_coupons if c["name"] == sc["title"]), None)
        price = mine["price"] if mine else None
        if price is None:
            continue
        codes = [c for c in sc["products"] if c in items]
        if not codes:
            continue
        engine_coupons.append({
            "id": sc["couponId"], "name": sc["title"], "type": "item",
            "scope": codes, "value": {"price": price},
            "couponId": sc["couponId"], "couponCode": sc["couponCode"],
            "valid_from": mine["valid_from"] if mine else "2000-01-01",
            "valid_to": mine["valid_to"] if mine else "2999-12-31",
            "stackable": False,
        })
    # 我的券里门店券没覆盖的（如任选券），按名称模糊匹配
    covered = {c["name"] for c in engine_coupons}
    for mc in my_coupons:
        if mc["name"] in covered:
            continue
        base = mc["name"].replace("元", "")
        codes = [it["code"] for it in items.values()
                 if base in it["name"] or it["name"] in base]
        if "任选" in mc["name"]:
            codes = [it["code"] for it in items.values()
                     if it["category"] == "side" and "鸡" in it["name"]] or codes
            engine_coupons.append({
                "id": f"my_{len(engine_coupons)}", "name": mc["name"],
                "type": "fixed_bundle", "scope": codes[:8],
                "value": {"price": mc["price"], "count": 2},
                "valid_from": mc["valid_from"], "valid_to": mc["valid_to"],
                "stackable": False,
            })
        elif codes:
            engine_coupons.append({
                "id": f"my_{len(engine_coupons)}", "name": mc["name"],
                "type": "item", "scope": codes[:4],
                "value": {"price": mc["price"]},
                "valid_from": mc["valid_from"], "valid_to": mc["valid_to"],
                "stackable": False,
            })

    active = [c for c in engine_coupons if c["valid_from"] <= TODAY <= c["valid_to"]]
    inactive = [c for c in engine_coupons if c not in active]
    for c in inactive:
        print(f"[跳过] 「{c['name']}」今天未生效（{c['valid_from']} 起）")
    print(f"[用券] 今日可用 {len(active)} 张: {', '.join(c['name'] for c in active)}")

    data = {
        "budget": args.budget, "people": args.people,
        "items": list(items.values()),
        "coupons": [{k: v for k, v in c.items() if not k.startswith("valid")} for c in active],
        "coupon_stacking": False, "delivery_fee": 0.0,
    }

    from meal_optimizer import enumerate_plans, suggest_addon
    by_price, by_score, by_budget, by_save = enumerate_plans(data)
    print(f"[优化] 候选方案 {len(by_price)} 套")

    def rank_of(saved):
        if saved >= 30.0:
            return "麦门巨佬"
        if saved >= 20.0:
            return "麦门长老"
        if saved >= 10.0:
            return "麦门道友"
        return "麦门学徒"

    # 7. 官方核价校验 Top1
    print("\n" + "=" * 56)
    print("🧙 麦门军师 · 锦囊（真实数据）")
    print(f"门店: 麦当劳天津长荣大厦餐厅 | {args.people} 人 | 预算 ¥{args.budget:.0f}")
    print("=" * 56)
    verified = None
    for view, plans in [("最便宜", by_price), ("最大优惠", by_save), ("最性价比", by_score), ("最贴近预算", by_budget)]:
        if not plans:
            continue
        print(f"\n【{view}】")
        for i, p in enumerate(plans[:3], 1):
            names = " + ".join(f"{x['name']}x{x['qty']}" for x in p["items"])
            print(f"  {i}. {names}")
            print(f"     原价 ¥{p['base_price']:.2f} | 券减 ¥{p['discount']:.2f} | 引擎实付 ¥{p['final_price']:.2f} | {p['total_kcal']}kcal")
            if p["coupons"]:
                print(f"     用券: {', '.join(c['name'] for c in p['coupons'])}")
        if view == "最便宜":
            if not args.offline:
                verified = verify(args.store, plans[0], active, call_tool, tool_result_text)
            top_save = by_save[0] if by_save else None
            if top_save and top_save["discount"] > 0:
                print(f"\n🏆 麦门段位: {rank_of(top_save['discount'])}（「{top_save['coupons'][0]['name']}」立省 ¥{top_save['discount']:.2f}，约等于多吃 {top_save['discount']/16.5:.1f} 个麦香鸡）")
                if not args.offline:
                    v2 = verify(args.store, top_save, active, call_tool, tool_result_text)
                    if v2 is not None:
                        mark = "✅ 一致" if abs(v2 - top_save["final_price"]) < 0.01 else f"⚠️ 引擎算 ¥{top_save['final_price']:.2f}，以官方为准"
                        print(f"   省钱方案官方核价: 实付 ¥{v2:.2f} {mark}")
    if verified is not None:
        print(f"\n✅ 官方核价: 实付 ¥{verified:.2f}" +
              ("（与引擎一致）" if abs(verified - by_price[0]["final_price"]) < 0.01
               else f"（引擎算 ¥{by_price[0]['final_price']:.2f} 有偏差，以官方为准）"))

    with open("/tmp/mcd_real_input.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    with open("/tmp/mcd_real_plans.json", "w", encoding="utf-8") as f:
        json.dump({"cheapest": by_price[:3], "best_value": by_score[:3],
                   "closest": by_budget[:3], "verified_price": verified},
                  f, ensure_ascii=False, indent=2)
    print("\n[saved] /tmp/mcd_real_input.json, /tmp/mcd_real_plans.json")


def verify(store, plan, active_coupons, call_tool, tool_result_text):
    """把引擎方案交给 calculate-price 官方核价（券挂到适用商品上）。"""
    full = {c["id"]: c for c in active_coupons}
    items = [{"productCode": it["code"], "quantity": it["qty"]} for it in plan["items"]]
    for used in plan["coupons"]:
        c = full.get(used["id"])
        if not c or c["type"] != "item":
            continue  # fixed_bundle 等复杂券型暂不送官方核价
        scope = c.get("scope") or []
        for entry in items:
            if entry["productCode"] in scope and "couponId" not in entry:
                entry["couponId"] = c.get("couponId", used["id"])
                entry["couponCode"] = c.get("couponCode", "")
                break
    text = tool_result_text(call_tool("calculate-price",
                                      {"storeCode": store, "orderType": 1, "beType": 1, "items": items}))
    d = extract_json(text)
    if not d:
        return None
    return (d.get("data", {}).get("price") or 0) / 100.0


if __name__ == "__main__":
    main()
