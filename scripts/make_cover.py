#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 1024 提交用作品封面 v4（1600x1200, 4:3）——像素复古风。
参考 WaytoAGI 1024 用餐赛道官方海报视觉语言：8-bit 像素背景 + CRT 电视 +
手绘金色 M + 彩虹联名行；所有文字块垫深色金边面板（游戏对话框风格）。
中文大字用小字号渲染后 NEAREST 放大得真像素锯齿。
内置溢出检测：每块文字与其所在面板边界比对，超出即报警。
用法：python3 scripts/make_cover.py
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BG = os.path.join(ROOT, "assets", "8_bit_pixel_art_poster_illustr_2026-10-24T12-49-07.png")
OUT_PNG = os.path.join(ROOT, "docs", "cover-1024.png")
OUT_JPG = os.path.join(ROOT, "docs", "cover-1024.jpg")

W, H = 1600, 1200
PIX = 4  # 像素放大倍数

GOLD = (255, 205, 43)
RED = (214, 32, 46)
RED_DARK = (70, 6, 18)
INK = (26, 16, 20)
PANEL = (22, 12, 16, 236)
WHITE = (255, 255, 255)
CREAM = (255, 240, 214)
RAINBOW = [(238, 60, 60), (245, 150, 40), (250, 210, 60), (70, 190, 90),
           (60, 140, 235), (150, 90, 220)]

FONT_W3 = "/System/Library/Fonts/Hiragino Sans GB.ttc"
FONT_W6 = "/System/Library/Fonts/Hiragino Sans GB.ttc"

ISSUES = []  # 溢出告警收集


def font(size, bold=False):
    return ImageFont.truetype(FONT_W6 if bold else FONT_W3, size,
                              index=2 if bold else 0)


def fit(name, bbox, box):
    """文字 bbox 必须完整落在面板 box 内，否则记一条告警。"""
    if (bbox[0] < box[0] - 1 or bbox[1] < box[1] - 1
            or bbox[2] > box[2] + 1 or bbox[3] > box[3] + 1):
        ISSUES.append("%s: 文字%s 超出面板%s" % (name, bbox, box))


def pixel_text(img, pos, text, final_size, fill, stroke_fill=None,
               bold=True, scale=PIX, stroke_w=2, spacing=0):
    """小字号渲染后 NEAREST 放大，得到 8-bit 像素文字。返回粘贴后的 (w, h)。"""
    small = final_size // scale
    f = font(small, bold)
    sw = stroke_w if stroke_fill else 0
    tmp = Image.new("RGBA", (10, 10))
    td = ImageDraw.Draw(tmp)
    bbox = td.textbbox((0, 0), text, font=f, stroke_width=sw)
    if spacing:
        w = td.textlength(text, font=f) + spacing * (len(text) - 1) / scale
        layer = Image.new("RGBA", (int(w) + 24, bbox[3] - bbox[1] + 24), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        x = 12 - bbox[0]
        for ch in text:
            ld.text((x, 12 - bbox[1]), ch, font=f, fill=fill,
                    stroke_width=sw, stroke_fill=stroke_fill or fill)
            x += ld.textlength(ch, font=f) + spacing / scale
    else:
        layer = Image.new("RGBA", (bbox[2] - bbox[0] + 24, bbox[3] - bbox[1] + 24),
                          (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        ld.text((12 - bbox[0], 12 - bbox[1]), text, font=f, fill=fill,
                stroke_width=sw, stroke_fill=stroke_fill or fill)
    big = layer.resize((layer.width * scale, layer.height * scale), Image.NEAREST)
    if img is not None:
        img.paste(big, pos, big)
    return big.width, big.height


def draw_text(d, xy, s, f, fill, stroke=0, stroke_fill=None):
    d.text(xy, s, font=f, fill=fill, stroke_width=stroke,
           stroke_fill=stroke_fill or RED_DARK)


def panel(d, box, radius=14, fill=PANEL, outline=GOLD, width=3):
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


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


def stat_pill(img, x, y, text, size=26):
    """麦当劳黄标签：金底 + 深红描边 + 墨色清晰粗体（小字号不用像素字，避免糊）。"""
    d = ImageDraw.Draw(img)
    f = font(size, True)
    bbox = d.textbbox((0, 0), text, font=f)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    bw, bh = tw + 44, th + 26
    d.rounded_rectangle([x, y, x + bw, y + bh], radius=8, fill=GOLD,
                        outline=RED_DARK, width=2)
    d.text((x + 22 - bbox[0], y + 13 - bbox[1]), text, font=f, fill=INK)
    return x + bw, y + bh


def main():
    if not os.path.exists(BG):
        sys.exit("背景图不存在: %s" % BG)
    os.makedirs(os.path.dirname(OUT_PNG), exist_ok=True)

    bg = Image.open(BG).convert("RGBA").resize((W, H), Image.LANCZOS)

    # 顶部与底部压暗，让面板与场景融合
    shade = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(shade)
    for y in range(H):
        top = max(0, int(170 * max(0.0, 1 - y / 470.0) ** 1.4)) if y < 470 else 0
        bot = max(0, int(190 * max(0.0, (y - 880) / 320.0) ** 1.4)) if y > 880 else 0
        sd.line([(0, y), (W, y)], fill=max(top, bot))
    dark = Image.new("RGBA", (W, H), (18, 8, 12, 255))
    bg = Image.composite(dark, bg, shade).convert("RGBA")
    d = ImageDraw.Draw(bg)

    # ============ 面板 1：顶部联名横条 ============
    bar = [52, 34, W - 52, 100]
    panel(d, bar, radius=12)
    f_brand = font(30, bold=True)
    x, y = 76, 52
    for i, ch in enumerate("WaytoAGI"):
        d.text((x, y), ch, font=f_brand, fill=RAINBOW[i % len(RAINBOW)])
        x += d.textlength(ch, font=f_brand)
    d.text((x + 20, y), "×", font=f_brand, fill=(255, 255, 255, 210))
    x += 20 + d.textlength("×", font=f_brand) + 20
    d.text((x, y), "WORKBUDDY", font=font(30, True), fill=WHITE)
    x += d.textlength("WORKBUDDY", font=f_brand)
    d.text((x + 20, y), "×", font=f_brand, fill=(255, 255, 255, 210))
    x += 20 + d.textlength("×", font=f_brand) + 20
    draw_m_logo(d, x, y - 4, 34)
    x += 34 * 2 + 12
    d.text((x, y), "麦当劳 MCP", font=f_brand, fill=GOLD)
    brand_end = x + d.textlength("麦当劳 MCP", font=f_brand)
    fit("联名行", (76, y, brand_end, y + 40), bar)
    # 右上角赛事信息
    f_evt = font(24)
    txt = "AI切磋大会 · 1024 超能 Coding 周末 · 用餐赛道"
    evt_w = d.textlength(txt, font=f_evt)
    d.text((W - 76 - evt_w, y + 6), txt, font=f_evt, fill=(255, 235, 200, 235))
    fit("赛事条", (W - 76 - evt_w, y, W - 76, y + 36), bar)

    # ============ 面板 2：标题大对话框 ============
    tp = [52, 108, 880, 514]
    panel(d, tp, radius=16)
    tw_, th_ = pixel_text(bg, (74, 122), "麦门军师", 160, GOLD,
                          stroke_fill=RED_DARK, bold=True, stroke_w=2, spacing=6)
    fit("大标题", (74, 122, 74 + tw_, 122 + th_), tp)
    for i in range(0, 500, 16):                       # 像素金线
        d.rectangle([82 + i, 340, 82 + i + 10, 348], fill=GOLD)
    d.text((82, 362), "MaiStrategist", font=font(34, True), fill=WHITE)
    bb = d.textbbox((82, 362), "MaiStrategist", font=font(34, True))
    fit("英文名", bb, tp)
    f_tag = font(30)
    t1 = "说句话的功夫，AI 替你领券、凑单、"
    t2 = "薅出神之一单——官方核价，闭眼冲"
    d.text((82, 418), t1, font=f_tag, fill=CREAM)
    fit("标语1", d.textbbox((82, 418), t1, font=f_tag), tp)
    d.text((82, 458), t2, font=f_tag, fill=CREAM)
    fit("标语2", d.textbbox((82, 458), t2, font=f_tag), tp)

    # ============ 战绩标签（右上 2x2 麦当劳黄签） ============
    stats = ["立省", "官方核价分毫不差", "113 个真实餐品", "热量预算模式"]
    for i, t in enumerate(stats):
        col, row = i % 2, i // 2
        ex, ey = stat_pill(bg, 1004 + col * 292, 138 + row * 66, t)
        if ex > W - 8 or ey > H - 8:
            ISSUES.append("标签%d 超出画布: (%d,%d)" % (i, ex, ey))

    # ============ CRT 屏幕叠字（48px 起步，保证笔画清晰） ============
    pixel_text(bg, (448, 682), "搭配完成", 48, (255, 140, 100),
               stroke_fill=(60, 0, 6), bold=True)
    pixel_text(bg, (1040, 706), "开饭!", 48, (120, 30, 10), bold=True)

    # ============ 面板 3：左下信息区 ============
    bp = [52, 1030, 830, 1152]
    panel(d, bp, radius=12)
    s1 = "一键下单 · 把饭点安排明白"
    d.text((78, 1052), s1, font=font(30), fill=CREAM)
    fit("底行1", d.textbbox((78, 1052), s1, font=font(30)), bp)
    s2 = "github.com/JaneConan/mcd-mcp-strategist"
    d.text((78, 1098), s2, font=font(30, True), fill=GOLD)
    fit("底行2", d.textbbox((78, 1098), s2, font=font(30, True)), bp)

    # ============ 右下：二维码卡片（从简：扫码上车 + Star） ============
    try:
        import qrcode
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,
                           box_size=10, border=2)
        qr.add_data("https://github.com/JaneConan/mcd-mcp-strategist")
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="#1a1014",
                               back_color="white").convert("RGB")
        qr_size = 150
        qr_img = qr_img.resize((qr_size, qr_size), Image.NEAREST)
        card = [1180, 1002, W - 8, H - 8]
        d.rounded_rectangle(card, radius=14, fill=(255, 255, 255, 248),
                            outline=GOLD, width=3)
        bg.paste(qr_img, (card[0] + 22, card[1] + 20))
        tx = card[0] + 22 + qr_size + 24
        f_q1, f_q2 = font(30, True), font(26, True)
        q1, q2 = "扫码上车", "Star 麦门军师"
        d.text((tx, 1058), q1, font=f_q1, fill=INK)
        d.text((tx, 1104), q2, font=f_q2, fill=RED)
        fit("QR文案1", d.textbbox((tx, 1058), q1, font=f_q1), card)
        fit("QR文案2", d.textbbox((tx, 1104), q2, font=f_q2), card)
    except ImportError:
        print("提示: pip install qrcode 后可生成右下角二维码")

    bg.convert("RGB").save(OUT_PNG, "PNG")
    bg.convert("RGB").save(OUT_JPG, "JPEG", quality=92)
    for p in (OUT_PNG, OUT_JPG):
        print("%s  %.2f MB" % (p, os.path.getsize(p) / 1048576.0))
    print("size:", Image.open(OUT_PNG).size)
    if ISSUES:
        print("!! 溢出告警 %d 条:" % len(ISSUES))
        for s in ISSUES:
            print("  -", s)
    else:
        print("溢出检测: 全部文字均在面板内 OK")


if __name__ == "__main__":
    main()
