#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 1024 提交用作品封面 v2（1600x1200, 4:3）——像素复古风。
参考 WaytoAGI 1024 用餐赛道官方海报视觉语言：8-bit 像素背景 + CRT 电视 +
手绘金色 M + 彩虹联名行；中文大字用小字号渲染后 NEAREST 放大，得到真像素锯齿。
用法：python3 scripts/make_cover.py
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BG = os.path.join(ROOT, "assets", "8_bit_pixel_art_poster_illustr_2026-10-24T12-49-07.png")
OUT_PNG = os.path.join(ROOT, "docs", "cover-1024.png")
OUT_JPG = os.path.join(ROOT, "docs", "cover-1024.jpg")

W, H = 1600, 1200
PIX = 4  # 像素放大倍数

GOLD = (255, 205, 43)
GOLD_DEEP = (255, 176, 32)
RED = (214, 32, 46)
RED_DARK = (70, 6, 18)
INK = (26, 16, 20)          # 深咖底色
WHITE = (255, 255, 255)
CREAM = (255, 240, 214)
RAINBOW = [(238, 60, 60), (245, 150, 40), (250, 210, 60), (70, 190, 90),
           (60, 140, 235), (150, 90, 220)]

FONT_W3 = "/System/Library/Fonts/Hiragino Sans GB.ttc"
FONT_W6 = "/System/Library/Fonts/Hiragino Sans GB.ttc"


def font(size, bold=False):
    return ImageFont.truetype(FONT_W6 if bold else FONT_W3, size,
                              index=2 if bold else 0)


def pixel_text(img, pos, text, final_size, fill, stroke_fill=None,
               bold=True, scale=PIX, stroke_w=2, spacing=0):
    """小字号渲染后 NEAREST 放大，得到 8-bit 像素文字。spacing 为字间距(像素, 最终尺寸)。"""
    small = final_size // scale
    f = font(small, bold)
    sw = stroke_w if stroke_fill else 0
    if spacing:
        # 逐字绘制以实现字间距
        tmp = Image.new("RGBA", (10, 10))
        td = ImageDraw.Draw(tmp)
        bbox = td.textbbox((0, 0), text, font=f, stroke_width=sw)
        w = td.textlength(text, font=f) + spacing * (len(text) - 1)
        layer = Image.new("RGBA", (int(w) + 20, bbox[3] - bbox[1] + 20), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        x = 10 - bbox[0]
        for ch in text:
            ld.text((x, 10 - bbox[1]), ch, font=f, fill=fill,
                    stroke_width=sw, stroke_fill=stroke_fill or fill)
            x += ld.textlength(ch, font=f) + spacing
    else:
        tmp = Image.new("RGBA", (10, 10))
        td = ImageDraw.Draw(tmp)
        bbox = td.textbbox((0, 0), text, font=f, stroke_width=sw)
        layer = Image.new("RGBA", (bbox[2] - bbox[0] + 20, bbox[3] - bbox[1] + 20),
                          (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        ld.text((10 - bbox[0], 10 - bbox[1]), text, font=f, fill=fill,
                stroke_width=sw, stroke_fill=stroke_fill or fill)
    big = layer.resize((layer.width * scale, layer.height * scale), Image.NEAREST)
    img.paste(big, pos, big)
    return big.width, big.height


def draw_text(d, xy, s, f, fill, stroke=0, stroke_fill=None):
    d.text(xy, s, font=f, fill=fill, stroke_width=stroke,
           stroke_fill=stroke_fill or RED_DARK)


def draw_m_logo(d, x, y, s=34, color=GOLD):
    """手绘简化版金色 M（双拱 + 外撇腿）。"""
    wdt = max(4, int(s * 0.26))
    d.arc([x, y + s * 0.05, x + s * 0.98, y + s * 1.18], 180, 360,
          fill=color, width=wdt)
    d.arc([x + s * 1.02, y + s * 0.05, x + s * 2.0, y + s * 1.18], 180, 360,
          fill=color, width=wdt)
    d.line([(x + s * 0.34, y + s * 0.60), (x + s * 0.02, y + s * 1.10)],
           fill=color, width=wdt)
    d.line([(x + s * 1.66, y + s * 0.60), (x + s * 1.98, y + s * 1.10)],
           fill=color, width=wdt)


def pixel_pill(img, x, y, text, final_size, pad_x=30, pad_y=14,
               bg=(22, 12, 14, 205), outline=(255, 205, 43, 160), fill=GOLD):
    d = ImageDraw.Draw(img)
    small = final_size // PIX
    f = font(small, True)
    tmp = Image.new("RGBA", (10, 10))
    td = ImageDraw.Draw(tmp)
    bbox = td.textbbox((0, 0), text, font=f)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    bw, bh = tw * PIX + pad_x * 2, th * PIX + pad_y * 2
    d.rounded_rectangle([x, y, x + bw, y + bh], radius=10, fill=bg,
                        outline=outline, width=2)
    pixel_text(img, (x + pad_x, y + pad_y - 2), text, final_size, fill,
               stroke_fill=None, bold=True)
    return x + bw, y + bh


def main():
    if not os.path.exists(BG):
        sys.exit("背景图不存在: %s" % BG)
    os.makedirs(os.path.dirname(OUT_PNG), exist_ok=True)

    bg = Image.open(BG).convert("RGBA").resize((W, H), Image.LANCZOS)

    # 顶部与底部压暗，保证文字可读（中间电视区保持鲜艳）
    shade = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(shade)
    for y in range(H):
        top = max(0, int(190 * (1 - y / 430.0) ** 1.4)) if y < 430 else 0
        bot = max(0, int(200 * ((y - 900) / 300.0) ** 1.4)) if y > 900 else 0
        sd.line([(0, y), (W, y)], fill=max(top, bot))
    dark = Image.new("RGBA", (W, H), (18, 8, 12, 255))
    bg = Image.composite(dark, bg, shade).convert("RGBA")
    d = ImageDraw.Draw(bg)

    # ---- 顶部联名行：WaytoAGI 彩虹字 × WorkBuddy × 金色M 麦当劳 MCP ----
    f_brand = font(30, bold=True)
    x = 72
    y = 46
    for i, ch in enumerate("WaytoAGI"):
        d.text((x, y), ch, font=f_brand, fill=RAINBOW[i % len(RAINBOW)])
        x += d.textlength(ch, font=f_brand)
    d.text((x + 22, y), "×", font=f_brand, fill=(255, 255, 255, 200))
    x += 22 + d.textlength("×", font=f_brand) + 22
    d.text((x, y), "WORKBUDDY", font=font(30, True), fill=WHITE)
    x += d.textlength("WORKBUDDY", font=f_brand)
    d.text((x + 22, y), "×", font=f_brand, fill=(255, 255, 255, 200))
    x += 22 + d.textlength("×", font=f_brand) + 22
    draw_m_logo(d, x, y - 4, 34)
    x += 34 * 2 + 12
    d.text((x, y), "麦当劳 MCP", font=f_brand, fill=GOLD)

    # 右上角赛事信息
    f_evt = font(26)
    txt = "AI切磋大会 · 1024 超能 Coding 周末 · 用餐赛道"
    d.text((W - 72 - d.textlength(txt, font=f_evt), y + 4), txt,
           font=f_evt, fill=(255, 235, 200, 220))

    # ---- 像素大标题 ----
    pixel_text(bg, (66, 118), "麦门军师", 208, GOLD, stroke_fill=RED_DARK,
               bold=True, stroke_w=2, spacing=6)
    # 标题下像素金线
    for i in range(0, 560, 16):
        d.rectangle([76 + i, 372, 76 + i + 10, 380], fill=GOLD)

    # ---- 英文名 + 一句话 ----
    d.text((78, 400), "MaiStrategist", font=font(46, True), fill=WHITE)
    f_tag = font(38)
    draw_text(d, (78, 472), "说句话的功夫，AI 替你领券、凑单、", f_tag, CREAM,
              stroke=2, stroke_fill=(40, 6, 12))
    draw_text(d, (78, 522), "薅出神之一单——官方核价，一键下单", f_tag, CREAM,
              stroke=2, stroke_fill=(40, 6, 12))

    # ---- 战绩胶囊（像素风，右上角 2x2 悬浮面板） ----
    stats = ["立省", "官方核价分毫不差", "113 个真实餐品", "热量预算模式"]
    for i, t in enumerate(stats):
        col, row = i % 2, i // 2
        pixel_pill(bg, 992 + col * 306, 142 + row * 66, t, 28)

    # ---- CRT 屏幕叠字（呼应官方海报的"搭配完成/开饭"） ----
    # 左屏（红）：搭配完成 ✓
    pixel_text(bg, (470, 690), "搭配完成", 34, (255, 120, 90),
               stroke_fill=(60, 0, 6), bold=True)
    # 右屏（黄）：开饭！
    pixel_text(bg, (1035, 715), "开饭!", 40, (120, 30, 10), bold=True)

    # ---- 左下角信息 ----
    d.text((78, 1046), "基于麦当劳 MCP · WorkBuddy Skill", font=font(32),
           fill=(255, 235, 200, 230))
    d.text((78, 1096), "github.com/JaneConan/mcd-mcp-strategist",
           font=font(32, True), fill=GOLD, stroke_width=2,
           stroke_fill=(40, 6, 12))

    # ---- 右下：盖住 AI 水印 + 核验徽标 ----
    d.rounded_rectangle([1160, 1096, W - 8, H - 8], radius=10,
                        fill=(14, 6, 8, 235), outline=(255, 205, 43, 190), width=2)
    f_ok = font(30, True)
    txt = "全链路实测通过 · MCP 35 工具在线"
    tw = d.textlength(txt, font=f_ok)
    pixel_text(bg, (int(1160 + (W - 8 - 1160 - tw * 1) // 2), 1112), txt, 30,
               GOLD, bold=True)

    bg.convert("RGB").save(OUT_PNG, "PNG")
    bg.convert("RGB").save(OUT_JPG, "JPEG", quality=92)
    for p in (OUT_PNG, OUT_JPG):
        print("%s  %.2f MB" % (p, os.path.getsize(p) / 1048576.0))
    print("size:", Image.open(OUT_PNG).size)


if __name__ == "__main__":
    main()
