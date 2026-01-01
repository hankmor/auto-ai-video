import os
import numpy as np
import pypinyin
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
    concatenate_videoclips,
    CompositeVideoClip,
    CompositeAudioClip,
)
from moviepy.audio.AudioClip import CompositeAudioClip
import moviepy.audio.fx.all as afx
import moviepy.video.fx.all as vfx

from config.config import config
from model.models import Scene
from util.logger import logger
from steps.image.font_manager import font_manager


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

    def create_brand_intro(self, duration: float = 3.0):
        try:
            logo_path = os.path.join("brand", "logo_gemini_magic_storybook.png")
            if not os.path.exists(logo_path):
                logger.warning(f"Brand logo not found at {logo_path}, skipping intro")
                return None

            width, height = config.VIDEO_SIZE
            brand_dir = "brand"
            os.makedirs(brand_dir, exist_ok=True)
            bg_path = os.path.join(brand_dir, "intro_bg.png")
            title_path = os.path.join(brand_dir, "intro_title.png")
            subtitle_path = os.path.join(brand_dir, "intro_subtitle.png")

            if not os.path.exists(bg_path):
                bg_img = Image.new("RGB", (width, height), (255, 255, 255))
                draw = ImageDraw.Draw(bg_img)
                for y in range(height):
                    ratio = y / height
                    r = int(255 + (224 - 255) * ratio)
                    g = int(240 + (230 - 240) * ratio)
                    b = int(245 + (255 - 245) * ratio)
                    draw.line([(0, y), (width, y)], fill=(r, g, b))
                bg_img.save(bg_path)

            bg_clip = ImageClip(bg_path).set_duration(duration)
            logo_img = ImageClip(logo_path)
            logo_scale = min(width * 0.6 / logo_img.w, height * 0.4 / logo_img.h)
            logo_img = logo_img.resize(logo_scale)
            logo_y = height * 0.3
            logo_clip = logo_img.set_position(("center", logo_y)).set_duration(duration)

            if not os.path.exists(title_path):
                title_img = Image.new("RGBA", (width, 200), (255, 255, 255, 0))
                title_draw = ImageDraw.Draw(title_img)
                title_font = font_manager.get_font("chinese", 100)
                title_text = "智绘童梦"
                bbox = title_draw.textbbox((0, 0), title_text, font=title_font)
                title_width = bbox[2] - bbox[0]
                title_x = (width - title_width) // 2
                title_draw.text(
                    (title_x, 50), title_text, font=title_font, fill=(74, 74, 74)
                )
                title_img.save(title_path)

            if not os.path.exists(subtitle_path):
                subtitle_img = Image.new("RGBA", (width, 100), (255, 255, 255, 0))
                subtitle_draw = ImageDraw.Draw(subtitle_img)
                subtitle_font = font_manager.get_font("english", 50)
                subtitle_text = "SmartArt Kids"
                bbox = subtitle_draw.textbbox((0, 0), subtitle_text, font=subtitle_font)
                subtitle_width = bbox[2] - bbox[0]
                subtitle_x = (width - subtitle_width) // 2
                subtitle_draw.text(
                    (subtitle_x, 20),
                    subtitle_text,
                    font=subtitle_font,
                    fill=(135, 206, 235),
                )
                subtitle_img.save(subtitle_path)

            title_y = logo_y + logo_img.h + 50
            title_clip = (
                ImageClip(title_path).set_position((0, title_y)).set_duration(duration)
            )
            subtitle_y = title_y + 200
            subtitle_clip = (
                ImageClip(subtitle_path)
                .set_position((0, subtitle_y))
                .set_duration(duration)
            )

            intro_clip = CompositeVideoClip(
                [bg_clip, logo_clip, title_clip, subtitle_clip]
            )
            intro_clip = intro_clip.fadein(0.5).fadeout(0.5)
            return intro_clip
        except Exception as e:
            logger.error(f"Failed to create brand intro: {e}")
            return None

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

        if config.ENABLE_BRAND_INTRO:
            intro_clip = self.create_brand_intro(duration=3.0)
            if intro_clip:
                clips.append(intro_clip)
                bgm_start_time += 3.0

        cover_bg_path = None
        for s in scenes:
            if s.image_path and os.path.exists(s.image_path):
                cover_bg_path = s.image_path
                break

        if topic and cover_bg_path:
            cover_path = os.path.join(config.OUTPUT_DIR, "cover.png")
            if self.generate_cover(cover_bg_path, topic, cover_path, subtitle=subtitle):
                # Title Audio Logic (CLI Fallback for simplicity and reliability)
                try:
                    title_audio_path = os.path.join(
                        config.OUTPUT_DIR, "title_audio.mp3"
                    )
                    import subprocess

                    cmd = [
                        "edge-tts",
                        "--text",
                        topic,
                        "--write-media",
                        title_audio_path,
                        "--voice",
                        config.TTS_VOICE_TITLE,
                    ]
                    subprocess.run(
                        cmd,
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )

                    if os.path.exists(title_audio_path):
                        title_audio_clip = AudioFileClip(title_audio_path)
                        silence_pre, silence_post = 0.5, 1.0
                        total_duration = max(
                            silence_pre + title_audio_clip.duration + silence_post, 2.0
                        )
                        if trans_duration > 0:
                            total_duration += trans_duration

                        cover_clip = ImageClip(cover_path).set_duration(total_duration)
                        final_audio = CompositeAudioClip(
                            [title_audio_clip.set_start(silence_pre)]
                        )
                        cover_clip = cover_clip.set_audio(final_audio)
                        clips.append(cover_clip)
                        bgm_start_time = total_duration
                    else:
                        clips.append(ImageClip(cover_path).set_duration(2.0))
                        bgm_start_time = 2.0
                except Exception as e:
                    logger.warning(f"Failed to add audio to cover: {e}")
                    clips.append(ImageClip(cover_path).set_duration(2.0))
                    bgm_start_time = 2.0

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
