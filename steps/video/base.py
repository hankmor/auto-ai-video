import os
import numpy as np
import pypinyin
import math
from abc import ABC, abstractmethod
from typing import List, Optional
from PIL import Image, ImageDraw

if not hasattr(Image, "ANTIALIAS"):
    setattr(Image, "ANTIALIAS", Image.LANCZOS)

from moviepy.editor import (
    ImageClip,
    AudioFileClip,
    VideoFileClip,
    VideoClip,
    ColorClip,
    concatenate_videoclips,
    CompositeVideoClip,
    CompositeAudioClip,
)
from moviepy.audio.AudioClip import CompositeAudioClip
import moviepy.audio.fx.all as afx
import moviepy.video.fx.all as vfx
import subprocess

from config.config import config
from model.models import Scene
from util.logger import logger
from steps.image.font import font_manager


class VideoAssemblerBase(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def _compose_scene(
        self, scene: Scene, visual_clip: VideoClip, duration: float
    ) -> VideoClip:
        pass

    def _load_visual(self, scene: Scene, duration: float) -> Optional[VideoClip]:
        if (
            config.ENABLE_ANIMATION
            and scene.video_path
            and os.path.exists(scene.video_path)
        ):
            try:
                v_clip = VideoFileClip(scene.video_path)
                if v_clip.duration < duration:
                    v_clip = vfx.loop(v_clip, duration=duration)
                return v_clip.set_duration(duration)
            except Exception as e:
                logger.error(f"Error loading video {scene.video_path}: {e}")

        if scene.image_path and os.path.exists(scene.image_path):
            try:
                img_clip = ImageClip(scene.image_path)
                return self.apply_ken_burns(img_clip, duration=duration)
            except Exception as e:
                logger.error(f"Error loading image {scene.image_path}: {e}")
                return None
        return None

    def apply_ken_burns(
        self, clip: ImageClip, duration: float, scale_factor: float = 1.15
    ) -> VideoClip:
        w, h = clip.size

        def make_frame(t):
            progress = t / duration
            current_scale = 1.0 + (scale_factor - 1.0) * progress
            crop_w = w / current_scale
            crop_h = h / current_scale
            x1 = (w - crop_w) / 2
            y1 = (h - crop_h) / 2
            frame = clip.get_frame(0)
            img_pil = Image.fromarray(frame)
            img_cropped = img_pil.crop((x1, y1, x1 + crop_w, y1 + crop_h))
            if hasattr(Image, "Resampling"):
                resample_method = Image.Resampling.LANCZOS
            else:
                resample_method = getattr(
                    Image, "LANCZOS", getattr(Image, "ANTIALIAS", 1)
                )
            img_resized = img_cropped.resize((w, h), resample=resample_method)
            return np.array(img_resized)

        return VideoClip(make_frame=make_frame, duration=duration).set_fps(24)

    def create_page_flip_transition(
        self,
        from_image_path: str,
        to_image_path: str,
        duration: float = 0.6,
    ) -> Optional[VideoClip]:
        """
        更真实的“翻书/翻页”转场：从 from_image 翻到 to_image（以左侧为书脊，右侧翻页）。
        实现要点：
        - 页面主体随翻页角度做水平收缩（模拟绕书脊旋转）
        - 页面形状做轻微透视梯形（上下边缘随翻页倾斜）
        - 增加页边高光、背后投影渐变（增强立体感）
        """
        if not from_image_path or not to_image_path:
            return None
        if not os.path.exists(from_image_path) or not os.path.exists(to_image_path):
            return None
        if duration <= 0:
            return None

        try:
            img_page = Image.open(from_image_path).convert("RGBA")
            img_next = Image.open(to_image_path).convert("RGBA")
            if img_page.size != img_next.size:
                img_next = img_next.resize(img_page.size)
            w, h = img_page.size

            # 兼容不同 PIL 版本的 resample 常量
            if hasattr(Image, "Resampling"):
                resample_method = Image.Resampling.LANCZOS
            else:
                resample_method = getattr(Image, "LANCZOS", getattr(Image, "ANTIALIAS", 1))

            def make_frame(t):
                p = 0.0 if duration <= 0 else max(0.0, min(1.0, t / duration))
                theta = p * (math.pi / 2.0)  # 0 -> 90deg
                cos_t = max(0.02, math.cos(theta))
                sin_t = math.sin(theta)

                # 页面可见宽度（以左侧为书脊）
                page_w = max(1, int(w * cos_t))
                # 透视倾斜幅度（越翻越明显）
                skew = int(h * 0.06 * sin_t)

                frame = img_next.copy()

                # 右侧被翻开的区域投影（落在 next 页面上）
                shadow_w = min(140, w - page_w)
                if shadow_w > 0:
                    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                    sdraw = ImageDraw.Draw(shadow)
                    base_alpha = int(140 * sin_t)
                    for i in range(shadow_w):
                        a = int(base_alpha * (1 - i / shadow_w))
                        if a <= 0:
                            continue
                        x = page_w + i
                        sdraw.line([(x, 0), (x, h)], fill=(0, 0, 0, a))
                    frame = Image.alpha_composite(frame, shadow)

                # 页面主体：先水平缩放，再用梯形 mask 做“透视页形”
                page_rect = img_page.resize((page_w, h), resample=resample_method).copy()
                mask = Image.new("L", (page_w, h), 0)
                mdraw = ImageDraw.Draw(mask)
                # 梯形：右边缘上下分别向内偏移 skew
                mdraw.polygon([(0, 0), (page_w, skew), (page_w, h - skew), (0, h)], fill=255)
                page_rect.putalpha(mask)

                # 页边高光（右边缘一条白色渐变）
                hl_w = min(24, page_w)
                if hl_w > 2:
                    highlight = Image.new("RGBA", (page_w, h), (0, 0, 0, 0))
                    hdraw = ImageDraw.Draw(highlight)
                    hl_alpha = int(120 * sin_t)
                    for i in range(hl_w):
                        a = int(hl_alpha * (1 - i / hl_w))
                        x = page_w - 1 - i
                        hdraw.line([(x, 0), (x, h)], fill=(255, 255, 255, a))
                    page_rect = Image.alpha_composite(page_rect, highlight)

                frame.paste(page_rect, (0, 0), page_rect)
                return np.array(frame.convert("RGB"))

            return VideoClip(make_frame=make_frame, duration=duration).set_fps(24)
        except Exception as e:
            logger.warning(f"Failed to create page flip transition: {e}")
            return None

    # 品牌片头已与 Hook Voice 合并：当开启 enable_hook_voice 且有文案时，
    # 将使用 assets/image/brand_intro.png 作为片头画面并播放引导语音。

    def create_brand_outro(self, duration: float = 4.0, platform: str = "general"):
        try:
            logo_path = os.path.join("brand", "logo_gemini_magic_storybook.png")
            if not os.path.exists(logo_path):
                return None
            width, height = config.VIDEO_SIZE
            brand_dir = "brand"
            os.makedirs(brand_dir, exist_ok=True)
            bg_path = os.path.join(brand_dir, "outro_bg.png")
            text_path = os.path.join(brand_dir, f"outro_text_{platform}.png")

            if not os.path.exists(bg_path):
                bg_img = Image.new("RGB", (width, height), (255, 255, 255))
                draw = ImageDraw.Draw(bg_img)
                for y in range(height):
                    ratio = y / height
                    r = int(224 + (255 - 224) * ratio)
                    g = int(247 + (240 - 247) * ratio)
                    b = int(255 + (245 - 255) * ratio)
                    draw.line([(0, y), (width, y)], fill=(r, g, b))
                bg_img.save(bg_path)
            bg_clip = ImageClip(bg_path).set_duration(duration)

            logo_img = ImageClip(logo_path)
            logo_scale = min(width * 0.35 / logo_img.w, height * 0.2 / logo_img.h)
            logo_img = logo_img.resize(logo_scale)
            logo_clip = logo_img.set_position(("center", 200)).set_duration(duration)

            if not os.path.exists(text_path):
                text_img = Image.new("RGBA", (width, 800), (255, 255, 255, 0))
                text_draw = ImageDraw.Draw(text_img)

                font_large = font_manager.get_font("chinese", 80)
                thanks_text = "感谢观看"
                bbox = text_draw.textbbox((0, 0), thanks_text, font=font_large)
                text_draw.text(
                    ((width - (bbox[2] - bbox[0])) // 2, 50),
                    thanks_text,
                    font=font_large,
                    fill=(74, 74, 74),
                )

                font_medium = font_manager.get_font("chinese", 60)
                like_text = "记得点赞关注哦 ❤️"
                bbox = text_draw.textbbox((0, 0), like_text, font=font_medium)
                text_draw.text(
                    ((width - (bbox[2] - bbox[0])) // 2, 180),
                    like_text,
                    font=font_medium,
                    fill=(255, 105, 180),
                )

                font_small = font_manager.get_font("chinese", 45)
                platform_accounts = {
                    "douyin": "抖音: @智绘童梦",
                    "xiaohongshu": "小红书: @智绘童梦",
                    "youtube": "YouTube: @SmartArtKids",
                    "general": "智绘童梦 · 陪伴成长每一刻",
                }
                account_text = platform_accounts.get(
                    platform, platform_accounts["general"]
                )
                bbox = text_draw.textbbox((0, 0), account_text, font=font_small)
                text_draw.text(
                    ((width - (bbox[2] - bbox[0])) // 2, 300),
                    account_text,
                    font=font_small,
                    fill=(100, 100, 100),
                )

                slogan_text = "用智慧为孩子绘制梦想"
                bbox = text_draw.textbbox((0, 0), slogan_text, font=font_small)
                text_draw.text(
                    ((width - (bbox[2] - bbox[0])) // 2, 400),
                    slogan_text,
                    font=font_small,
                    fill=(135, 206, 235),
                )
                text_img.save(text_path)

            text_clip = (
                ImageClip(text_path).set_position((0, 800)).set_duration(duration)
            )
            outro_clip = CompositeVideoClip([bg_clip, logo_clip, text_clip])
            outro_clip = outro_clip.fadein(0.5).fadeout(0.5)
            return outro_clip
        except Exception as e:
            logger.error(f"Failed to create brand outro: {e}")
            return None

    def _is_english_title(self, title: str) -> bool:
        non_space = [c for c in title if c != " "]
        if not non_space:
            return False
        ascii_count = sum(1 for c in non_space if c.isascii() and c.isalpha())
        return ascii_count / len(non_space) > 0.7

    def _generate_cover_english(
        self, image_path: str, title: str, output_path: str, subtitle: str = ""
    ):
        try:
            img = Image.open(image_path).convert("RGBA")
            W, H = img.size
            max_text_width = int(W * 0.85)
            base_size = int(W * 0.08)
            min_size = int(W * 0.04)
            title_size = base_size
            font_title = font_manager.get_font("english", title_size)
            draw = ImageDraw.Draw(img)
            words = title.split()

            def wrap_text(font, max_width):
                lines = []
                current_line = []
                for word in words:
                    test_line = " ".join(current_line + [word])
                    bbox = draw.textbbox((0, 0), test_line, font=font)
                    if bbox[2] - bbox[0] <= max_width:
                        current_line.append(word)
                    else:
                        if current_line:
                            lines.append(" ".join(current_line))
                        current_line = [word]
                if current_line:
                    lines.append(" ".join(current_line))
                return lines

            lines = wrap_text(font_title, max_text_width)
            while len(lines) > 3 and title_size > min_size:
                title_size = int(title_size * 0.85)
                font_title = font_manager.get_font("english", title_size)
                lines = wrap_text(font_title, max_text_width)

            max_lines = 4
            while len(lines) > max_lines and base_size > 20:
                base_size = int(base_size * 0.9)
                font_title = font_manager.get_font("english", base_size)
                lines = wrap_text(font_title, max_text_width)

            line_spacing = int(title_size * 0.3)
            total_block_height = 0
            line_metrics = []
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font_title)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                line_metrics.append({"text": line, "width": w, "height": h})
                total_block_height += h + line_spacing
            total_block_height -= line_spacing

            max_line_width = (
                max(m["width"] for m in line_metrics) if line_metrics else 0
            )
            center_x, center_y = W / 2, H / 2
            subtitle_height = 0
            if subtitle:
                subtitle_height = int(W * 0.05) + 30
                center_y -= subtitle_height / 2
            start_y = center_y - (total_block_height / 2)

            # Draw bg panel
            pad_x, pad_y = int(W * 0.06), int(H * 0.05)
            box_bottom = start_y + total_block_height + pad_y
            if subtitle:
                box_bottom += subtitle_height
            box_coords = [
                center_x - (max_line_width / 2) - pad_x,
                start_y - pad_y,
                center_x + (max_line_width / 2) + pad_x,
                box_bottom,
            ]

            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.rounded_rectangle(box_coords, radius=15, fill=(0, 0, 0, 170))
            img = Image.alpha_composite(img, overlay)
            draw = ImageDraw.Draw(img)

            current_y = start_y
            for metrics in line_metrics:
                x_line = center_x - (metrics["width"] / 2)
                draw.text(
                    (x_line, current_y),
                    metrics["text"],
                    font=font_title,
                    fill=(255, 255, 255, 255),
                    stroke_width=2,
                    stroke_fill=(0, 0, 0, 100),
                )
                current_y += metrics["height"] + line_spacing

            if subtitle:
                font_sub = font_manager.get_font("english", int(W * 0.05))
                bbox_s = draw.textbbox((0, 0), subtitle, font=font_sub)
                w_sub = bbox_s[2] - bbox_s[0]
                draw.text(
                    (center_x - (w_sub / 2), current_y + 20),
                    subtitle,
                    font=font_sub,
                    fill=(255, 215, 0, 255),
                    stroke_width=1,
                    stroke_fill=(0, 0, 0, 100),
                )

            img.save(output_path)
            return True
        except Exception as e:
            logger.error(f"Failed to generate English cover: {e}")
            return False

    def generate_cover(
        self, image_path: str, title: str, output_path: str, subtitle: str = ""
    ):
        if self._is_english_title(title):
            return self._generate_cover_english(
                image_path, title, output_path, subtitle
            )

        try:
            img = Image.open(image_path).convert("RGBA")
            W, H = img.size
            title_size = int(W * 0.12)
            pinyin_size = int(title_size * 0.4)
            spacing = int(H * 0.015)
            font_title = font_manager.get_font("chinese", title_size)
            font_pinyin = font_manager.get_font("chinese", pinyin_size)
            draw = ImageDraw.Draw(img)

            pinyin_list = pypinyin.pinyin(title, style=pypinyin.Style.TONE)
            char_data = []
            total_block_width = 0
            for i, char in enumerate(title):
                bbox_c = draw.textbbox((0, 0), char, font=font_title)
                w_char = bbox_c[2] - bbox_c[0]
                h_char = bbox_c[3] - bbox_c[1]
                p_str = pinyin_list[i][0] if i < len(pinyin_list) else ""
                bbox_p = draw.textbbox((0, 0), p_str, font=font_pinyin)
                w_pin = bbox_p[2] - bbox_p[0]
                h_pin = bbox_p[3] - bbox_p[1]
                cell_width = max(w_char, w_pin)
                char_data.append(
                    {
                        "char": char,
                        "pinyin": p_str,
                        "w_char": w_char,
                        "h_char": h_char,
                        "w_pin": w_pin,
                        "h_pin": h_pin,
                        "cell_width": cell_width,
                    }
                )
                total_block_width += cell_width + 4
            if total_block_width > 0:
                total_block_width -= 4

            max_h_char = (
                max([d["h_char"] for d in char_data]) if char_data else title_size
            )
            max_h_pin = (
                max([d["h_pin"] for d in char_data]) if char_data else pinyin_size
            )
            total_block_height = max_h_pin + spacing + max_h_char

            center_x, center_y = W / 2, H / 2
            subtitle_block_h = 0
            if subtitle:
                subtitle_block_h = int(title_size * 0.45) + spacing + 20
            total_content_height = total_block_height + subtitle_block_h
            start_x = center_x - (total_block_width / 2)
            start_y = center_y - (total_content_height / 2)

            pad_x, pad_y = int(W * 0.05), int(H * 0.04)
            box_coords = [
                start_x - pad_x,
                start_y - pad_y,
                start_x + total_block_width + pad_x,
                start_y + total_content_height + pad_y,
            ]
            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.rectangle(box_coords, fill=(0, 0, 0, 160))
            img = Image.alpha_composite(img, overlay)
            draw = ImageDraw.Draw(img)

            current_x = start_x
            y_pinyin_baseline = start_y
            y_hanzi_baseline = start_y + max_h_pin + spacing

            for item in char_data:
                x_pin = current_x + (item["cell_width"] - item["w_pin"]) / 2
                draw.text(
                    (x_pin, y_pinyin_baseline),
                    item["pinyin"],
                    font=font_pinyin,
                    fill=(200, 200, 200, 255),
                )
                x_char = current_x + (item["cell_width"] - item["w_char"]) / 2
                draw.text(
                    (x_char, y_hanzi_baseline),
                    item["char"],
                    font=font_title,
                    fill=(255, 255, 255, 255),
                    stroke_width=2,
                    stroke_fill=(0, 0, 0, 50),
                )
                current_x += item["cell_width"] + 4

            if subtitle:
                font_sub = font_manager.get_font("chinese", int(title_size * 0.45))
                bbox_s = draw.textbbox((0, 0), subtitle, font=font_sub)
                w_sub = bbox_s[2] - bbox_s[0]
                draw.text(
                    (center_x - (w_sub / 2), start_y + total_block_height + 10),
                    subtitle,
                    font=font_sub,
                    fill=(255, 230, 0, 255),
                    stroke_width=1,
                    stroke_fill=(0, 0, 0, 50),
                )

            img.save(output_path)
            return True
        except Exception as e:
            logger.error(f"Failed to generate cover: {e}")
            return False

    def assemble_video(
        self,
        scenes: List[Scene],
        output_filename: str = "final_video.mp4",
        topic: str = "",
        subtitle: str = "",
        category: str = "",
    ):
        logger.info("Assembling video clips...")
        clips = []
        bgm_start_time = 0.0

        trans_type = "none"
        trans_duration = 0.0
        if (
            category
            and hasattr(config, "CATEGORY_TRANSITIONS")
            and category in config.CATEGORY_TRANSITIONS
        ):
            trans_type = config.CATEGORY_TRANSITIONS[category]
            if trans_type == "crossfade":
                trans_duration = 0.8
            elif trans_type == "crossfade_slow":
                trans_duration = 2.0
        
        # 先选一张可用的图片作为封面背景，同时用于对齐片头图片尺寸
        cover_bg_path = None
        for s in scenes:
            if s.image_path and os.path.exists(s.image_path):
                cover_bg_path = s.image_path
                break

        # Hook Voice 片头（品牌图/黑底 + 引导语音）
        # 说明：如果你希望单独制作片头视频/音频，请在 config.yaml 设置 features.enable_hook_voice=false。
        hook_text = ""
        if hasattr(config, "ENABLE_HOOK_VOICE") and config.ENABLE_HOOK_VOICE:
            if (
                hasattr(config, "CATEGORY_HOOK_VOICE_TEXT")
                and category
                and category in config.CATEGORY_HOOK_VOICE_TEXT
            ):
                hook_text = (config.CATEGORY_HOOK_VOICE_TEXT.get(category) or "").strip()
            if not hook_text and hasattr(config, "HOOK_VOICE_TEXT"):
                hook_text = (config.HOOK_VOICE_TEXT or "").strip()

        hook_intro_added = False
        hook_intro_img_path = None
        if hook_text:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            brand_intro_path = os.path.join(base_dir, "assets", "image", "brand_intro.png")
            if os.path.exists(brand_intro_path):
                try:
                    def _abs_path(p: str) -> str:
                        if not p:
                            return ""
                        return p if os.path.isabs(p) else os.path.join(base_dir, p)

                    def _ease_out_back(x: float) -> float:
                        # 轻微回弹：抖音风“弹入”更有活力
                        c1 = 1.70158
                        c3 = c1 + 1.0
                        return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2

                    def _make_name_tag_img(text: str, w: int, h: int) -> Image.Image:
                        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                        d = ImageDraw.Draw(img)
                        radius = int(min(w, h) * 0.28)
                        # 背景 + 霓虹描边
                        d.rounded_rectangle((0, 0, w, h), radius=radius, fill=(0, 0, 0, 130))
                        d.rounded_rectangle((2, 2, w - 2, h - 2), radius=radius, outline=(0, 242, 234, 180), width=4)
                        font = font_manager.get_font("chinese", int(h * 0.56))
                        bbox = d.textbbox((0, 0), text, font=font)
                        tw = bbox[2] - bbox[0]
                        th = bbox[3] - bbox[1]
                        d.text(((w - tw) / 2, (h - th) / 2 - 2), text, font=font, fill=(245, 245, 255, 240))
                        return img

                    hook_audio_path = os.path.join(config.OUTPUT_DIR, "hook_audio.mp3")
                    hook_text_path = os.path.join(config.OUTPUT_DIR, "hook_audio.txt")

                    need_regen = True
                    if os.path.exists(hook_audio_path) and os.path.exists(hook_text_path):
                        try:
                            old_text = open(hook_text_path, "r", encoding="utf-8").read().strip()
                            need_regen = old_text != hook_text
                        except Exception:
                            need_regen = True

                    if need_regen:
                        cmd_hook = [
                            "edge-tts",
                            "--text",
                            hook_text,
                            "--write-media",
                            hook_audio_path,
                            "--voice",
                            config.TTS_VOICE_TITLE,
                        ]
                        subprocess.run(
                            cmd_hook,
                            check=True,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                        with open(hook_text_path, "w", encoding="utf-8") as f:
                            f.write(hook_text)

                    if os.path.exists(hook_audio_path):
                        hook_audio_clip = AudioFileClip(hook_audio_path)
                        # 片头时间轴：默认留一点前后静音，但如果启用“绘宝分段出场”，则让朗读从第 3 段开始
                        silence_pre, silence_post = 0.2, 0.4
                        audio_start = silence_pre
                        intro_duration = max(hook_audio_clip.duration + audio_start + silence_post, 1.2)
                        # 背景：brand（brand_intro.png）或 black（纯黑）
                        bg_mode = str(getattr(config, "HOOK_INTRO_BG_MODE", "brand") or "brand").lower().strip()
                        intro_bg = None
                        # 尽量与后续画面尺寸一致，减少 compose 黑边
                        target_size = None
                        if cover_bg_path and os.path.exists(cover_bg_path):
                            try:
                                target_size = Image.open(cover_bg_path).size
                            except Exception:
                                target_size = None
                        if bg_mode == "black":
                            if target_size:
                                intro_bg = ColorClip(size=target_size, color=(0, 0, 0)).set_duration(intro_duration)
                            else:
                                # 兼容：部分配置未提供 VIDEO_SIZE 时，给一个安全默认值（竖屏 9:16）
                                fallback_size = getattr(config, "VIDEO_SIZE", (1080, 1920))
                                intro_bg = ColorClip(size=fallback_size, color=(0, 0, 0)).set_duration(intro_duration)
                        else:
                            intro_img = ImageClip(brand_intro_path)
                            if target_size:
                                try:
                                    intro_img = intro_img.resize(target_size)
                                except Exception:
                                    pass
                            intro_bg = intro_img.set_duration(intro_duration)

                        # 在背景上叠加“绘宝”动画（弹入 + 漂浮 + 眨眼）
                        intro_clip = intro_bg
                        try:
                            if hasattr(config, "ENABLE_MASCOT_INTRO") and config.ENABLE_MASCOT_INTRO:
                                mascot_path = _abs_path(getattr(config, "MASCOT_INTRO_PATH", ""))
                                blink_path = _abs_path(getattr(config, "MASCOT_INTRO_BLINK_PATH", ""))
                                if mascot_path and os.path.exists(mascot_path):
                                    logger.info(f"🎭 绘宝片头：已启用，素材路径={mascot_path}")
                                    W, H = intro_bg.size

                                    # -------- 分段时间轴参数（按你的需求给默认值，可在 config.yaml 覆盖）--------
                                    stage1_dur = max(0.2, float(getattr(config, "MASCOT_STAGE1_DUR", 1.0) or 1.0))
                                    stage1_blinks = max(0, int(getattr(config, "MASCOT_STAGE1_BLINKS", 2) or 2))
                                    stage1_blink_dur = max(0.04, float(getattr(config, "MASCOT_STAGE1_BLINK_DUR", 0.10) or 0.10))
                                    stage2_pause = max(0.0, float(getattr(config, "MASCOT_STAGE2_PAUSE", 0.5) or 0.5))
                                    stage2_dur = max(0.2, float(getattr(config, "MASCOT_STAGE2_DUR", 0.6) or 0.6))
                                    stage2_jump = max(0.0, float(getattr(config, "MASCOT_STAGE2_JUMP", 0.10) or 0.10))
                                    stage3_pause = max(0.0, float(getattr(config, "MASCOT_STAGE3_PAUSE", 0.2) or 0.2))

                                    # 朗读开始时间：第 3 段开始
                                    audio_start = stage1_dur + stage2_pause + stage2_dur + stage3_pause
                                    logger.info(
                                        f"🎭 绘宝片头时间轴：探头={stage1_dur:.2f}s，停顿={stage2_pause:.2f}s，跳入={stage2_dur:.2f}s，停顿={stage3_pause:.2f}s，朗读开始={audio_start:.2f}s"
                                    )
                                    intro_duration = max(audio_start + hook_audio_clip.duration + silence_post, 1.2)
                                    intro_bg = intro_bg.set_duration(intro_duration)

                                    # -------- 素材加载（全身 & 眨眼）--------
                                    mascot_img = Image.open(mascot_path).convert("RGBA")
                                    blink_img = None
                                    if blink_path and os.path.exists(blink_path):
                                        try:
                                            blink_img = Image.open(blink_path).convert("RGBA")
                                        except Exception:
                                            blink_img = None

                                    # -------- 第 1 段：从左侧中部弹出“脑袋”+ 眨巴两下（1s）--------
                                    head_crop = getattr(config, "MASCOT_HEAD_CROP", [0.10, 0.02, 0.78, 0.60])
                                    if not (isinstance(head_crop, (list, tuple)) and len(head_crop) == 4):
                                        head_crop = [0.10, 0.02, 0.78, 0.60]
                                    hx, hy, hw, hh = head_crop
                                    iW, iH = mascot_img.size
                                    # 判断是比例还是像素
                                    if max(hx, hy, hw, hh) <= 1.0:
                                        x1 = int(iW * float(hx))
                                        y1 = int(iH * float(hy))
                                        x2 = int(iW * float(hx + hw))
                                        y2 = int(iH * float(hy + hh))
                                    else:
                                        x1 = int(hx)
                                        y1 = int(hy)
                                        x2 = int(hx + hw)
                                        y2 = int(hy + hh)
                                    x1 = max(0, min(iW - 1, x1))
                                    y1 = max(0, min(iH - 1, y1))
                                    x2 = max(x1 + 2, min(iW, x2))
                                    y2 = max(y1 + 2, min(iH, y2))

                                    head_img = mascot_img.crop((x1, y1, x2, y2))
                                    head_blink_img = None
                                    if blink_img is not None:
                                        head_blink_img = blink_img.crop((x1, y1, x2, y2))

                                    head_scale = float(getattr(config, "MASCOT_HEAD_SCALE", 0.40) or 0.40)
                                    head_clip = ImageClip(np.array(head_img)).set_duration(stage1_dur)
                                    head_clip = head_clip.resize(width=int(W * head_scale))
                                    hW, hH = head_clip.size

                                    head_x_r = float(getattr(config, "MASCOT_HEAD_X", 0.06) or 0.06)
                                    head_y_r = float(getattr(config, "MASCOT_HEAD_Y", 0.36) or 0.36)
                                    head_target_x = int(W * head_x_r) if head_x_r <= 1.0 else int(head_x_r)
                                    head_target_y = int(H * head_y_r) if head_y_r <= 1.0 else int(head_y_r)
                                    head_start_x = -hW - int(W * 0.06)
                                    # 从左侧中部探头：y 与目标保持一致，避免“先出现在左上角再移动”的观感
                                    head_start_y = head_target_y

                                    def head_pos(t: float):
                                        p = max(0.0, min(1.0, t / max(0.001, stage1_dur)))
                                        e = _ease_out_back(p)
                                        x = head_start_x + (head_target_x - head_start_x) * e
                                        y = head_start_y + (head_target_y - head_start_y) * e
                                        return (int(x), int(y))

                                    # 眨眼实现：避免使用 set_opacity(函数)（部分 moviepy 版本会报 function*float）
                                    # 改为“分段拼接”：正常帧/眨眼帧按时间切片串起来，并用全局时间驱动位置函数，保证运动连续。
                                    head_segments = []
                                    blink_windows = []
                                    if head_blink_img is not None and stage1_blinks > 0:
                                        for i in range(stage1_blinks):
                                            center = (i + 1) * stage1_dur / (stage1_blinks + 1)
                                            start = max(0.0, center - stage1_blink_dur / 2.0)
                                            end = min(stage1_dur, center + stage1_blink_dur / 2.0)
                                            if end > start:
                                                blink_windows.append((start, end))

                                    def _is_blink(seg_t0: float, seg_t1: float) -> bool:
                                        for a, b in blink_windows:
                                            if abs(seg_t0 - a) < 1e-6 and abs(seg_t1 - b) < 1e-6:
                                                return True
                                        return False

                                    # 生成不重叠的时间切片：[0..]，眨眼窗口优先
                                    cut_points = [0.0, stage1_dur]
                                    for a, b in blink_windows:
                                        cut_points.extend([a, b])
                                    cut_points = sorted(set([max(0.0, min(stage1_dur, float(x))) for x in cut_points]))

                                    for t0, t1 in zip(cut_points[:-1], cut_points[1:]):
                                        seg_dur = t1 - t0
                                        if seg_dur <= 1e-6:
                                            continue
                                        use_blink = _is_blink(t0, t1)
                                        seg_img = head_blink_img if (use_blink and head_blink_img is not None) else head_img
                                        seg_clip = ImageClip(np.array(seg_img)).set_duration(seg_dur)
                                        seg_clip = seg_clip.resize(width=hW)
                                        seg_clip = seg_clip.set_position(lambda t, off=t0: head_pos(t + off))
                                        head_segments.append(seg_clip)

                                    # 如果没有任何切片（极端情况），至少放一个正常头部
                                    if not head_segments:
                                        head_segments = [
                                            ImageClip(np.array(head_img))
                                            .set_duration(stage1_dur)
                                            .resize(width=hW)
                                            .set_position(head_pos)
                                        ]

                                    head_timeline = concatenate_videoclips(head_segments, method="compose")
                                    head_timeline = head_timeline.set_start(0).set_end(stage1_dur)

                                    # -------- 第 2 段：停 0.5s 后从左侧跳出，全身站到屏幕中间 --------
                                    body_scale = float(getattr(config, "MASCOT_INTRO_SCALE", 0.42) or 0.42)
                                    # 用已加载的 RGBA 图像数组创建 clip，避免不同环境下读取文件导致透明通道/遮罩异常
                                    body_clip = ImageClip(np.array(mascot_img)).set_duration(intro_duration)
                                    body_clip = body_clip.resize(width=int(W * body_scale))
                                    mW, mH = body_clip.size

                                    body_start = stage1_dur + stage2_pause
                                    body_end = intro_duration
                                    # 目标：屏幕中间站立（按中心点对齐）
                                    center_y_r = float(getattr(config, "MASCOT_BODY_CENTER_Y", 0.58) or 0.58)
                                    body_target_x = int((W - mW) / 2)
                                    body_target_y = int(H * center_y_r - mH / 2)
                                    body_start_x = -mW - int(W * 0.08)
                                    body_start_y = int(H * 0.55 - mH / 2)
                                    jump_h = int(H * stage2_jump)

                                    # 讲解动作：从朗读开始后才启用
                                    # 注意：当前 moviepy 版本的 vfx.rotate 对“随时间变化的角度函数”兼容性不好，
                                    # 会触发 `unsupported operand type(s) for *: 'function' and 'float'`。
                                    # 因此这里用“左右轻移 + 上下轻摆”来表现讲解动作（更稳、更可控）。
                                    gesture_rot = float(getattr(config, "MASCOT_GESTURE_ROT_DEG", 6.0) or 0.0)
                                    gesture_freq = float(getattr(config, "MASCOT_GESTURE_FREQ", 2.0) or 0.0)
                                    gesture_shift = float(getattr(config, "MASCOT_GESTURE_SHIFT", 0.008) or 0.0) * W
                                    gesture_bob = float(getattr(config, "MASCOT_GESTURE_BOB", 0.006) or 0.0) * H
                                    gesture_local_start = max(0.0, audio_start - body_start)

                                    def body_pos(t: float):
                                        # t 为 body_clip 的局部时间（从 body_start 开始）
                                        if t < 0:
                                            return (body_start_x, body_start_y)
                                        if t <= stage2_dur:
                                            p = max(0.0, min(1.0, t / stage2_dur))
                                            # 这里不要用 back-ease（会过冲，容易看起来“跳出来不对/发飘”）
                                            e = 1 - (1 - p) ** 3
                                            x = body_start_x + (body_target_x - body_start_x) * e
                                            y = body_start_y + (body_target_y - body_start_y) * e
                                            # 跳跃弧线：中间最高
                                            if jump_h > 0:
                                                y -= int(jump_h * math.sin(math.pi * p))
                                            return (int(x), int(y))
                                        # 到位后保持站立；朗读时轻微左右移动作为“讲解动作”
                                        x = body_target_x
                                        y = body_target_y
                                        if t >= gesture_local_start:
                                            if gesture_shift:
                                                x += int(
                                                    gesture_shift
                                                    * math.sin(
                                                        2
                                                        * math.pi
                                                        * gesture_freq
                                                        * (t - gesture_local_start)
                                                    )
                                                )
                                            if gesture_bob:
                                                y += int(
                                                    gesture_bob
                                                    * math.sin(
                                                        2
                                                        * math.pi
                                                        * gesture_freq
                                                        * (t - gesture_local_start)
                                                        + math.pi / 2
                                                    )
                                                )
                                        return (int(x), int(y))

                                    body_anim = body_clip.set_start(body_start).set_end(body_end)
                                    body_anim = body_anim.set_position(lambda t: body_pos(t - body_start))
                                    # 保留参数以便后续升级到“手臂分层/多帧手势”时使用；当前不做动态旋转，避免兼容性问题
                                    _ = gesture_rot

                                    # 合成：背景 + 头(第1段) + 身体(第2/3段)
                                    layers = [intro_bg, head_timeline, body_anim]
                                    intro_clip = CompositeVideoClip(layers, size=intro_bg.size).set_duration(intro_duration)
                                else:
                                    logger.warning(f"🎭 绘宝片头：已启用但素材不存在，将跳过。路径={mascot_path}")
                        except Exception as e:
                            logger.warning(f"Failed to add mascot intro animation: {e}")

                        # 音频：开头语音 + 可选入场音效（whoosh）
                        audio_layers = [hook_audio_clip.set_start(audio_start)]
                        try:
                            sfx_path = _abs_path(str(getattr(config, "HOOK_INTRO_SFX_PATH", "") or "").strip())
                            if sfx_path and os.path.exists(sfx_path):
                                sfx_start = float(getattr(config, "HOOK_INTRO_SFX_START", 0.22) or 0.0)
                                sfx_vol = float(getattr(config, "HOOK_INTRO_SFX_VOLUME", 0.5) or 0.5)
                                trim_s = float(getattr(config, "HOOK_INTRO_SFX_TRIM_START", 0.0) or 0.0)
                                trim_e = float(getattr(config, "HOOK_INTRO_SFX_TRIM_END", 0.0) or 0.0)
                                fade_in = float(getattr(config, "HOOK_INTRO_SFX_FADE_IN", 0.0) or 0.0)
                                fade_out = float(getattr(config, "HOOK_INTRO_SFX_FADE_OUT", 0.0) or 0.0)

                                sfx_clip = AudioFileClip(sfx_path)
                                # 裁剪：用中后段更“轻”，避免起音过刺
                                if trim_s > 0 or trim_e > 0:
                                    start_t = max(0.0, trim_s)
                                    end_t = trim_e if trim_e and trim_e > start_t else None
                                    try:
                                        sfx_clip = sfx_clip.subclip(start_t, end_t)
                                    except Exception:
                                        # 裁剪失败则回退为原始音效
                                        pass

                                # 淡入淡出：让音效更自然
                                if fade_in > 0:
                                    sfx_clip = afx.audio_fadein(sfx_clip, fade_in)
                                if fade_out > 0:
                                    sfx_clip = afx.audio_fadeout(sfx_clip, fade_out)

                                sfx_clip = sfx_clip.volumex(max(0.0, min(2.0, sfx_vol))).set_start(sfx_start)
                                audio_layers.append(sfx_clip)
                        except Exception as e:
                            logger.warning(f"Failed to add hook intro sfx: {e}")
                        intro_audio = CompositeAudioClip(audio_layers)
                        intro_clip = intro_clip.set_audio(intro_audio)
                        clips.append(intro_clip)
                        bgm_start_time += intro_duration
                        hook_intro_added = True
                        # 关键：hook 结束后会插入 pause + flip 转场，这里必须与 bg_mode 保持一致。
                        # 否则即使黑底片头，也会在朗读结束后“跳出品牌图”（你现在看到的问题）。
                        if bg_mode == "black":
                            try:
                                # 生成一张黑色占位图，供 pause/flip 使用（避免引用 brand_intro.png）
                                w, h = intro_bg.size
                                hook_intro_img_path = os.path.join(config.OUTPUT_DIR, "hook_intro_black.png")
                                if not os.path.exists(hook_intro_img_path):
                                    Image.new("RGB", (int(w), int(h)), (0, 0, 0)).save(hook_intro_img_path)
                            except Exception as e:
                                logger.warning(f"生成黑色片头占位图失败，将跳过 pause/flip：{e}")
                                hook_intro_img_path = None
                        else:
                            hook_intro_img_path = brand_intro_path
                except Exception as e:
                    logger.warning(f"Failed to add hook intro: {e}")

        if topic and cover_bg_path:
            cover_path = os.path.join(config.OUTPUT_DIR, "cover.png")
            if self.generate_cover(cover_bg_path, topic, cover_path, subtitle=subtitle):
                # Title Audio Logic (CLI Fallback for simplicity and reliability)
                try:
                    # 在封面之前插入：停顿 + 翻书转场（仅当片头 hook 已启用且封面存在）
                    if hook_intro_added and hook_intro_img_path and os.path.exists(hook_intro_img_path):
                        pause_dur = float(getattr(config, "HOOK_INTRO_PAUSE", 0.25) or 0.0)
                        flip_dur = float(getattr(config, "HOOK_INTRO_FLIP", 0.6) or 0.0)
                        if pause_dur > 0:
                            pause_clip = ImageClip(hook_intro_img_path).set_duration(pause_dur)
                            if cover_bg_path and os.path.exists(cover_bg_path):
                                try:
                                    w0, h0 = Image.open(cover_bg_path).size
                                    pause_clip = pause_clip.resize((w0, h0))
                                except Exception:
                                    pass
                            clips.append(pause_clip)
                            bgm_start_time += pause_dur

                        if flip_dur > 0:
                            flip_clip = self.create_page_flip_transition(
                                hook_intro_img_path, cover_path, duration=flip_dur
                            )
                            if flip_clip:
                                clips.append(flip_clip)
                                bgm_start_time += flip_dur

                    title_audio_path = os.path.join(
                        config.OUTPUT_DIR, "title_audio.mp3"
                    )
                    # 标题语音（不存在才生成，避免重复开销）
                    if not os.path.exists(title_audio_path):
                        cmd_title = [
                            "edge-tts",
                            "--text",
                            topic,
                            "--write-media",
                            title_audio_path,
                            "--voice",
                            config.TTS_VOICE_TITLE,
                        ]
                        subprocess.run(
                            cmd_title,
                            check=True,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )

                    title_audio_clip = (
                        AudioFileClip(title_audio_path)
                        if os.path.exists(title_audio_path)
                        else None
                    )

                    if title_audio_clip:
                        silence_pre, silence_post = 0.4, 1.0
                        total_duration = max(
                            silence_pre + title_audio_clip.duration + silence_post, 2.0
                        )
                        if trans_duration > 0:
                            total_duration += trans_duration

                        cover_clip = ImageClip(cover_path).set_duration(total_duration)
                        cover_clip = cover_clip.set_audio(
                            CompositeAudioClip([title_audio_clip.set_start(silence_pre)])
                        )
                        clips.append(cover_clip)
                        bgm_start_time += total_duration
                    else:
                        clips.append(ImageClip(cover_path).set_duration(2.0))
                        bgm_start_time += 2.0
                except Exception as e:
                    logger.warning(f"Failed to add audio to cover: {e}")
                    clips.append(ImageClip(cover_path).set_duration(2.0))
                    bgm_start_time += 2.0

        for scene in scenes:
            if not scene.audio_path:
                continue
            try:
                audio_clip = AudioFileClip(scene.audio_path)
                audio_padding = 0.5
                duration = audio_clip.duration + audio_padding
                actual_duration = duration  # Logic splits here slightly compared to old code but effectively same
                if trans_duration > 0:
                    duration += trans_duration

                visual_clip = self._load_visual(scene, duration)
                if visual_clip:
                    visual_clip = visual_clip.set_audio(audio_clip)

                    # ABSTRACT METHOD CALL
                    visual_clip = self._compose_scene(scene, visual_clip, duration)

                    if trans_duration > 0 and len(clips) > 0:
                        visual_clip = visual_clip.crossfadein(trans_duration)
                    clips.append(visual_clip)
            except Exception as e:
                logger.error(f"Error processing scene {scene.scene_id}: {e}")

        if not clips:
            return

        if config.ENABLE_BRAND_OUTRO:
            platform_map = {"儿童绘本": "general", "英语绘本": "general"}
            platform = platform_map.get(category, "general")
            outro_clip = self.create_brand_outro(duration=4.0, platform=platform)
            if outro_clip:
                clips.append(outro_clip)

        padding = -trans_duration if trans_duration > 0 else 0
        final_clip = concatenate_videoclips(clips, method="compose", padding=padding)

        bgm_file = None
        if category and category in config.CATEGORY_BGM:
            bgm_filename = config.CATEGORY_BGM[category]
            # Assumes assets path relative to this file's parent's parent...
            # Original: os.path.join(os.path.dirname(__file__), "assets", "music")
            # Now we are in auto_maker/steps/video/base.py.
            # auto_maker is ../../
            # assets is ../../assets?
            # Adjust path:
            base_dir = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            potential_path = os.path.join(base_dir, "assets", "music", bgm_filename)
            if os.path.exists(potential_path):
                bgm_file = potential_path
            else:
                logger.warning(f"BGM not found at {potential_path}")

        if bgm_file:
            try:
                bgm_clip = AudioFileClip(bgm_file)
                bgm_duration = max(0, final_clip.duration - bgm_start_time)
                if bgm_duration > 0:
                    bgm_clip = afx.audio_loop(bgm_clip, duration=bgm_duration)
                    bgm_clip = bgm_clip.volumex(0.15)
                    bgm_clip = bgm_clip.set_start(bgm_start_time)
                    final_audio = CompositeAudioClip([final_clip.audio, bgm_clip])
                    final_clip = final_clip.set_audio(final_audio)
            except Exception as e:
                logger.error(f"Failed to mix BGM: {e}")

        output_path = os.path.join(config.OUTPUT_DIR, output_filename)
        final_clip.write_videofile(
            output_path, fps=24, codec="libx264", audio_codec="aac"
        )
        logger.info(f"Video saved to {output_path}")
        return output_path
