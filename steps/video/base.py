import os
import numpy as np
import pypinyin
import math
import asyncio
import edge_tts
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

from config.config import C
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

    def _get_depth_estimator(self):
        if not hasattr(self, "_depth_estimator") or self._depth_estimator is None:
            from steps.effects.depth_estimator import DepthEstimator

            self._depth_estimator = DepthEstimator()
        return self._depth_estimator

    def _get_parallax_animator(self):
        if not hasattr(self, "_parallax_animator") or self._parallax_animator is None:
            from steps.effects.parallax_animator import ParallaxAnimator

            self._parallax_animator = ParallaxAnimator(
                movement_scale=C.PARALLAX_MOVEMENT_SCALE
            )
        return self._parallax_animator

    def _resize_to_fill(self, clip: VideoClip, target_size: tuple) -> VideoClip:
        """Resize clip to fill target size (Aspect Fill)"""
        W, H = target_size
        src_w, src_h = clip.size

        scale = max(W / src_w, H / src_h)
        new_w = int(src_w * scale)
        new_h = int(src_h * scale)

        # Resize
        clip = clip.resize(newsize=(new_w, new_h))

        # Center Crop
        if new_w != W or new_h != H:
            x_offset = (new_w - W) // 2
            y_offset = (new_h - H) // 2
            clip = clip.crop(x1=x_offset, y1=y_offset, x2=x_offset + W, y2=y_offset + H)
        return clip

    def _load_visual(self, scene: Scene, duration: float) -> Optional[VideoClip]:
        if C.ENABLE_ANIMATION and scene.video_path and os.path.exists(scene.video_path):
            try:
                v_clip = VideoFileClip(scene.video_path)
                if v_clip.duration < duration:
                    v_clip = vfx.loop(v_clip, duration=duration)
                return v_clip.set_duration(duration)
            except Exception as e:
                logger.traceback_and_raise(
                    Exception(f"Error loading video {scene.video_path}: {e}")
                )

        if scene.image_path and os.path.exists(scene.image_path):
            try:
                # 1. Try Parallax Effect (if enabled)
                if getattr(C, "SHOULD_USE_PARALLAX", False):
                    try:
                        logger.info(
                            f"🌌 Attempting Parallax for scene {scene.scene_id}"
                        )
                        estimator = self._get_depth_estimator()
                        animator = self._get_parallax_animator()

                        # Prepare cache dir if enabled
                        cache_dir = None
                        if getattr(C, "PARALLAX_CACHE_DEPTH_MAPS", True):
                            cache_dir = os.path.join(C.OUTPUT_DIR, "depth_cache")
                            os.makedirs(cache_dir, exist_ok=True)

                        # Estimate depth
                        depth_map = estimator.estimate(
                            scene.image_path, cache_dir=cache_dir
                        )

                        # Get action (default to pan_right for parallax usually looks best)
                        action = (
                            getattr(scene, "camera_action", "pan_right") or "pan_right"
                        )

                        # Create clip
                        target_size = getattr(C, "VIDEO_SIZE", (1080, 1920))
                        p_clip = animator.create_parallax_clip(
                            scene.image_path,
                            depth_map,
                            duration,
                            action=action,
                            target_size=target_size,
                        )

                        if p_clip:
                            # Resize to fill video size
                            if hasattr(C, "VIDEO_SIZE"):
                                p_clip = self._resize_to_fill(p_clip, C.VIDEO_SIZE)
                            return p_clip

                    except Exception as e:
                        logger.warning(
                            f"⚠️ Parallax generation failed, falling back to Ken Burns: {e}"
                        )
                        # Fallthrough to normal image handling

                # 2. Normal Image Handling (Ken Burns)
                img_clip = ImageClip(scene.image_path)

                if hasattr(C, "VIDEO_SIZE"):
                    img_clip = self._resize_to_fill(img_clip, C.VIDEO_SIZE)

                # Use camera action from scene, default to 'zoom_in' or 'pan_right' etc.
                action = getattr(scene, "camera_action", "zoom_in")
                if not action:
                    action = "zoom_in"

                return self.apply_camera_movement(
                    img_clip, duration=duration, action=action
                )
            except Exception as e:
                logger.traceback_and_raise(
                    Exception(f"Error loading image {scene.image_path}: {e}")
                )
                return None
        return None

    # ==================== Easing Functions ====================
    @staticmethod
    def _ease_in_out_cubic(t):
        """三次缓动函数，平滑加速和减速"""
        if t < 0.5:
            return 4 * t * t * t
        else:
            return 1 - pow(-2 * t + 2, 3) / 2

    @staticmethod
    def _ease_out_quad(t):
        """二次缓动函数，快速开始，缓慢结束"""
        return 1 - (1 - t) * (1 - t)

    @staticmethod
    def _ease_in_out_sine(t):
        """正弦缓动函数，非常平滑"""
        return -(math.cos(math.pi * t) - 1) / 2

    def _calculate_zoom_transform(self, w, h, progress, scale_factor, is_zoom_in):
        """计算缩放变换参数"""
        if is_zoom_in:
            current_scale = 1.0 + (scale_factor - 1.0) * progress
        else:
            current_scale = scale_factor - (scale_factor - 1.0) * progress

        crop_w = w / current_scale
        crop_h = h / current_scale
        x1 = (w - crop_w) / 2
        y1 = (h - crop_h) / 2

        return current_scale, x1, y1, crop_w, crop_h

    def _calculate_pan_transform(self, w, h, progress, pan_scale, direction):
        """计算平移变换参数"""
        current_scale = pan_scale
        crop_w = w / current_scale
        crop_h = h / current_scale
        max_x = w - crop_w
        max_y = h - crop_h

        if direction == "left":
            x1 = max_x * (1 - progress)
            y1 = max_y / 2
        elif direction == "right":
            x1 = max_x * progress
            y1 = max_y / 2
        elif direction == "up":
            x1 = max_x / 2
            y1 = max_y * (1 - progress)
        elif direction == "down":
            x1 = max_x / 2
            y1 = max_y * progress
        else:
            x1 = (w - crop_w) / 2
            y1 = (h - crop_h) / 2

        return current_scale, x1, y1, crop_w, crop_h

    def _calculate_combined_transform(
        self, w, h, progress, scale_factor, pan_scale, action_parts
    ):
        """计算组合运动变换参数"""
        # 解析zoom部分
        if "zoom" in action_parts:
            if "in" in action_parts:
                current_scale = 1.0 + (scale_factor - 1.0) * progress
            elif "out" in action_parts:
                current_scale = scale_factor - (scale_factor - 1.0) * progress
            else:
                current_scale = pan_scale
        else:
            current_scale = pan_scale

        crop_w = w / current_scale
        crop_h = h / current_scale
        max_x = w - crop_w
        max_y = h - crop_h

        # 解析pan部分
        if "left" in action_parts:
            x1, y1 = max_x * (1 - progress), max_y / 2
        elif "right" in action_parts:
            x1, y1 = max_x * progress, max_y / 2
        elif "up" in action_parts:
            x1, y1 = max_x / 2, max_y * (1 - progress)
        elif "down" in action_parts:
            x1, y1 = max_x / 2, max_y * progress
        else:
            x1, y1 = (w - crop_w) / 2, (h - crop_h) / 2

        return current_scale, x1, y1, crop_w, crop_h

    def _apply_rotation_if_enabled(self, img, rotation_angle):
        """应用旋转效果（如果启用）"""
        if abs(rotation_angle) > 0.01:
            return img.rotate(rotation_angle, resample=Image.BICUBIC, expand=False)
        return img

    def apply_camera_movement(
        self,
        clip: ImageClip,
        duration: float,
        action: str = "zoom_in",
        scale_factor: float = None,
    ) -> VideoClip:
        """
        应用增强的肯·伯恩斯（Ken Burns）风格镜头运动。
        支持缓动函数、组合运动和可选旋转效果。
        """
        w, h = clip.size

        # 从配置获取参数
        enable_easing = getattr(C, "CAMERA_ENABLE_EASING", True)
        enable_rotation = getattr(C, "CAMERA_ENABLE_ROTATION", False)
        rotation_degree = getattr(C, "CAMERA_ROTATION_DEGREE", 1.5)

        if scale_factor is None:
            scale_factor = getattr(C, "CAMERA_MOVEMENT_INTENSITY", 1.15)

        pan_scale = scale_factor

        def make_frame(t):
            raw_progress = t / duration
            progress = (
                self._ease_in_out_cubic(raw_progress) if enable_easing else raw_progress
            )

            rotation_angle = 0

            # 根据不同的action类型调用对应的变换计算方法
            if action == "zoom_in":
                current_scale, x1, y1, crop_w, crop_h = self._calculate_zoom_transform(
                    w, h, progress, scale_factor, is_zoom_in=True
                )
                if enable_rotation:
                    rotation_angle = rotation_degree * progress

            elif action == "zoom_out":
                current_scale, x1, y1, crop_w, crop_h = self._calculate_zoom_transform(
                    w, h, progress, scale_factor, is_zoom_in=False
                )
                if enable_rotation:
                    rotation_angle = -rotation_degree * progress

            elif action.startswith("pan_"):
                direction = action.replace("pan_", "")
                current_scale, x1, y1, crop_w, crop_h = self._calculate_pan_transform(
                    w, h, progress, pan_scale, direction
                )

            elif "_" in action and not action.startswith("pan_"):
                # 组合运动
                action_parts = action.split("_")
                current_scale, x1, y1, crop_w, crop_h = (
                    self._calculate_combined_transform(
                        w, h, progress, scale_factor, pan_scale, action_parts
                    )
                )
                if enable_rotation:
                    rotation_angle = rotation_degree * math.sin(progress * math.pi)
            else:
                # 静止或未知动作
                return clip.get_frame(t)

            # 渲染帧
            frame = clip.get_frame(0)
            img_pil = Image.fromarray(frame)
            img_cropped = img_pil.crop((x1, y1, x1 + crop_w, y1 + crop_h))

            # 应用旋转
            if enable_rotation:
                img_cropped = self._apply_rotation_if_enabled(
                    img_cropped, rotation_angle
                )

            # 缩放回原始尺寸
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
                resample_method = getattr(
                    Image, "LANCZOS", getattr(Image, "ANTIALIAS", 1)
                )

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
                page_rect = img_page.resize(
                    (page_w, h), resample=resample_method
                ).copy()
                mask = Image.new("L", (page_w, h), 0)
                mdraw = ImageDraw.Draw(mask)
                # 梯形：右边缘上下分别向内偏移 skew
                mdraw.polygon(
                    [(0, 0), (page_w, skew), (page_w, h - skew), (0, h)], fill=255
                )
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
            logger.traceback_and_raise(
                Exception(f"Failed to create page flip transition: {e}")
            )
            return None

    def apply_circle_open(self, clip: VideoClip, duration: float = 1.0) -> VideoClip:
        """
        Apply a Circle Open transition (iris in) effect to the START of the clip.
        """
        w, h = clip.w, clip.h
        # Calculate max radius to cover screen
        max_r = (w**2 + h**2) ** 0.5 / 2 * 1.2

        def make_mask_frame(t):
            # If t > duration, fully transparent mask (white) = fully visible
            if t >= duration:
                return np.ones((h, w), dtype=float)

            progress = t / duration
            # Ease out
            progress = 1 - (1 - progress) ** 2
            r = int(max_r * progress)

            mask_img = Image.new("L", (w, h), 0)
            draw = ImageDraw.Draw(mask_img)
            cx, cy = w // 2, h // 2
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)

            return np.array(mask_img) / 255.0

        # Create mask clip with same duration as content
        mask_clip = VideoClip(
            make_frame=make_mask_frame, ismask=True, duration=clip.duration
        )
        return clip.set_mask(mask_clip)

    def apply_blur_transition(
        self, clip: VideoClip, duration: float = 0.5
    ) -> VideoClip:
        # Simple fade in from blur?
        # MoviePy's standard blur is slow. Let's stick to simple fade or circle for now.
        return clip.crossfadein(duration)

    # 品牌片头已与 Hook Voice 合并：当开启 enable_hook_voice 且有文案时，
    # 将使用 assets/image/brand_intro.png 作为片头画面并播放引导语音。

    def create_brand_outro(self, duration: float = 4.0, platform: str = "general"):
        try:
            # Modified to use existing asset
            logo_path = os.path.join(C.ASSETS_DIR, "image", "logo.png")

            if not os.path.exists(logo_path):
                logger.warning(f"⚠️ Brand Outro Skipped: Logo not found at {logo_path}")
                return None

            width, height = C.VIDEO_SIZE

            # Use separate brand dir for generated cache to avoid polluting assets
            brand_dir = os.path.join(C.OUTPUT_DIR, "brand_cache")
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
                like_text = "记得点赞关注哦"
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
            logger.traceback_and_raise(Exception(f"Failed to create brand outro: {e}"))
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
                # Detect if subtitle contains Chinese (or non-ASCII) to pick font
                has_chinese = any("\u4e00" <= c <= "\u9fff" for c in subtitle)
                font_type = "chinese" if has_chinese else "english"
                font_sub = font_manager.get_font(font_type, int(W * 0.05))

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
            logger.traceback_and_raise(
                Exception(f"Failed to generate English cover: {e}")
            )
            return False

    def _generate_intro_dub_sync(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None,
        rate: Optional[str] = None,
        pitch: Optional[str] = None,
        style: Optional[str] = None,
    ) -> bool:
        """
        Synchronously generate dubbing via edge-tts python library.
        Running in a separate thread to avoid conflicting with existing event loops.
        """
        import threading

        try:
            # Use defaults from Config if not provided
            used_voice = (
                voice if voice else getattr(C, "TTS_VOICE", "zh-CN-YunxiaNeural")
            )
            used_rate = rate if rate else "-10%"
            used_pitch = pitch if pitch else "+0Hz"

            def _run_in_thread():
                async def _gen():
                    communicate = edge_tts.Communicate(
                        text, used_voice, rate=used_rate, pitch=used_pitch
                    )
                    await communicate.save(output_path)

                # New loop for this thread
                asyncio.run(_gen())

            # Start a new thread to run the async task
            t = threading.Thread(target=_run_in_thread)
            t.start()
            t.join(timeout=30)  # Wait up to 30s

            if t.is_alive():
                logger.error("Intro Dub Generation Timed Out")
                return False

            return True

        except Exception as e:
            logger.traceback_and_raise(Exception(f"Failed to generate intro dub: {e}"))
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
            logger.traceback_and_raise(Exception(f"Failed to generate cover: {e}"))
            return False

    # ===================================================================
    # 辅助方法：用于 assemble_video 的各个步骤
    # ===================================================================

    def _setup_transition_config(self, category: str):
        """配置转场类型和参数"""
        trans_type = "none"
        trans_duration, padding = 0.0, 0.0

        if (
            category
            and hasattr(C, "CATEGORY_TRANSITIONS")
            and category in C.CATEGORY_TRANSITIONS
        ):
            trans_type = C.CATEGORY_TRANSITIONS[category]

        if trans_type == "crossfade":
            trans_duration, padding = 0.8, -0.8
        elif trans_type == "crossfade_slow":
            trans_duration, padding = 1.5, -1.5
        elif trans_type == "circle_open":
            trans_duration, padding = 1.2, -1.0
        elif trans_type == "page_turn":
            trans_duration, padding = 0.8, 0.0

        return trans_type, trans_duration, padding

    def _generate_cover_clip(self, scenes: List[Scene], topic: str, subtitle: str):
        """生成封面 clip"""
        cover_path = os.path.join(C.OUTPUT_DIR, "cover.png")

        if not os.path.exists(cover_path):
            logger.info("Generating Video Cover in Assembly Phase...")
            base_image = next(
                (
                    s.image_path
                    for s in scenes
                    if s.image_path and os.path.exists(s.image_path)
                ),
                None,
            )

            if base_image:
                self.generate_cover(
                    image_path=base_image,
                    title=topic or "Untitled",
                    output_path=cover_path,
                    subtitle=subtitle,
                )
            else:
                logger.warning("No scene image available for cover generation.")

        if os.path.exists(cover_path):
            try:
                cover_clip = ImageClip(cover_path)

                # 🔥 关键修复：确保封面也缩放到 VIDEO_SIZE
                if hasattr(C, "VIDEO_SIZE"):
                    target_w, target_h = C.VIDEO_SIZE
                    curr_w, curr_h = cover_clip.size

                    if curr_w != target_w or curr_h != target_h:
                        logger.info(
                            f"📐 封面缩放: {curr_w}x{curr_h} -> {target_w}x{target_h}"
                        )

                        # Aspect Fill
                        scale = max(target_w / curr_w, target_h / curr_h)
                        new_w, new_h = int(curr_w * scale), int(curr_h * scale)

                        cover_clip = cover_clip.resize(newsize=(new_w, new_h))

                        # Center crop
                        if new_w != target_w or new_h != target_h:
                            cover_clip = cover_clip.crop(
                                x_center=new_w / 2,
                                y_center=new_h / 2,
                                width=target_w,
                                height=target_h,
                            )

                # 🔥 添加封面朗读音频
                duration = 2.5
                if topic:
                    cover_audio_path = os.path.join(C.OUTPUT_DIR, "cover_title.mp3")
                    logger.info(f"🎤 生成封面朗读: {topic}")
                    if self._generate_intro_dub_sync(
                        text=topic,
                        output_path=cover_audio_path,
                        # 使用旁白音色或默认音色
                        voice=None,
                    ):
                        if os.path.exists(cover_audio_path):
                            audio_clip = AudioFileClip(cover_audio_path)

                            # 确保封面时长至少为2.5秒，或音频时长+0.5秒缓冲
                            duration = max(2.5, audio_clip.duration + 0.5)
                            logger.info(
                                f"   封面朗读时长: {audio_clip.duration:.2f}s -> 封面总时长: {duration:.2f}s"
                            )

                            # Padding audio using CompositeAudioClip to avoid duration mismatch errors
                            padded_audio = CompositeAudioClip(
                                [audio_clip.set_start(0)]
                            ).set_duration(duration)
                            cover_clip = cover_clip.set_audio(padded_audio)

                return cover_clip.set_duration(duration).fadein(0.5).fadeout(0.5)
            except Exception as e:
                logger.traceback_and_raise(
                    Exception(f"Failed to load cover image: {e}")
                )
        return None

    def _load_scene_assets(
        self, scene: Scene, action_map: dict, i: int, padding: float
    ):
        """
        加载场景的音频和视觉资源

        Returns:
            tuple: (audio_clip, visual_clip, duration) 或 (None, None, None) 如果失败
        """
        try:
            # 解析运镜动作
            raw_action = getattr(scene, "camera_action", "zoom_in")
            scene.camera_action = action_map.get(raw_action, "zoom_in")

            # 加载音频并计算时长
            audio_clip = AudioFileClip(scene.audio_path).fx(afx.audio_fadeout, 0.05)
            duration = audio_clip.duration + 0.5  # audio_padding
            if padding < 0 and i > 0:
                duration += abs(padding)

            # 加载视觉
            logger.debug(f"   ➡️ Scene {i}: Loading visual from {scene.image_path}")
            visual_clip = self._load_visual(scene, duration)
            if not visual_clip:
                logger.warning(
                    f"   ⚠️ Scene {i}: visual_clip is ALREADY None after _load_visual"
                )
                return None, None, None

            logger.debug(f"   ✅ Scene {i}: Visual loaded: {visual_clip.size}")
            return audio_clip, visual_clip, duration

        except Exception as e:
            logger.exception(f"Failed to load assets for scene {scene.scene_id}")
            return None, None, None

    def _sync_audio_video(self, visual_clip, audio_clip, duration):
        """
        同步音频和视频，设置duration

        Returns:
            合成后的visual_clip
        """
        padded_audio = CompositeAudioClip([audio_clip.set_start(0)]).set_duration(
            duration
        )
        return visual_clip.set_audio(padded_audio).set_duration(duration)

    def _apply_transition(
        self,
        clips,
        visual_clip,
        prev_scene,
        current_scene,
        i,
        trans_type,
        trans_duration,
        padding,
    ):
        """
        应用转场效果

        Args:
            clips: 当前clips列表
            visual_clip: 当前场景的visual clip
            prev_scene: 前一个场景
            current_scene: 当前场景
            i: 场景索引
            trans_type: 转场类型
            trans_duration: 转场时长
            padding: 重叠时间（负数表示重叠）

        Returns:
            处理后的visual_clip
        """
        # 翻书转场
        if trans_type == "page_turn" and prev_scene:
            trans_clip = self.create_page_flip_transition(
                prev_scene.image_path, current_scene.image_path, trans_duration
            )
            if trans_clip:
                clips.append(trans_clip)

        # 重叠转场效果
        if padding < 0 and i > 0:
            if trans_type == "circle_open":
                visual_clip = self.apply_circle_open(visual_clip, abs(padding))
            elif trans_type.startswith("crossfade"):
                visual_clip = visual_clip.crossfadein(abs(padding))

        return visual_clip

    def _process_scenes(
        self,
        scenes: List[Scene],
        action_map: dict,
        trans_type: str,
        trans_duration: float,
        padding: float,
    ):
        """批量处理场景，返回 clips 列表"""
        clips = []
        prev_scene_node = None

        for i, scene in enumerate(scenes):
            if not scene.audio_path:
                continue
            try:
                # 1. 加载资源（使用辅助方法）
                audio_clip, visual_clip, duration = self._load_scene_assets(
                    scene, action_map, i, padding
                )
                if not visual_clip:
                    continue

                # 2. 同步音视频（使用辅助方法）
                visual_clip = self._sync_audio_video(visual_clip, audio_clip, duration)

                # 合成场景（添加字幕等）
                narration_cn_log = getattr(scene, "narration_cn", "") or "N/A"
                logger.info(
                    f"🎨 正在合成场景 {scene.scene_id}，narration='{scene.narration[:30]}...', narration_cn='{narration_cn_log[:20]}...'"
                )
                visual_clip = self._compose_scene(scene, visual_clip, duration)
                logger.info(f"   ✅ 场景 {scene.scene_id} 合成完成")

                # 4. 应用转场（使用辅助方法）
                visual_clip = self._apply_transition(
                    clips,
                    visual_clip,
                    prev_scene_node,
                    scene,
                    i,
                    trans_type,
                    trans_duration,
                    padding,
                )

                clips.append(visual_clip)
                prev_scene_node = scene

            except Exception as e:
                logger.traceback_and_raise(
                    Exception(f"Error processing scene {scene.scene_id}: {e}")
                )

        return clips

    def _add_brand_outro(self, clips: List):
        """添加品牌片尾"""
        if not C.ENABLE_BRAND_OUTRO:
            return

        try:
            outro_clip = self.create_brand_outro(duration=4.0)
            if outro_clip:
                clips.append(outro_clip)
                logger.info("✅ 品牌片尾已添加")
            else:
                logger.warning("⚠️ 品牌片尾生成失败")
        except Exception as e:
            logger.traceback_and_raise(Exception(f"Failed to create brand outro: {e}"))

    def _add_custom_intro(self, main_clip, intro_hook: str, bgm_start_time: float):
        """添加自定义片头视频，返回 (final_clip, new_bgm_start_time)"""
        if not C.ENABLE_CUSTOM_INTRO:
            return main_clip, bgm_start_time

        intro_path = self._resolve_intro_path()
        if not intro_path or not os.path.exists(intro_path):
            if intro_path:
                logger.warning(
                    f"Custom intro enabled but file not found at {intro_path}"
                )
            return main_clip, bgm_start_time

        try:
            logger.debug(f"Adding custom intro video from {intro_path}")
            intro_clip = VideoFileClip(intro_path)

            # 添加配音
            intro_clip = self._add_intro_dubbing(intro_clip, intro_hook)

            # 缩放到目标尺寸
            intro_clip = self._resize_intro_to_target(intro_clip)

            # 应用转场
            final_clip, bgm_offset = self._apply_intro_transition(intro_clip, main_clip)

            return final_clip, bgm_start_time + bgm_offset

        except Exception as e:
            logger.traceback_and_raise(
                Exception(f"Failed to add custom intro video: {e}")
            )
            return main_clip, bgm_start_time

    def _resolve_intro_path(self):
        """解析片头视频路径"""
        intro_path = None
        category = getattr(C, "CURRENT_CATEGORY", "")

        # 优先使用分类专属片头
        if category and hasattr(C, "CATEGORY_INTROS") and category in C.CATEGORY_INTROS:
            intro_path = C.CATEGORY_INTROS[category]

        # 否则使用通用片头
        if not intro_path:
            generic_intro = getattr(C, "CUSTOM_INTRO_VIDEO_PATH", "")
            if generic_intro:
                import random

                intro_path = (
                    random.choice(generic_intro)
                    if isinstance(generic_intro, list)
                    else str(generic_intro)
                )

        # 转换为绝对路径
        if intro_path and not os.path.isabs(intro_path):
            base_dir = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            intro_path = os.path.join(base_dir, intro_path)

        return intro_path

    def _adjust_intro_audio_for_video(
        self, new_audio, intro_clip, dub_audio_path, intro_hook
    ):
        """
        调整intro音频长度以匹配视频
        如果音频过长，尝试加速重新生成（最多30%）

        Returns:
            调整后的audio clip
        """
        if new_audio.duration <= intro_clip.duration:
            return new_audio

        ratio = new_audio.duration / intro_clip.duration
        if ratio > 1.3:
            logger.debug(
                f"⚠️ Audio is much longer ({ratio:.2f}x). Capping speedup to +30% and extending video."
            )
            return self._regenerate_faster_intro_dub(
                new_audio,
                intro_clip,
                dub_audio_path,
                intro_hook,
                max_speed_increase=0.3,
            )
        else:
            logger.debug(
                f"⚠️ Intro Audio ({new_audio.duration:.2f}s) > Video ({intro_clip.duration:.2f}s). Regenerating to fit..."
            )
            return self._regenerate_faster_intro_dub(
                new_audio, intro_clip, dub_audio_path, intro_hook
            )

    def _sync_intro_clip_with_audio(self, intro_clip, new_audio):
        """
        同步intro视频和音频长度
        - 如果音频短，裁剪视频
        - 如果音频长，延长视频（使用最后一帧）

        Returns:
            调整后的intro_clip
        """
        # 设置音频
        intro_clip = intro_clip.without_audio().set_audio(new_audio)

        # 如果音频比视频短，裁剪视频
        if intro_clip.duration > new_audio.duration:
            logger.debug(
                f"✂️ 裁剪片头视频: {intro_clip.duration:.2f}s -> {new_audio.duration:.2f}s"
            )
            return intro_clip.subclip(0, new_audio.duration)

        # 如果音频比视频长，延长视频
        elif new_audio.duration > intro_clip.duration:
            diff = new_audio.duration - intro_clip.duration
            logger.debug(f"🐢 延长片头视频以匹配音频: +{diff:.2f}s")
            # 使用最后一帧定格
            last_frame = intro_clip.get_frame(intro_clip.duration - 0.05)
            freeze_clip = (
                ImageClip(last_frame).set_duration(diff).set_fps(intro_clip.fps)
            )
            intro_clip = concatenate_videoclips([intro_clip, freeze_clip])
            intro_clip = intro_clip.set_audio(new_audio)

        return intro_clip

    def _add_intro_dubbing(self, intro_clip, intro_hook: str):
        """为片头添加配音"""
        if not getattr(C, "ENABLE_CUSTOM_INTRO_DUB", False) or not intro_hook:
            return intro_clip

        logger.info(f"🧠 Using AI Generated Intro Hook: {intro_hook}")
        logger.info(f"🎤 Generating Intro Dub: {intro_hook[:15]}...")

        dub_audio_path = os.path.join(C.OUTPUT_DIR, "intro_hook_dub.mp3")

        # 生成配音
        if not self._generate_intro_dub_sync(
            text=intro_hook,
            output_path=dub_audio_path,
            voice=getattr(C, "CUSTOM_INTRO_DUB_VOICE", None),
            rate=getattr(C, "CUSTOM_INTRO_DUB_RATE", None),
            pitch=getattr(C, "CUSTOM_INTRO_DUB_PITCH", None),
        ):
            return intro_clip

        if not os.path.exists(dub_audio_path):
            return intro_clip

        new_audio = AudioFileClip(dub_audio_path)

        # 1. 调整音频长度（如果需要）
        new_audio = self._adjust_intro_audio_for_video(
            new_audio, intro_clip, dub_audio_path, intro_hook
        )

        # 2. 同步视频和音频
        return self._sync_intro_clip_with_audio(intro_clip, new_audio)

    def _regenerate_faster_intro_dub(
        self,
        old_audio,
        intro_clip,
        dub_audio_path,
        intro_hook,
        max_speed_increase: float = 1.0,
    ):
        """重新生成加速的片头配音
        max_speed_increase: 最大允许增加的倍速 (例如 0.3 表示最多加速 +30%)
        """
        ratio = old_audio.duration / intro_clip.duration

        # Apply strict capping
        if ratio > (1.0 + max_speed_increase):
            logger.info(
                f"   ⚠️ Desired ratio {ratio:.2f}x exceeds limit +{max_speed_increase:.0%}. Capping."
            )
            ratio = 1.0 + max_speed_increase

        current_rate_str = getattr(C, "CUSTOM_INTRO_DUB_RATE", "+0%")

        try:
            base_rate_val = int(current_rate_str.strip("%"))
        except:
            base_rate_val = 0

        current_speed = 1.0 + (base_rate_val / 100.0)
        target_speed = current_speed * ratio * 1.05  # 5% buffer
        new_rate_str = f"{int((target_speed - 1.0) * 100):+d}%"

        logger.info(
            f"🔄 Regenerating Intro Dub with rate: {current_rate_str} -> {new_rate_str}"
        )

        old_audio.close()

        if self._generate_intro_dub_sync(
            text=intro_hook,
            output_path=dub_audio_path,
            voice=getattr(C, "CUSTOM_INTRO_DUB_VOICE", None),
            rate=new_rate_str,
            pitch=getattr(C, "CUSTOM_INTRO_DUB_PITCH", None),
        ):
            new_audio = AudioFileClip(dub_audio_path)
            if new_audio.duration > intro_clip.duration:
                logger.warning("⚠️ Audio still slightly longer. Trimming end.")
                new_audio = new_audio.subclip(0, intro_clip.duration)
            return new_audio
        else:
            logger.error("Failed to regenerate faster audio.")
            return (
                AudioFileClip(dub_audio_path)
                if os.path.exists(dub_audio_path)
                else old_audio
            )

    def _resize_intro_to_target(self, intro_clip):
        """将片头视频缩放到目标尺寸（Aspect Fill）"""
        if not hasattr(C, "VIDEO_SIZE"):
            return intro_clip

        target_w, target_h = C.VIDEO_SIZE
        w, h = intro_clip.size

        if w == target_w and h == target_h:
            return intro_clip

        # Aspect Fill: 缩放后裁剪
        ratio_w, ratio_h = target_w / w, target_h / h
        scale = max(ratio_w, ratio_h)
        new_w, new_h = int(w * scale), int(h * scale)

        logger.debug(f"🎬 片头视频缩放: {w}x{h} -> {new_w}x{new_h} (scale={scale:.3f})")

        if scale != 1.0:
            intro_clip = intro_clip.resize(newsize=(new_w, new_h))

        # Center crop
        if new_w != target_w or new_h != target_h:
            intro_clip = intro_clip.crop(
                x_center=new_w / 2,
                y_center=new_h / 2,
                width=target_w,
                height=target_h,
            )

        return intro_clip

    def _apply_intro_transition(self, intro_clip, main_clip):
        """应用片头转场效果，返回 (final_clip, bgm_offset)"""
        intro_trans = getattr(C, "CUSTOM_INTRO_TRANSITION", "crossfade")
        intro_trans_dur = abs(
            float(getattr(C, "CUSTOM_INTRO_TRANSITION_DURATION", 0.8))
        )

        if intro_trans == "crossfade" and intro_trans_dur > 0:
            # 延长片头：添加定格帧
            last_frame_t = max(0, intro_clip.duration - 0.1)
            last_frame_img = intro_clip.get_frame(last_frame_t)
            freeze_clip = ImageClip(last_frame_img).set_duration(intro_trans_dur)

            intro_extended = concatenate_videoclips([intro_clip, freeze_clip])
            main_clip = main_clip.crossfadein(intro_trans_dur)

            final_clip = concatenate_videoclips(
                [intro_extended, main_clip],
                method="compose",
                padding=-intro_trans_dur,
            )
            return final_clip, intro_clip.duration
        else:
            # 硬切
            return concatenate_videoclips(
                [intro_clip, main_clip], method="compose", padding=0
            ), intro_clip.duration

    def _mix_background_music(self, final_clip, category: str, bgm_start_time: float):
        """混合背景音乐"""
        bgm_file = self._resolve_bgm_file(category)
        if not bgm_file:
            return final_clip

        try:
            bgm_clip = AudioFileClip(bgm_file)
            bgm_duration = max(0, final_clip.duration - bgm_start_time)

            logger.debug(f"🎶 BGM Logic: File={bgm_file}")
            logger.debug(
                f"   Start Time={bgm_start_time:.2f}s, Final Duration={final_clip.duration:.2f}s, BGM Duration={bgm_duration:.2f}s"
            )

            if bgm_duration > 0:
                bgm_clip = afx.audio_loop(bgm_clip, duration=bgm_duration)
                bgm_clip = (
                    bgm_clip.fx(afx.audio_fadeout, 3.0)
                    .volumex(0.15)
                    .set_start(bgm_start_time)
                )

                original_audio = final_clip.audio
                final_audio = (
                    CompositeAudioClip([original_audio, bgm_clip])
                    if original_audio
                    else bgm_clip
                )

                final_clip = final_clip.set_audio(final_audio)
                logger.debug("   ✅ BGM mixed successfully.")
            else:
                logger.warning("   ⚠️ BGM duration <= 0, skipping mix.")

        except Exception as e:
            logger.traceback_and_raise(Exception(f"Failed to mix BGM: {e}"))

        return final_clip

    def _resolve_bgm_file(self, category: str):
        """解析背景音乐文件路径"""
        if not category or category not in C.CATEGORY_BGM:
            return None

        bgm_filename = C.CATEGORY_BGM[category]
        base_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        potential_path = os.path.join(base_dir, "assets", "music", bgm_filename)

        return potential_path if os.path.exists(potential_path) else None

    def assemble_video(
        self,
        scenes: List[Scene],
        output_filename: str = "final_video.mp4",
        topic: str = "",
        subtitle: str = "",
        category: str = "",
        intro_hook: str = "",
    ):
        """
        组装最终视频

        流程：
        1. 配置转场
        2. 生成封面
        3. 处理场景 clips
        4. 添加片尾
        5. 拼接主视频
        6. 添加片头
        7. 混合 BGM
        8. 输出视频文件
        """
        logger.info("Assembling video clips...")

        # 1. 设置转场配置
        trans_type, trans_duration, padding = self._setup_transition_config(category)

        # 2. 生成封面
        clips = []
        cover_clip = self._generate_cover_clip(scenes, topic, subtitle)
        if cover_clip:
            clips.append(cover_clip)

        # 3. 处理所有场景
        action_map = {
            "static": "static",
            "zoom_in": "zoom_in",
            "zoom_out": "zoom_out",
            "pan_left": "pan_left",
            "pan_right": "pan_right",
            "pan_up": "pan_up",
            "pan_down": "pan_down",
            "follow": "pan_right",
            "track": "pan_left",
        }

        scene_clips = self._process_scenes(
            scenes, action_map, trans_type, trans_duration, padding
        )
        clips.extend(scene_clips)

        if not clips:
            logger.error("No clips generated. Aborting video assembly.")
            return None

        # 4. 添加品牌片尾
        self._add_brand_outro(clips)

        # 5. 合并场景 clips 为主视频
        main_clip = concatenate_videoclips(clips, method="compose", padding=padding)

        # 6. 添加片头视频
        bgm_start_time = 0.0
        final_clip, bgm_start_time = self._add_custom_intro(
            main_clip, intro_hook, bgm_start_time
        )

        # 7. 混合背景音乐
        final_clip = self._mix_background_music(final_clip, category, bgm_start_time)

        # 8. 输出视频文件
        output_path = os.path.join(C.OUTPUT_DIR, output_filename)
        final_clip.write_videofile(
            output_path, fps=24, codec="libx264", audio_codec="aac"
        )
        logger.info(f"Video saved to {output_path}")
        return output_path
