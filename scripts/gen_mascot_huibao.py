import os
import sys
import math
import argparse
from PIL import Image, ImageDraw, ImageFilter

# 允许脚本从项目根目录直接运行
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from steps.image.font import font_manager


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def _mix(a, b, t: float):
    t = _clamp(t, 0.0, 1.0)
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
        int(a[3] + (b[3] - a[3]) * t),
    )


def _radial_glow(size, center, radius, color_rgba):
    w, h = size
    cx, cy = center
    base = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = base.load()
    for y in range(h):
        for x in range(w):
            d = math.hypot(x - cx, y - cy)
            if d > radius:
                continue
            a = int(color_rgba[3] * (1 - d / radius) ** 1.8)
            if a <= 0:
                continue
            px[x, y] = (color_rgba[0], color_rgba[1], color_rgba[2], a)
    return base.filter(ImageFilter.GaussianBlur(radius=8))


def _render_background(size=(1024, 1024)) -> Image.Image:
    """渲染背景（含网格与氛围光）。"""
    w, h = size
    bg = Image.new("RGBA", (w, h), (8, 10, 18, 255))
    draw = ImageDraw.Draw(bg)
    top = (14, 22, 40, 255)
    bottom = (22, 10, 28, 255)
    for y in range(h):
        t = y / (h - 1)
        c = _mix(top, bottom, t)
        draw.line([(0, y), (w, y)], fill=c)

    grid = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    g = ImageDraw.Draw(grid)
    step = 64
    for x in range(0, w, step):
        g.line([(x, 0), (x, h)], fill=(255, 255, 255, 10))
    for y in range(0, h, step):
        g.line([(0, y), (w, y)], fill=(255, 255, 255, 10))
    bg = Image.alpha_composite(bg, grid)

    # 霓虹氛围光
    bg = Image.alpha_composite(bg, _radial_glow((w, h), (int(w * 0.30), int(h * 0.25)), 380, (0, 242, 234, 85)))
    bg = Image.alpha_composite(bg, _radial_glow((w, h), (int(w * 0.75), int(h * 0.35)), 420, (255, 0, 80, 75)))
    return bg


def _render_robot_layer(size=(1024, 1024), show_name: bool = False, blink: bool = False) -> Image.Image:
    """
    渲染机器人本体（透明背景），适合直接叠加到其它图上。
    - show_name: 是否在下方显示“绘宝”名牌（片头通常不建议显示，避免抢焦点）
    - blink: 是否眨眼（用于片头动画切换）
    """
    w, h = size
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)

    # 配色（现代科技 + 可爱）
    white = (250, 252, 255, 255)
    pearl = (232, 238, 248, 255)
    outline = (35, 45, 70, 255)
    glass = (12, 18, 32, 255)
    cyan = (0, 242, 234, 255)
    pink = (255, 0, 80, 255)

    cx, cy = w // 2, int(h * 0.56)

    # 头部：更现代的“椭圆胶囊头盔”
    head = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    hd = ImageDraw.Draw(head)
    hx0, hy0, hx1, hy1 = cx - 240, cy - 320, cx + 240, cy + 70
    hd.ellipse((hx0, hy0, hx1, hy1), fill=white, outline=outline, width=10)
    # 内阴影（让壳体更立体）
    inner = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    idr = ImageDraw.Draw(inner)
    idr.ellipse((hx0 + 18, hy0 + 22, hx1 - 18, hy1 - 30), fill=(0, 0, 0, 40))
    inner = inner.filter(ImageFilter.GaussianBlur(radius=10))
    head = Image.alpha_composite(head, inner)
    # 高光
    gloss = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(gloss)
    gd.ellipse((hx0 + 40, hy0 + 40, cx + 40, cy - 60), fill=(255, 255, 255, 95))
    head = Image.alpha_composite(head, gloss.filter(ImageFilter.GaussianBlur(radius=10)))

    # 面罩：黑玻璃（大、圆、现代）
    visor = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    vd = ImageDraw.Draw(visor)
    vx0, vy0, vx1, vy1 = cx - 190, cy - 230, cx + 190, cy - 35
    vd.rounded_rectangle((vx0, vy0, vx1, vy1), radius=90, fill=glass, outline=outline, width=8)
    # 玻璃高光条
    hl = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    hld = ImageDraw.Draw(hl)
    hld.rounded_rectangle((vx0 + 18, vy0 + 18, vx1 - 18, vy0 + 78), radius=50, fill=(255, 255, 255, 38))
    visor = Image.alpha_composite(visor, hl.filter(ImageFilter.GaussianBlur(radius=8)))

    # 眼睛：异色大眼（更可爱）+ 霓虹发光（更科技）/ 眨眼状态（用于动画）
    canvas = Image.alpha_composite(
        canvas, _radial_glow((w, h), (cx - 85, cy - 135), 140, (0, 242, 234, 160))
    )
    canvas = Image.alpha_composite(
        canvas, _radial_glow((w, h), (cx + 85, cy - 135), 140, (255, 0, 80, 150))
    )
    d = ImageDraw.Draw(canvas)
    eyes = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ed = ImageDraw.Draw(eyes)
    if not blink:
        ed.ellipse((cx - 140, cy - 190, cx - 30, cy - 80), fill=(115, 245, 255, 255))
        ed.ellipse((cx + 30, cy - 190, cx + 140, cy - 80), fill=(255, 140, 210, 255))
        # 高光
        ed.ellipse((cx - 110, cy - 175, cx - 85, cy - 150), fill=(255, 255, 255, 235))
        ed.ellipse((cx - 80, cy - 155, cx - 66, cy - 141), fill=(255, 255, 255, 190))
        ed.ellipse((cx + 60, cy - 175, cx + 85, cy - 150), fill=(255, 255, 255, 235))
        ed.ellipse((cx + 90, cy - 155, cx + 104, cy - 141), fill=(255, 255, 255, 190))
    else:
        # 眨眼：用轻微上扬弧线表示闭眼（保留异色）
        ed.arc((cx - 150, cy - 160, cx - 20, cy - 85), start=15, end=165, fill=(0, 242, 234, 255), width=10)
        ed.arc((cx + 20, cy - 160, cx + 150, cy - 85), start=15, end=165, fill=(255, 0, 80, 255), width=10)
        # 小高光点（让闭眼也显得“萌”）
        ed.ellipse((cx - 95, cy - 140, cx - 85, cy - 130), fill=(255, 255, 255, 180))
        ed.ellipse((cx + 85, cy - 140, cx + 95, cy - 130), fill=(255, 255, 255, 180))

    # 微笑（更现代：小弧线）
    mouth = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    md = ImageDraw.Draw(mouth)
    md.arc((cx - 70, cy - 130, cx + 70, cy - 40), start=25, end=155, fill=(230, 240, 255, 210), width=6)

    # 身体：更现代的胶囊躯干 + 胸口“能量核心”
    body = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bd = ImageDraw.Draw(body)
    bx0, by0, bx1, by1 = cx - 190, cy - 5, cx + 190, cy + 255
    bd.rounded_rectangle((bx0, by0, bx1, by1), radius=110, fill=white, outline=outline, width=10)
    # 胸甲
    bd.rounded_rectangle((bx0 + 24, by0 + 30, bx1 - 24, by0 + 150), radius=85, fill=pearl)
    # 能量核心（星形）
    core = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    cd = ImageDraw.Draw(core)
    sx, sy = cx, cy + 72
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rr = 30 if i % 2 == 0 else 13
        pts.append((sx + rr * math.cos(ang), sy + rr * math.sin(ang)))
    cd.polygon(pts, fill=(255, 236, 120, 255), outline=(220, 170, 60, 255))
    core_glow = _radial_glow((w, h), (sx, sy), 120, (255, 220, 120, 120))

    # 腿/脚：更拟人但保持可爱比例（短腿 + 圆润鞋底）
    legs = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ld = ImageDraw.Draw(legs)
    leg_w = 56
    leg_h = 70
    gap = 36
    leg_y0 = by1 - 22
    # 左腿
    lx0 = cx - gap // 2 - leg_w
    lx1 = lx0 + leg_w
    ld.rounded_rectangle((lx0, leg_y0, lx1, leg_y0 + leg_h), radius=22, fill=white, outline=outline, width=6)
    # 右腿
    rx0 = cx + gap // 2
    rx1 = rx0 + leg_w
    ld.rounded_rectangle((rx0, leg_y0, rx1, leg_y0 + leg_h), radius=22, fill=white, outline=outline, width=6)
    # 脚（鞋底）
    foot_w = 96
    foot_h = 46
    fy0 = leg_y0 + leg_h - 6
    ld.rounded_rectangle((lx0 - 20, fy0, lx0 - 20 + foot_w, fy0 + foot_h), radius=22, fill=white, outline=outline, width=6)
    ld.rounded_rectangle((rx1 - foot_w + 20, fy0, rx1 + 20, fy0 + foot_h), radius=22, fill=white, outline=outline, width=6)
    # 鞋底发光条（小科技感）
    ld.rounded_rectangle((lx0 - 8, fy0 + 26, lx0 - 8 + foot_w - 24, fy0 + 38), radius=10, fill=(0, 242, 234, 140))
    ld.rounded_rectangle((rx1 - foot_w + 32, fy0 + 26, rx1 + 8, fy0 + 38), radius=10, fill=(255, 0, 80, 120))

    # 手臂：小人体更“拟人”，但仍然圆润
    arms = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ad = ImageDraw.Draw(arms)
    # 左臂
    ad.rounded_rectangle((bx0 - 70, by0 + 70, bx0 + 10, by0 + 150), radius=40, fill=white, outline=outline, width=8)
    ad.ellipse((bx0 - 95, by0 + 125, bx0 + 25, by0 + 240), fill=white, outline=outline, width=8)
    # 右臂（比赞）
    ad.rounded_rectangle((bx1 - 10, by0 + 70, bx1 + 70, by0 + 150), radius=40, fill=white, outline=outline, width=8)
    ad.ellipse((bx1 - 25, by0 + 125, bx1 + 95, by0 + 240), fill=white, outline=outline, width=8)
    ad.rounded_rectangle((bx1 + 42, by0 + 95, bx1 + 112, by0 + 156), radius=24, fill=white, outline=outline, width=6)
    # 手背指示灯
    ad.ellipse((bx0 - 42, by0 + 172, bx0 - 12, by0 + 202), fill=cyan)
    ad.ellipse((bx1 + 12, by0 + 172, bx1 + 42, by0 + 202), fill=pink)

    # 头顶天线（更科技：小圆点灯）
    antenna = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    at = ImageDraw.Draw(antenna)
    at.line([(cx, hy0 - 10), (cx, hy0 - 70)], fill=outline, width=8)
    at.ellipse((cx - 16, hy0 - 98, cx + 16, hy0 - 66), fill=pink, outline=outline, width=6)
    antenna = Image.alpha_composite(antenna, _radial_glow((w, h), (cx, hy0 - 82), 80, (255, 0, 80, 120)))

    # 悬浮推进器光（更现代科技感）
    thruster = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    td = ImageDraw.Draw(thruster)
    # 有腿后减少“推进器感”，改成更柔和的底部光晕
    td.ellipse((cx - 100, cy + 280, cx + 100, cy + 320), fill=(0, 242, 234, 65))
    thruster = thruster.filter(ImageFilter.GaussianBlur(radius=10))

    # 合成（顺序很关键）
    canvas = Image.alpha_composite(canvas, thruster)
    canvas = Image.alpha_composite(canvas, head)
    canvas = Image.alpha_composite(canvas, antenna)
    canvas = Image.alpha_composite(canvas, visor)
    canvas = Image.alpha_composite(canvas, eyes)
    canvas = Image.alpha_composite(canvas, mouth)
    canvas = Image.alpha_composite(canvas, arms)
    canvas = Image.alpha_composite(canvas, body)
    canvas = Image.alpha_composite(canvas, legs)
    canvas = Image.alpha_composite(canvas, core_glow)
    canvas = Image.alpha_composite(canvas, core)

    # 名牌（可选）
    if show_name:
        tag = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        td2 = ImageDraw.Draw(tag)
        tag_text = "绘宝"
        font = font_manager.get_font("chinese", 70)
        bbox = td2.textbbox((0, 0), tag_text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        pad_x, pad_y = 28, 18
        tx0, ty0 = cx - tw // 2 - pad_x, cy + 300
        tx1, ty1 = cx + tw // 2 + pad_x, cy + 300 + th + pad_y * 2
        td2.rounded_rectangle((tx0, ty0, tx1, ty1), radius=34, fill=(0, 0, 0, 120), outline=(0, 242, 234, 160), width=5)
        td2.text((cx - tw / 2, ty0 + pad_y), tag_text, font=font, fill=(245, 245, 255, 245))
        canvas = Image.alpha_composite(canvas, tag)
    return canvas

def generate_huibao_assets(
    out_path: str,
    out_transparent_path: str | None = None,
    out_blink_transparent_path: str | None = None,
    size=(1024, 1024),
    show_name: bool = True,
):
    """
    同时生成两份：
    - 带背景版本（用于单独展示）
    - 透明版本（用于叠加到封面/品牌图/视频）
    """
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    if out_transparent_path:
        os.makedirs(os.path.dirname(out_transparent_path), exist_ok=True)

    bg = _render_background(size=size)
    # 带背景图默认显示名牌，透明叠加图默认不显示名牌
    robot = _render_robot_layer(size=size, show_name=show_name, blink=False)

    # 带背景版本：额外加一个地面软阴影增强悬浮感
    w, h = size
    cx, cy = w // 2, int(h * 0.56)
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.ellipse((cx - 220, cy + 270, cx + 220, cy + 330), fill=(0, 0, 0, 120))
    final = Image.alpha_composite(bg, shadow.filter(ImageFilter.GaussianBlur(radius=16)))
    final = Image.alpha_composite(final, robot)
    final.convert("RGB").save(out_path, quality=95)

    # 透明版本：直接导出 RGBA（保留发光、透明通道）
    if out_transparent_path:
        robot_overlay = _render_robot_layer(size=size, show_name=False, blink=False)
        robot_overlay.save(out_transparent_path)
    # 透明眨眼版本：用于片头动画（与正常版位置/尺寸一致）
    if out_blink_transparent_path:
        robot_blink = _render_robot_layer(size=size, show_name=False, blink=True)
        robot_blink.save(out_blink_transparent_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="生成平台吉祥物“绘宝”图片（带背景 + 透明叠加版）")
    parser.add_argument("-o", "--out", default="assets/image/mascot_huibao.png", help="输出：带背景版本 PNG 路径")
    parser.add_argument(
        "-p",
        "--out-transparent",
        default="assets/image/mascot_huibao_transparent.png",
        help="输出：透明版本 PNG 路径（用于叠加）",
    )
    parser.add_argument(
        "--out-blink-transparent",
        default="assets/image/mascot_huibao_blink_transparent.png",
        help="输出：透明眨眼版本 PNG 路径（用于片头动画）",
    )
    parser.add_argument("--size", default="1024", help="输出尺寸（正方形边长，例如 1024）")
    parser.add_argument("--show-name", action="store_true", help="带背景版本是否显示“绘宝”名牌（透明版默认不显示）")
    args = parser.parse_args()

    side = int(args.size)
    generate_huibao_assets(
        out_path=args.out,
        out_transparent_path=args.out_transparent,
        out_blink_transparent_path=args.out_blink_transparent,
        size=(side, side),
        show_name=bool(args.show_name),
    )


