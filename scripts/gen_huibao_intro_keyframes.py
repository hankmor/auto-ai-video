"""
生成“绘宝片头”分镜脚本与关键帧图片（>=7 张）。

说明：
- 输入：assets/image/huibao.png（应为透明 PNG）
- 输出：output/huibao_intro_keyframes/
  - keyframes/kf_*.png（1080x1980，透明背景）
  - keyframes_preview/kf_*_black.jpg（黑底预览）
  - script.md / script.json

注意：本脚本只做“关键帧/分镜参考”。如果需要更真实的“弯头/手势”，建议提供分层素材或骨骼动画。
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "assets" / "image" / "huibao.png"
OUT_DIR = ROOT / "output" / "huibao_intro_keyframes"
KF_DIR = OUT_DIR / "keyframes"
KF_PREVIEW_DIR = OUT_DIR / "keyframes_preview"

W, H = 1080, 1980


@dataclass
class Keyframe:
    t: float
    name: str
    desc: str
    file: str


@dataclass
class Shot:
    start: float
    end: float
    desc: str
    sfx: str = ""
    voice: str = ""
    keyframes: list[Keyframe] = None


def _ensure_dirs():
    KF_DIR.mkdir(parents=True, exist_ok=True)
    KF_PREVIEW_DIR.mkdir(parents=True, exist_ok=True)


def _alpha_bbox(img: Image.Image, th: int = 8):
    """返回 alpha>th 的 bbox（left, top, right, bottom），无则 None。"""
    rgba = img.convert("RGBA")
    a = rgba.split()[-1]
    return a.point(lambda v: 255 if v > th else 0).getbbox()


def _resize_to_subject_width(img: Image.Image, subject_w_px: int) -> Image.Image:
    """按主体 bbox 宽度缩放到指定像素宽度（保持比例）。"""
    bbox = _alpha_bbox(img)
    if not bbox:
        return img
    x1, y1, x2, y2 = bbox
    bw = max(1, x2 - x1)
    scale = subject_w_px / bw
    nw = max(1, int(round(img.width * scale)))
    nh = max(1, int(round(img.height * scale)))
    return img.resize((nw, nh), resample=Image.Resampling.LANCZOS)


def _find_eye_centroids(img: Image.Image):
    """
    尝试在透明 PNG 中找到“青色眼睛”和“粉色眼睛”的质心（用于画闭眼线）。
    返回 [(x,y), (x,y)] 或 []。
    """
    rgba = img.convert("RGBA")
    px = rgba.load()
    w, h = rgba.size
    acc = []

    # cyan
    sx = sy = cnt = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 50:
                continue
            # 青色：g,b 高且 r 低
            if g > 170 and b > 170 and r < 120:
                sx += x
                sy += y
                cnt += 1
    if cnt > 200:
        acc.append((sx / cnt, sy / cnt))

    # pink
    sx = sy = cnt = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 50:
                continue
            # 粉色：r,b 高，g 中等
            if r > 180 and b > 150 and g > 80:
                sx += x
                sy += y
                cnt += 1
    if cnt > 200:
        acc.append((sx / cnt, sy / cnt))

    return acc


def _draw_blink_lines(img: Image.Image, eye_pts: list[tuple[float, float]]):
    """在给定图片上画“闭眼弧线”（不改变 alpha）。"""
    if len(eye_pts) < 2:
        return img
    out = img.copy().convert("RGBA")
    d = ImageDraw.Draw(out)
    # 线条样式：深灰偏白，避免太突兀
    col = (235, 235, 240, 220)
    for (ex, ey) in eye_pts:
        w = 90
        h = 26
        # 画上弧线
        bbox = (ex - w / 2, ey - h / 2, ex + w / 2, ey + h / 2)
        d.arc(bbox, start=200, end=340, fill=col, width=6)
        # 小睫毛点缀
        d.line((ex - 18, ey + 2, ex - 32, ey - 8), fill=col, width=4)
        d.line((ex + 18, ey + 2, ex + 32, ey - 8), fill=col, width=4)
    return out


def _paste_center(canvas: Image.Image, sprite: Image.Image, center_x: int, center_y: int):
    """把 sprite 以中心点对齐贴到 canvas 上（透明叠加）。"""
    x = int(round(center_x - sprite.width / 2))
    y = int(round(center_y - sprite.height / 2))
    canvas.alpha_composite(sprite, (x, y))


def _render_keyframes() -> tuple[list[Shot], list[Keyframe]]:
    """
    生成 1080x1980 关键帧（透明），并返回分镜数据。

    时间轴（秒）：
    - 0.0~1.0：左侧中部探头 + 眨 2 次
    - 1.0~1.5：停顿
    - 1.5~2.0：嗖的一声从左侧跳入到屏幕中间
    - 2.0~2.2：停顿
    - 2.2~：开始朗读 hook，并做讲解动作（关键帧只给姿态参考）
    """
    _ensure_dirs()

    if not SRC.exists():
        raise FileNotFoundError(f"找不到素材：{SRC}")

    base = Image.open(SRC).convert("RGBA")

    # 目标：人物主体宽度占屏幕 ~60%
    target_subject_w = int(W * 0.60)
    sprite = _resize_to_subject_width(base, target_subject_w)
    eye_pts = _find_eye_centroids(sprite)

    # 计算主体 bbox，便于做“探头裁剪”
    bbox = _alpha_bbox(sprite) or (0, 0, sprite.width, sprite.height)
    x1, y1, x2, y2 = bbox
    bw, bh = (x2 - x1), (y2 - y1)

    # “脑袋”区域：主体上半部分（含脸屏）
    head_crop = (
        int(x1),
        int(y1),
        int(x2),
        int(y1 + bh * 0.60),
    )
    head = sprite.crop(head_crop).convert("RGBA")
    head_eye_pts = _find_eye_centroids(head)

    # 场景位置
    center_x = W // 2
    center_y = int(H * 0.58)

    # 探头位置（左侧中部）
    head_y = int(H * 0.46)
    head_x_end = int(W * 0.22)
    head_x_start = -int(head.width * 0.65)

    # 全身跳入起点/终点
    body_x_start = -int(sprite.width * 0.70)
    body_x_end = center_x
    body_y_end = center_y

    # 关键帧列表（>=7）
    kfs: list[Keyframe] = []

    def save_kf(name: str, t: float, desc: str, canvas: Image.Image):
        path = KF_DIR / f"{name}.png"
        canvas.save(path, format="PNG")
        # 黑底预览
        bg = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        bg.alpha_composite(canvas)
        bg.convert("RGB").save(KF_PREVIEW_DIR / f"{name}_black.jpg", quality=95)
        kfs.append(Keyframe(t=t, name=name, desc=desc, file=str(path.relative_to(OUT_DIR))))

    # KF1：开场（完全隐藏，纯透明）
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    save_kf("kf_01_start_hidden", 0.0, "开场：绘宝完全隐藏在左侧外", c)

    # KF2：探头开始（轻微右歪头）
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    head_pose = head.rotate(12, resample=Image.Resampling.BICUBIC, expand=True)
    hx = int(head_x_start + (head_x_end - head_x_start) * 0.35)
    c.alpha_composite(head_pose, (hx, head_y - head_pose.height // 2))
    save_kf("kf_02_peek_in", 0.35, "探头中：从左侧中部探出一点并右歪头", c)

    # KF3：眨眼 1（闭眼）
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    head_blink = _draw_blink_lines(head_pose, head_eye_pts)
    hx = int(head_x_start + (head_x_end - head_x_start) * 0.70)
    c.alpha_composite(head_blink, (hx, head_y - head_blink.height // 2))
    save_kf("kf_03_blink_1", 0.72, "探头后眨眼（第1次）", c)

    # KF4：眨眼 2（闭眼）
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hx = int(head_x_start + (head_x_end - head_x_start) * 0.92)
    head_blink2 = _draw_blink_lines(head_pose, head_eye_pts)
    c.alpha_composite(head_blink2, (hx, head_y - head_blink2.height // 2))
    save_kf("kf_04_blink_2", 0.90, "探头后眨眼（第2次）", c)

    # KF5：探头结束（停顿前）
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hx = head_x_end
    c.alpha_composite(head_pose, (hx, head_y - head_pose.height // 2))
    save_kf("kf_05_peek_hold", 1.00, "探头结束：脑袋探出并停住（准备停顿0.5s）", c)

    # KF6：跳出中段（嗖的一声，空中）
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    p = 0.55
    bx = int(body_x_start + (body_x_end - body_x_start) * p)
    # 跳跃弧线
    jump = int(H * 0.06)
    by = int(body_y_end - jump * math.sin(math.pi * p))
    _paste_center(c, sprite, bx, by)
    save_kf("kf_06_jump_mid", 1.78, "全身嗖的一声跳出：空中中段", c)

    # KF7：落地站中间（停顿0.2s前）
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    _paste_center(c, sprite, body_x_end, body_y_end)
    save_kf("kf_07_land_center", 2.00, "落地：站立在屏幕中间", c)

    # KF8：讲解姿态（朗读开始，轻微讲解动作参考）
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    talk = sprite.rotate(-3, resample=Image.Resampling.BICUBIC, expand=True)
    _paste_center(c, talk, body_x_end + int(W * 0.01), body_y_end)
    save_kf("kf_08_talk_gesture", 2.20, "朗读开始：讲解姿态（轻微侧摆/点头参考）", c)

    # 分镜脚本
    shots: list[Shot] = [
        Shot(
            start=0.0,
            end=1.0,
            desc="绘宝隐藏在左侧中部→向右歪头探出脑袋→眨巴两下大眼睛（可爱、轻微回弹）。",
            sfx="无",
            voice="无",
            keyframes=[kf for kf in kfs if 0.0 <= kf.t <= 1.0],
        ),
        Shot(
            start=1.0,
            end=1.5,
            desc="停顿 0.5 秒，保持探头姿态（制造期待感）。",
            sfx="无",
            voice="无",
            keyframes=[kf for kf in kfs if 1.0 <= kf.t <= 1.5],
        ),
        Shot(
            start=1.5,
            end=2.0,
            desc="伴随“嗖”的音效，从左侧快速跳出，全身落在屏幕中间站稳。",
            sfx="whoosh（嗖）",
            voice="无",
            keyframes=[kf for kf in kfs if 1.5 <= kf.t <= 2.0],
        ),
        Shot(
            start=2.0,
            end=2.2,
            desc="停顿 0.2 秒：站稳后微微前倾准备讲解。",
            sfx="无",
            voice="无",
            keyframes=[kf for kf in kfs if 2.0 <= kf.t <= 2.2],
        ),
        Shot(
            start=2.2,
            end=6.0,
            desc="开始朗读 hook 文案；绘宝做讲解动作（轻微左右摆动/点头）。若需‘只动手’，建议后续补分层手臂素材。",
            sfx="无（可保留轻微环境音）",
            voice="hook 朗读",
            keyframes=[kf for kf in kfs if kf.t >= 2.2],
        ),
    ]

    return shots, kfs


def _write_script(shots: list[Shot], kfs: list[Keyframe]):
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # script.json
    script = {
        "resolution": [W, H],
        "asset": str(SRC.relative_to(ROOT)),
        "timeline_seconds": {
            "stage1_peek": [0.0, 1.0],
            "stage2_pause": [1.0, 1.5],
            "stage2_jump": [1.5, 2.0],
            "stage3_pause": [2.0, 2.2],
            "stage4_hook_voice": [2.2, 6.0],
        },
        "shots": [
            {
                "start": s.start,
                "end": s.end,
                "desc": s.desc,
                "sfx": s.sfx,
                "voice": s.voice,
                "keyframes": [asdict(k) for k in (s.keyframes or [])],
            }
            for s in shots
        ],
        "keyframes": [asdict(k) for k in kfs],
    }
    (OUT_DIR / "script.json").write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")

    # script.md
    md = []
    md.append("## 绘宝片头分镜脚本（关键帧参考）\\n")
    md.append(f"- **分辨率**：{W}×{H}\\n")
    md.append(f"- **角色素材**：`{SRC.relative_to(ROOT)}`（透明 PNG）\\n")
    md.append(f"- **关键帧目录**：`{KF_DIR.relative_to(ROOT)}`（PNG 透明）\\n")
    md.append(f"- **预览目录**：`{KF_PREVIEW_DIR.relative_to(ROOT)}`（黑底 JPG）\\n")
    md.append("\\n---\\n")

    md.append("## 时间轴\\n")
    md.append("- **0.0–1.0s**：探头 + 眨眼×2\\n")
    md.append("- **1.0–1.5s**：停顿\\n")
    md.append("- **1.5–2.0s**：嗖的一声跳入中间\\n")
    md.append("- **2.0–2.2s**：停顿\\n")
    md.append("- **2.2s 起**：开始朗读 hook + 讲解动作\\n")
    md.append("\\n---\\n")

    md.append("## 分镜\\n")
    for i, s in enumerate(shots, 1):
        md.append(f"### 镜头 {i}（{s.start:.2f}s–{s.end:.2f}s）\\n")
        md.append(f"- **画面**：{s.desc}\\n")
        md.append(f"- **音效**：{s.sfx or '无'}\\n")
        md.append(f"- **语音**：{s.voice or '无'}\\n")
        if s.keyframes:
            md.append("- **关键帧**：\\n")
            for k in s.keyframes:
                md.append(f"  - {k.name} @ {k.t:.2f}s：`{k.file}` —— {k.desc}\\n")
        md.append("\\n")

    (OUT_DIR / "script.md").write_text("".join(md), encoding="utf-8")


def main():
    shots, kfs = _render_keyframes()
    _write_script(shots, kfs)
    print(f"完成：{OUT_DIR}")


if __name__ == "__main__":
    main()


