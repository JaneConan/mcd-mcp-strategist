#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 1024 提交用作品封面（1600x1200, 4:3）。
背景为 AI 生成的插画（assets/ 下），中文标题与文案用 PIL 精排，
保证文字清晰不错字。用法：python3 scripts/make_cover.py
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BG = os.path.join(ROOT, "assets", "Vibrant_hero_illustration_bann_2026-10-24T12-41-41.png")
OUT_PNG = os.path.join(ROOT, "docs", "cover-1024.png")
OUT_JPG = os.path.join(ROOT, "docs", "cover-1024.jpg")

W, H = 1600, 1200

# ---- 麦当劳品牌色 ----
GOLD = (255, 205, 43)        # 麦门金
GOLD_DEEP = (255, 176, 32)
RED = (200, 16, 46)          # 麦门红
RED_DARK = (90, 8, 24)       # 描边深红
WHITE = (255, 255, 255)

FONT_W3 = "/System/Library/Fonts/Hiragino Sans GB.ttc"
FONT_W6 = "/System/Library/Fonts/Hiragino Sans GB.ttc"


def font(size, bold=False):
    return ImageFont.truetype(FONT_W6 if bold else FONT_W3, size, index=2 if bold else 0)


def text_w(draw, s, f):
    return draw.textlength(s, font=f)


def draw_text(draw, xy, s, f, fill, stroke=0, stroke_fill=None):
    draw.text(xy, s, font=f, fill=fill, stroke_width=stroke,
              stroke_fill=stroke_fill or RED_DARK)


def pill(draw, x, y, text, f, pad_x=28, pad_y=12, bg=(255, 255, 255, 38),
         outline=(255, 255, 255, 150), fill=WHITE):
    tw = text_w(draw, text, f)
    th = f.size
    box = [x, y, x + tw + pad_x * 2, y + th + pad_y * 2]
    draw.rounded_rectangle(box, radius=(th + pad_y * 2) // 2, fill=bg,
                           outline=outline, width=2)
    draw.text((x + pad_x, y + pad_y - 2), text, font=f, fill=fill)
    return box[2], box[3]


def main():
    if not os.path.exists(BG):
        sys.exit("背景图不存在: %s" % BG)
    os.makedirs(os.path.dirname(OUT_PNG), exist_ok=True)

    bg = Image.open(BG).convert("RGBA").resize((W, H), Image.LANCZOS)

    # 左侧压暗渐变，保证文字可读
    shade = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(shade)
    for x in range(W):
        base = max(0.0, 1 - x / 1050.0)
        a = int(165 * base ** 1.35)
        sd.line([(x, 0), (x, H)], fill=a)
    dark = Image.new("RGBA", (W, H), (40, 0, 8, 255))
    bg = Image.composite(dark, bg, shade).convert("RGBA")

    d = ImageDraw.Draw(bg)

    # ---- 顶部赛事徽标 ----
    f_badge = font(34, bold=True)
    pill(d, 88, 84, "1024 程序员节 · 用餐赛道", f_badge,
         bg=(255, 255, 255, 235), outline=(255, 255, 255, 0), fill=RED)

    # ---- 主标题 ----
    f_title = font(168, bold=True)
    draw_text(d, (82, 148), "麦门军师", f_title, GOLD, stroke=7,
              stroke_fill=RED_DARK)
    # 标题下金线
    d.rounded_rectangle([90, 372, 560, 382], radius=6, fill=GOLD)

    # ---- 英文名 ----
    f_en = font(54, bold=True)
    draw_text(d, (92, 404), "MaiStrategist", f_en, WHITE, stroke=0)

    # ---- 一句话介绍 ----
    f_tag = font(45)
    draw_text(d, (92, 492), "说句话的功夫，AI 替你领券、凑单、", f_tag, WHITE,
              stroke=2, stroke_fill=(70, 0, 14))
    draw_text(d, (92, 552), "薅出神之一单——官方核价，一键下单", f_tag, WHITE,
              stroke=2, stroke_fill=(70, 0, 14))

    # ---- 战绩胶囊 ----
    f_pill = font(32, bold=True)
    x = 92
    y = 640
    for t in ["实测立省 ¥24.10", "官方核价分毫不差", "113 个真实餐品", "热量预算模式"]:
        x, _ = pill(d, x, y, t, f_pill)
        x += 18

    # ---- 左下角信息 ----
    f_info = font(34)
    draw_text(d, (92, 1035), "基于麦当劳 MCP · WorkBuddy Skill", f_info,
              (255, 235, 200), stroke=0)
    draw_text(d, (92, 1090), "github.com/JaneConan/mcd-mcp-strategist", f_info,
              GOLD, stroke=2, stroke_fill=(70, 0, 14))

    # ---- 右下：盖住 AI 水印 + 放核验徽标 ----
    # 先铺一块深色圆角底板，确保水印被完全遮盖
    d.rounded_rectangle([1150, 1100, W - 8, H - 8], radius=28,
                        fill=(15, 0, 5, 235), outline=(255, 205, 43, 200), width=2)
    f_ok = font(32, bold=True)
    txt = "全链路实测通过 · MCP 35 工具在线"
    tw = text_w(d, txt, f_ok)
    pill(d, (W - 8 + 1150 - tw - 64) // 2, 1112, txt, f_ok, pad_x=32,
         bg=(0, 0, 0, 0), outline=(0, 0, 0, 0), fill=GOLD)

    bg.convert("RGB").save(OUT_PNG, "PNG")
    bg.convert("RGB").save(OUT_JPG, "JPEG", quality=92)
    for p in (OUT_PNG, OUT_JPG):
        print("%s  %.2f MB" % (p, os.path.getsize(p) / 1048576.0))
    print("size:", Image.open(OUT_PNG).size)


if __name__ == "__main__":
    main()
