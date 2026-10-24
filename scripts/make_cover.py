#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 1024 提交用作品封面 v3（1600x1200, 4:3）——像素复古风。
参考 WaytoAGI 1024 用餐赛道官方海报视觉语言：8-bit 像素背景 + CRT 电视 +
手绘金色 M + 彩虹联名行；所有文字块都垫深色金边面板（游戏对话框风格），
保证任何背景下文字都清晰。中文大字用小字号渲染后 NEAREST 放大得真像素锯齿。
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
PANEL = (22, 12, 16, 236)     # 面板底
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
    """小字号渲染后 NEAREST 放大，得到 8-bit 像素文字。spacing 为字间距(最终像素)。"""
    small = final_size // scale
    f = font(small, bold)
    sw = stroke_w if stroke_fill else 0
    tmp = Image.new("RGBA", (10, 10))
    td = ImageDraw.Draw(tmp)
    bbox = td.textbbox((0, 0), text, font=f, stroke_width=sw)
    if spacing:
        w = td.textlength(text, font=f) + spacing * (len(text) - 1)
        layer = Image.new("RGBA", (int(w) + 24, bbox[3] - bbox[1] + 24), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        x = 12 - bbox[0]
        for ch in text:
            ld.text((x, 12 - bbox[1]), ch, font=f, fill=fill,
                    stroke_width=sw, stroke_fill=stroke_fill or fill)
            x += ld.textlength(ch, font=f) + spacing
    else:
        layer = Image.new("RGBA", (bbox[2] - bbox[0] + 24, bbox[3] - bbox[1] + 24),
                          (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        ld.text((12 - bbox[0], 12 - bbox[1]), text, font=f, fill=fill,
                stroke_width=sw, stroke_fill=stroke_fill or fill)
    big = layer.resize((layer.width * scale, layer.height * scale), Image.NEAREST)
    img.paste(big, pos, big)


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


def pixel_pill(img, x, y, text, final_size, pad_x=30, pad_y=14,
               bg=(22, 12, 14, 225), outline=(255, 205, 43, 200), fill=GOLD):
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

    # 顶部与底部压暗，让面板与场景融合
    shade = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(shade)
    for y in range(H):
        top = max(0, int(170 * (1 - y / 470.0) ** 1.4)) if y < 470 else 0
        bot = max(0, int(190 * ((y - 880) / 320.0) ** 1.4)) if y > 880 else 0
        sd.line([(0, y), (W, y)], fill=max(top, bot))
    dark = Image.new("RGBA", (W, H), (18, 8, 12, 255))
    bg = Image.composite(dark, bg, shade).convert("RGBA")
    d = ImageDraw.Draw(bg)

    # ============ 面板 1：顶部联名横条 ============
    panel(d, [52, 34, W - 52, 100], radius=12)
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
    # 右上角赛事信息
    f_evt = font(26)
    txt = "AI切磋大会 · 1024 超能 Coding 周末 · 用餐赛道"
    d.text((W - 76 - d.textlength(txt, font=f_evt), y + 4), txt,
           font=f_evt, fill=(255, 235, 200, 235))

    # ============ 面板 2：标题区（大对话框） ============
    panel(d, [52, 116, 992, 474], radius=16)
    pixel_text(bg, (74, 132), "麦门军师", 176, GOLD, stroke_fill=RED_DARK,
               bold=True, stroke_w=2, spacing=6)
    for i in range(0, 520, 16):                       # 像素金线
        d.rectangle([82 + i, 344, 82 + i + 10, 352], fill=GOLD)
    d.text((84, 368), "MaiStrategist", font=font(40, True), fill=WHITE)
    f_tag = font(32)
    draw_text(d, (84, 424), "说句话的功夫，AI 替你领券、凑单、", f_tag, CREAM)
    draw_text(d, (84, 460), "薅出神之一单——官方核价", f_tag, CREAM)

    # ============ 战绩胶囊（右上 2x2 HUD 面板） ============
    stats = ["立省", "官方核价分毫不差", "113 个真实餐品", "热量预算模式"]
    for i, t in enumerate(stats):
        col, row = i % 2, i // 2
        pixel_pill(bg, 1004 + col * 292, 138 + row * 66, t, 26)

    # ============ CRT 屏幕叠字 ============
    pixel_text(bg, (470, 690), "搭配完成", 34, (255, 130, 95),
               stroke_fill=(60, 0, 6), bold=True)
    pixel_text(bg, (1058, 715), "开饭!", 40, (120, 30, 10), bold=True)

    # ============ 面板 3：左下信息区 ============
    panel(d, [52, 1030, 830, 1152], radius=12)
    d.text((78, 1052), "一键下单 · 把饭点安排明白",
           font=font(30), fill=CREAM)
    d.text((78, 1098), "github.com/JaneConan/mcd-mcp-strategist",
           font=font(30, True), fill=GOLD)

    # ============ 右下：二维码卡片 ============
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
        d.text((tx, card[1] + 24), "扫码访问仓库", font=font(30, True), fill=INK)
        d.text((tx, card[1] + 68), "github.com/JaneConan/", font=font(26),
               fill=(90, 40, 40))
        d.text((tx, card[1] + 100), "mcd-mcp-strategist", font=font(26),
               fill=(90, 40, 40))
        d.text((tx, card[1] + 140), "Star 一下麦门军师", font=font(26, True),
               fill=RED)
    except ImportError:
        print("提示: pip install qrcode 后可生成右下角二维码")

    bg.convert("RGB").save(OUT_PNG, "PNG")
    bg.convert("RGB").save(OUT_JPG, "JPEG", quality=92)
    for p in (OUT_PNG, OUT_JPG):
        print("%s  %.2f MB" % (p, os.path.getsize(p) / 1048576.0))
    print("size:", Image.open(OUT_PNG).size)


if __name__ == "__main__":
    main()
