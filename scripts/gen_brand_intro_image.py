import os
import sys
import colorsys
import argparse
from collections import Counter
from PIL import Image, ImageDraw, ImageFilter

# 允许脚本从项目根目录直接运行
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from steps.image.font import font_manager


def _rounded_rect(draw: ImageDraw.ImageDraw, xy, radius: int, fill):
    draw.rounded_rectangle(xy, radius=radius, fill=fill)


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _rgb_tuple(rgb) -> tuple[int, int, int]:
    r, g, b = rgb
    return int(r), int(g), int(b)


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = _clamp(t)
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def _adjust_sv(rgb: tuple[int, int, int], s_mul: float = 1.0, v_mul: float = 1.0) -> tuple[int, int, int]:
    r, g, b = [c / 255.0 for c in rgb]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    s = _clamp(s * s_mul)
    v = _clamp(v * v_mul)
    rr, gg, bb = colorsys.hsv_to_rgb(h, s, v)
    return int(rr * 255), int(gg * 255), int(bb * 255)


def _linear_gradient(size: tuple[int, int], c1: tuple[int, int, int], c2: tuple[int, int, int], horizontal: bool = True) -> Image.Image:
    """生成简单线性渐变（RGB）。"""
    w, h = size
    img = Image.new("RGB", (w, h), c1)
    draw = ImageDraw.Draw(img)
    steps = w if horizontal else h
    if steps <= 1:
        return img
    for i in range(steps):
        t = i / (steps - 1)
        c = _mix(c1, c2, t)
        if horizontal:
            draw.line([(i, 0), (i, h)], fill=c)
        else:
            draw.line([(0, i), (w, i)], fill=c)
    return img


def _paste_with_rounded_mask(base: Image.Image, overlay: Image.Image, box: tuple[int, int, int, int], radius: int):
    """将 overlay 以圆角 mask 贴到 base 的 box 区域。"""
    x0, y0, x1, y1 = box
    ow, oh = x1 - x0, y1 - y0
    overlay = overlay.resize((ow, oh))
    mask = Image.new("L", (ow, oh), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.rounded_rectangle((0, 0, ow, oh), radius=radius, fill=255)
    base.paste(overlay, (x0, y0), mask)

def _alpha_glow(overlay_rgba: Image.Image, glow_color: tuple[int, int, int], blur: int = 18, strength: int = 180) -> Image.Image:
    """
    根据 overlay 的 alpha 生成彩色发光层，用于“抖音风”霓虹描边/光晕。
    - glow_color: (r,g,b)
    - strength: 0-255，越大越亮
    """
    ov = overlay_rgba.convert("RGBA")
    a = ov.split()[-1]
    glow = Image.new("RGBA", ov.size, (*glow_color, 0))
    glow.putalpha(a.point(lambda x: int(x * (strength / 255.0))))
    return glow.filter(ImageFilter.GaussianBlur(radius=blur))


def _pick_accent_colors(img_rgba: Image.Image) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    """
    从 logo 图里挑两个“更适合做 UI 配色”的颜色：
    - accent：按钮/高亮用（更饱和）
    - text_accent：标题/点缀用（更深/更稳）
    """
    img = img_rgba.convert("RGB").resize((128, 128))
    pixels = list(img.getdata())

    # 过滤掉接近白/灰/黑的像素（避免被大面积背景主导）
    filtered = []
    for r, g, b in pixels:
        mx, mn = max(r, g, b), min(r, g, b)
        if mx < 40:  # 太黑
            continue
        if mx > 245 and (mx - mn) < 18:  # 近白且近灰
            continue
        # 量化，降低颜色种类
        q = (r // 16 * 16, g // 16 * 16, b // 16 * 16)
        filtered.append(q)

    if not filtered:
        # 回退：保留原先粉色系
        return (255, 105, 180), (70, 60, 80)

    counts = Counter(filtered)
    # 取 Top N 并按“更适合当强调色”的评分排序
    candidates = [c for c, _ in counts.most_common(30)]

    def score(rgb):
        r, g, b = [x / 255.0 for x in rgb]
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        # 偏好：中高饱和 + 不太暗 + 稍亮
        return (s * 1.6 + v * 0.6) * (0.6 + 0.4 * (v))

    # 先按“色彩适合度”排序，再挑第一个满足阈值的（避免挑到偏灰/偏米黄导致按钮不够醒目）
    candidates.sort(key=score, reverse=True)
    accent = None
    for rgb in candidates[:12]:
        r, g, b = [x / 255.0 for x in rgb]
        _, s, v = colorsys.rgb_to_hsv(r, g, b)
        if s >= 0.45 and v >= 0.45:
            accent = _rgb_tuple(rgb)
            break
    if accent is None:
        accent = _rgb_tuple(candidates[0])
    # 文本强调色：用 accent 稍微“压暗 + 降饱和”更耐看
    text_accent = _adjust_sv(accent, s_mul=0.75, v_mul=0.55)
    return accent, text_accent


def generate_brand_intro(
    logo_path: str,
    out_path: str,
    size: tuple[int, int] = (1080, 1920),
    brand_name: str = "智绘童梦",
    handle_text: str = "抖音：@智绘童梦",
    slogan: str = "每天更新｜成语｜绘本｜英语 | 历史",
    cta: str = "关注不迷路",
    mascot_path: str | None = None,
):
    w, h = size
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    logo = Image.open(logo_path).convert("RGBA")
    accent, text_accent = _pick_accent_colors(logo)
    # 抖音经典霓虹色（青蓝 + 玫红），在不破坏品牌色的前提下增强“抖音感”
    douyin_cyan = (0, 242, 234)
    douyin_pink = (255, 0, 80)
    btn_left = _mix(douyin_cyan, accent, 0.20)
    btn_right = _mix(douyin_pink, accent, 0.20)
    slogan_color = _mix(_adjust_sv(accent, s_mul=0.55, v_mul=0.95), (255, 255, 255), 0.35)
    title_color = _mix(text_accent, (245, 245, 255), 0.15)

    # 背景：用 logo 放大做模糊底图，配合轻微渐变遮罩，保证文字可读
    bg = logo.copy()
    bg = bg.resize((w, w))
    bg = bg.crop((0, 0, w, w))
    bg = bg.resize((w, h))
    bg = bg.filter(ImageFilter.GaussianBlur(radius=18))

    # 抖音风：压暗背景，提高前景对比度（更抓眼）
    dark = Image.new("RGBA", (w, h), (0, 0, 0, 110))
    fog = Image.new("RGBA", (w, h), (255, 255, 255, 25))
    canvas = Image.alpha_composite(bg, dark)
    canvas = Image.alpha_composite(canvas, fog)

    # 主视觉：logo 原图（不裁剪），放到上半部分
    hero_w = int(w * 0.92)
    hero = logo.copy()
    hero = hero.resize((hero_w, hero_w))
    hero_x = (w - hero_w) // 2
    hero_y = int(h * 0.10)
    # 霓虹描边框（抖音风），让主视觉更“封面化”
    frame_pad = 18
    frame_box = (
        hero_x - frame_pad,
        hero_y - frame_pad,
        hero_x + hero_w + frame_pad,
        hero_y + hero_w + frame_pad,
    )
    frame = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    grad = _linear_gradient(
        (frame_box[2] - frame_box[0], frame_box[3] - frame_box[1]),
        btn_left,
        btn_right,
        horizontal=True,
    ).convert("RGBA")
    _paste_with_rounded_mask(frame, grad, frame_box, radius=30)
    frame = frame.filter(ImageFilter.GaussianBlur(radius=2))
    canvas = Image.alpha_composite(canvas, frame)

    inner = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    idraw = ImageDraw.Draw(inner)
    idraw.rounded_rectangle(
        (frame_box[0] + 8, frame_box[1] + 8, frame_box[2] - 8, frame_box[3] - 8),
        radius=26,
        fill=(0, 0, 0, 70),
    )
    canvas = Image.alpha_composite(canvas, inner)
    canvas.paste(hero, (hero_x, hero_y), hero)

    draw = ImageDraw.Draw(canvas)

    # 底部信息面板
    panel_h = int(h * 0.22)
    panel_y0 = h - panel_h - int(h * 0.06)
    panel_x0 = int(w * 0.06)
    panel_x1 = w - panel_x0
    panel_y1 = panel_y0 + panel_h

    panel = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    panel_draw = ImageDraw.Draw(panel)
    # 抖音风信息卡：黑色半透明 + 霓虹双层描边
    _rounded_rect(panel_draw, (panel_x0, panel_y0, panel_x1, panel_y1), radius=26, fill=(0, 0, 0, 150))
    border = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(border)
    bdraw.rounded_rectangle((panel_x0, panel_y0, panel_x1, panel_y1), radius=26, outline=(*btn_left, 200), width=4)
    bdraw.rounded_rectangle((panel_x0 + 6, panel_y0 + 6, panel_x1 - 6, panel_y1 - 6), radius=22, outline=(*btn_right, 170), width=3)

    # 轻微阴影
    shadow = panel.filter(ImageFilter.GaussianBlur(radius=8))
    canvas = Image.alpha_composite(canvas, shadow)
    canvas = Image.alpha_composite(canvas, panel)
    canvas = Image.alpha_composite(canvas, border)
    draw = ImageDraw.Draw(canvas)

    # 可选：叠加“绘宝”（透明 PNG），让品牌页更有记忆点
    if mascot_path:
        try:
            mascot = Image.open(mascot_path).convert("RGBA")
            # 尺寸：按宽度比例缩放，避免压住主要文案
            mw = int(w * 0.42)
            mh = int(mascot.height * (mw / mascot.width))
            mascot = mascot.resize((mw, mh))

            # 放置在右下偏中位置：略微压住面板边框，形成“跳出来”的感觉
            mx = w - mw - int(w * 0.06)
            my = panel_y0 - mh + int(h * 0.10)

            # 霓虹发光（青+粉叠加，抖音感更强）
            glow_cyan = _alpha_glow(mascot, (0, 242, 234), blur=22, strength=190)
            glow_pink = _alpha_glow(mascot, (255, 0, 80), blur=26, strength=160)

            layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            layer.paste(glow_cyan, (mx, my), glow_cyan)
            layer.paste(glow_pink, (mx, my), glow_pink)
            canvas = Image.alpha_composite(canvas, layer)
            canvas.paste(mascot, (mx, my), mascot)
            draw = ImageDraw.Draw(canvas)
        except Exception:
            # 出错时不阻断主流程（例如找不到文件）
            pass

    # 文案排版
    font_title = font_manager.get_font("chinese", 72)
    font_sub = font_manager.get_font("chinese", 42)
    font_small = font_manager.get_font("chinese", 36)

    # 标题
    title = brand_name
    bbox = draw.textbbox((0, 0), title, font=font_title)
    title_w = bbox[2] - bbox[0]
    title_x = panel_x0 + 32
    title_y = panel_y0 + 26
    draw.text((title_x, title_y), title, font=font_title, fill=(*title_color, 255))

    # 账号
    bbox_h = draw.textbbox((0, 0), handle_text, font=font_small)
    handle_y = title_y + (bbox[3] - bbox[1]) + 18
    draw.text((title_x, handle_y), handle_text, font=font_small, fill=(220, 220, 220, 235))

    # slogan
    slogan_y = handle_y + (bbox_h[3] - bbox_h[1]) + 14
    draw.text((title_x, slogan_y), slogan, font=font_sub, fill=(*slogan_color, 255))

    # CTA 按钮
    btn_w = int(w * 0.28)
    btn_h = 64
    btn_x1 = panel_x1 - 28
    btn_x0 = btn_x1 - btn_w
    btn_y1 = panel_y1 - 26
    btn_y0 = btn_y1 - btn_h

    # CTA：霓虹渐变 + 发光（抖音风）
    btn = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    grad_btn = _linear_gradient((btn_w, btn_h), btn_left, btn_right, horizontal=True).convert("RGBA")
    _paste_with_rounded_mask(btn, grad_btn, (btn_x0, btn_y0, btn_x1, btn_y1), radius=32)
    glow = btn.filter(ImageFilter.GaussianBlur(radius=10))
    canvas = Image.alpha_composite(canvas, glow)
    canvas = Image.alpha_composite(canvas, btn)
    draw = ImageDraw.Draw(canvas)

    font_btn = font_manager.get_font("chinese", 38)
    bbox_b = draw.textbbox((0, 0), cta, font=font_btn)
    bw = bbox_b[2] - bbox_b[0]
    bh = bbox_b[3] - bbox_b[1]
    draw.text(
        (btn_x0 + (btn_w - bw) / 2, btn_y0 + (btn_h - bh) / 2 - 2),
        cta,
        font=font_btn,
        fill=(255, 255, 255, 255),
    )

    # 顶部轻提示（可选：让“开始/系列感”更强）
    # 说明：emoji 在部分字体/渲染环境下会变成方块，默认用符号心形保证可显示
    tip = "每天更新, 记得关注哦~"
    font_tip = font_manager.get_font("chinese", 34)
    bbox_t = draw.textbbox((0, 0), tip, font=font_tip)
    tw = bbox_t[2] - bbox_t[0]
    th = bbox_t[3] - bbox_t[1]
    tip_x = (w - tw) / 2
    tip_y = int(h * 0.04)
    # 小条形底
    pad_x, pad_y = 18, 10
    tip_bg = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    tip_draw = ImageDraw.Draw(tip_bg)
    # tip 底色随强调色略微变化（更协调）
    tip_bg_color = _adjust_sv(text_accent, s_mul=1.1, v_mul=0.65)
    _rounded_rect(
        tip_draw,
        (tip_x - pad_x, tip_y - pad_y, tip_x + tw + pad_x, tip_y + th + pad_y),
        radius=22,
        fill=(*tip_bg_color, 90),
    )
    canvas = Image.alpha_composite(canvas, tip_bg)
    draw = ImageDraw.Draw(canvas)
    draw.text((tip_x, tip_y), tip, font=font_tip, fill=(255, 255, 255, 235))

    canvas.convert("RGB").save(out_path, quality=95)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="生成抖音风品牌片头图（可选叠加绘宝吉祥物）")
    parser.add_argument("--logo", default="assets/image/logo.png", help="logo 路径（RGBA）")
    parser.add_argument("--out", default="assets/image/brand_intro.png", help="输出图片路径")
    parser.add_argument("--brand-name", default="智绘童梦", help="品牌名")
    parser.add_argument("--handle-text", default="抖音：@智绘童梦", help="账号文案")
    parser.add_argument("--slogan", default="每天更新｜成语｜绘本｜英语 | 历史", help="slogan 文案")
    parser.add_argument("--cta", default="关注不迷路", help="按钮文案")
    parser.add_argument("--mascot", default="", help="可选：绘宝透明 PNG 路径（为空则不叠加）")
    args = parser.parse_args()

    generate_brand_intro(
        logo_path=args.logo,
        out_path=args.out,
        brand_name=args.brand_name,
        handle_text=args.handle_text,
        slogan=args.slogan,
        cta=args.cta,
        mascot_path=(args.mascot or None),
    )

