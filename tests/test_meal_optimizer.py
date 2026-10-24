#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""麦门军师优化引擎单元测试: python3 tests/test_meal_optimizer.py"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from meal_optimizer import enumerate_plans, suggest_addon  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "..", "data", "menu_sample.json"), encoding="utf-8") as f:
    SAMPLE = json.load(f)


class TestOptimizer(unittest.TestCase):
    def test_returns_plans(self):
        by_price, by_score, by_budget, by_save = enumerate_plans(SAMPLE)
        self.assertGreater(len(by_price), 0)
        self.assertGreater(len(by_score), 0)
        self.assertGreater(len(by_budget), 0)
        self.assertGreater(len(by_save), 0)

    def test_budget_respected(self):
        data = dict(SAMPLE, budget=30.0, people=1)
        by_price, _, _, _ = enumerate_plans(data)
        for p in by_price:
            self.assertLessEqual(p["final_price"], 30.0)

    def test_cheapest_is_cheapest(self):
        data = dict(SAMPLE, budget=80.0, people=2)
        by_price, _, _, _ = enumerate_plans(data)
        prices = [p["final_price"] for p in by_price]
        self.assertEqual(prices, sorted(prices))

    def test_threshold_coupon_applied(self):
        data = dict(SAMPLE, budget=80.0, people=2)
        by_price, _, _, _ = enumerate_plans(data)
        # 原价过 59 的组合应能用上满 59 减 18
        rich = [p for p in by_price if p["base_price"] >= 59.0]
        self.assertTrue(rich, "样例数据应存在原价>=59 的组合")
        for p in rich:
            self.assertGreater(p["discount"], 0)

    def test_calorie_constraint(self):
        data = dict(SAMPLE, budget=80.0, people=2, max_kcal=1500)
        by_price, _, _, _ = enumerate_plans(data)
        self.assertGreater(len(by_price), 0, "1500 kcal 内应有可行方案")
        for p in by_price:
            self.assertLessEqual(p["total_kcal"], 1500)

    def test_must_have_and_exclude(self):
        data = dict(SAMPLE, budget=80.0, people=2, must_have=["BIG_MAC"], exclude=["COKE_S", "COKE_M"])
        by_price, _, _, _ = enumerate_plans(data)
        for p in by_price:
            codes = {i["code"] for i in p["items"]}
            self.assertIn("BIG_MAC", codes)
            self.assertNotIn("COKE_S", codes)
            self.assertNotIn("COKE_M", codes)

    def test_people_scaling(self):
        data = dict(SAMPLE, budget=150.0, people=3)
        by_price, _, _, _ = enumerate_plans(data)
        mains = sum(i["qty"] for p in by_price for i in p["items"] if i["category"] == "main")
        self.assertGreaterEqual(mains, 3)

    def test_item_coupon_better_than_none(self):
        data = dict(SAMPLE, budget=80.0, people=2)
        by_price, _, _, _ = enumerate_plans(data)
        # 含可减汉堡的组合应至少拿到 5 元立减或用更优的券
        with_burger = [p for p in by_price if any(i["code"] in ("BIG_MAC", "SPICY_CHICKEN_BURGER", "DOUBLE_BEEF") for i in p["items"])]
        self.assertTrue(with_burger)
        for p in with_burger:
            self.assertGreaterEqual(p["discount"], 5.0)

    def test_suggest_addon_when_close_to_threshold(self):
        data = dict(SAMPLE, budget=80.0, people=2)
        by_price, _, _, _ = enumerate_plans(data)
        sug = suggest_addon(by_price[0], data)
        # 最便宜方案通常够不到 39 门槛, 凑单提示可能为 None; 不为 None 时结构须正确
        if sug is not None:
            self.assertIn("coupon", sug)
            self.assertGreater(sug["net_save"], 0.0)

    def test_no_feasible_plan(self):
        data = dict(SAMPLE, budget=1.0, people=4)
        by_price, _, _, _ = enumerate_plans(data)
        self.assertEqual(len(by_price), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
