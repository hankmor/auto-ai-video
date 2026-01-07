import numpy as np
import pypinyin
from PIL import Image, ImageDraw
from moviepy.editor import ImageClip, CompositeVideoClip

from config.config import C
from model.models import Scene
from util.logger import logger
from steps.image.font import font_manager
from steps.video.base import VideoAssemblerBase


class BookVideoAssembler(VideoAssemblerBase):
    def _compose_scene(self, scene: Scene, visual_clip, duration: float):
        """Compose a scene with subtitle overlay"""
        W, H = visual_clip.size

        subtitle_text = scene.narration
        subtitle_cn = (
            getattr(scene, "narration_cn", "") if C.ENABLE_BILINGUAL_MODE else ""
        )

        logger.info(
            f"   🎬 Composing scene {scene.scene_id}: subtitle='{subtitle_text[:30]}...'"
        )

        book_layout_clip = self.create_book_layout_clip(
            visual_clip, subtitle_text, duration, (W, H), subtitle_cn
        )

        return book_layout_clip

    # ==================== Helper Methods ====================

    def _resize_visual_to_fill(self, visual_clip, target_size):
        """
        调整视觉clip以填充目标尺寸（Aspect-Fill）

        Args:
            visual_clip: 源视频clip
            target_size: (W, H) 目标尺寸

        Returns:
            调整后的clip
        """
        W, H = target_size
        src_w, src_h = visual_clip.size

        # 计算缩放比例（取最大值确保完全覆盖）
        scale = max(W / src_w, H / src_h)

        # 缩放
        scaled_clip = visual_clip.resize(scale)
        scaled_w, scaled_h = scaled_clip.size

        # 居中裁剪
        x_offset = (scaled_w - W) // 2
        y_offset = (scaled_h - H) // 2

        return scaled_clip.crop(
            x1=x_offset, y1=y_offset, x2=x_offset + W, y2=y_offset + H
        ).set_position(("center", "center"))

    def _calculate_text_layout_params(self, video_size):
        """
        计算文本布局参数

        Returns:
            dict: 包含所有布局参数
        """
        W, H = video_size

        return {
            "pane_height": int(H * 0.35),
            "pane_bottom_margin": int(H * 0.15),
            "pane_top": H - int(H * 0.35) - int(H * 0.15),
            "pane_x_margin": int(W * 0.08),
            "text_pad": int(W * 0.04),
            "text_area_w": (W - 2 * int(W * 0.08)) - 2 * int(W * 0.04),
            "text_area_h": int(H * 0.35) - 2 * int(W * 0.04),
            "text_start_x": int(W * 0.08) + int(W * 0.04),
            "text_start_y": H - int(H * 0.35) - int(H * 0.15) + int(W * 0.04),
        }

    def _wrap_english_text(self, text, font, max_width, draw):
        """
        自动换行英文文本

        Returns:
            list: 换行后的文本行列表
        """
        words = text.split()
        lines = []
        current_line = []

        def get_line_width(line_words):
            return draw.textbbox((0, 0), " ".join(line_words), font=font)[2]

        for word in words:
            test_line = current_line + [word]
            if get_line_width(test_line) <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]

        if current_line:
            lines.append(" ".join(current_line))

        return lines

    def _render_bilingual_subtitle(
        self, draw, text_en, text_cn, layout, video_size, draw_obj
    ):
        """
        渲染双语字幕（英文+中文拼音）

        Args:
            draw: PIL ImageDraw对象
            text_en: 英文文本
            text_cn: 中文文本
            layout: 布局参数
            video_size: (W, H)
            draw_obj: DrawObject用于计算宽度
        """
        W, H = video_size
        base_font_size = int(W * 0.05)
        font_en = font_manager.get_font("english", base_font_size)

        # 换行英文
        lines = self._wrap_english_text(
            text_en, font_en, layout["text_area_w"], draw_obj
        )

        # 计算英文高度
        line_height = int(base_font_size * 1.3)
        total_text_h = len(lines) * line_height + 40

        # 🔥 先计算中文实际高度（不渲染）
        chinese_h = self._calculate_chinese_pinyin_height(
            draw, text_cn, layout, base_font_size
        )

        total_content_h = total_text_h + chinese_h + 20  # 20是间距

        # 绘制背景框
        box_pad = 15
        bg_box = [
            layout["pane_x_margin"],
            layout["text_start_y"] - box_pad,
            W - layout["pane_x_margin"],
            layout["text_start_y"] + total_content_h + box_pad,
        ]
        draw.rounded_rectangle(bg_box, radius=10, fill=(0, 0, 0, 140))

        # 绘制英文
        current_y = layout["text_start_y"]
        for line in lines:
            w_line = draw_obj.textbbox((0, 0), line, font=font_en)[2]
            x_line = layout["text_start_x"] + (layout["text_area_w"] - w_line) / 2
            draw.text(
                (x_line, current_y), line, font=font_en, fill=(255, 255, 255, 255)
            )
            current_y += line_height

        current_y += 20  # 间距

        # 绘制中文拼音
        self._render_chinese_pinyin(
            draw, text_cn, current_y, layout, base_font_size, draw_obj
        )

    def _calculate_chinese_pinyin_height(self, draw, text_cn, layout, base_font_size):
        """
        计算中文拼音部分的实际渲染高度（不渲染）

        Returns:
            int: 实际需要的高度（像素）
        """
        fs_hanzi = int(base_font_size * 0.8)
        fs_pinyin = int(fs_hanzi * 0.6)
        font_hanzi = font_manager.get_font("chinese", fs_hanzi)
        font_pinyin = font_manager.get_font("chinese", fs_pinyin)

        pinyin_list = pypinyin.pinyin(text_cn, style=pypinyin.Style.TONE)
        rows = []
        current_row = []
        current_row_width = 0
        spacing = 4

        for i, char in enumerate(text_cn):
            bbox_c = draw.textbbox((0, 0), char, font=font_hanzi)
            w_char = bbox_c[2] - bbox_c[0]

            p_str = pinyin_list[i][0] if i < len(pinyin_list) else ""
            bbox_p = draw.textbbox((0, 0), p_str, font=font_pinyin)
            w_pin = bbox_p[2] - bbox_p[0]

            cell_width = max(w_char, w_pin)

            if current_row_width + cell_width > layout["text_area_w"]:
                rows.append(current_row)
                current_row = []
                current_row_width = 0

            current_row.append({"cell_width": cell_width})
            current_row_width += cell_width + spacing

        if current_row:
            rows.append(current_row)

        # 计算总高度
        row_height = fs_hanzi + fs_pinyin + 10
        total_height = len(rows) * row_height
        return total_height

    def _render_chinese_pinyin(
        self, draw, text_cn, start_y, layout, base_font_size, draw_obj
    ):
        """渲染中文+拼音"""
        fs_hanzi = int(base_font_size * 0.8)
        fs_pinyin = int(fs_hanzi * 0.6)
        font_hanzi = font_manager.get_font("chinese", fs_hanzi)
        font_pinyin = font_manager.get_font("chinese", fs_pinyin)

        pinyin_list = pypinyin.pinyin(text_cn, style=pypinyin.Style.TONE)
        rows = []
        current_row = []
        current_row_width = 0
        spacing = 4

        for i, char in enumerate(text_cn):
            bbox_c = draw.textbbox((0, 0), char, font=font_hanzi)
            w_char = bbox_c[2] - bbox_c[0]
            h_char = bbox_c[3] - bbox_c[1]

            p_str = pinyin_list[i][0] if i < len(pinyin_list) else ""
            bbox_p = draw.textbbox((0, 0), p_str, font=font_pinyin)
            w_pin = bbox_p[2] - bbox_p[0]
            h_pin = bbox_p[3] - bbox_p[1]

            cell_width = max(w_char, w_pin)

            if current_row_width + cell_width > layout["text_area_w"]:
                rows.append(current_row)
                current_row = []
                current_row_width = 0

            current_row.append(
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
            current_row_width += cell_width + spacing

        if current_row:
            rows.append(current_row)

        # Render Chinese Rows
        current_y = start_y
        for row in rows:
            row_width = sum(d["cell_width"] + spacing for d in row) - spacing
            start_x = layout["text_start_x"] + (layout["text_area_w"] - row_width) / 2

            y_pinyin = current_y
            y_hanzi = y_pinyin + fs_pinyin + 2

            curr_x = start_x
            for item in row:
                x_p = curr_x + (item["cell_width"] - item["w_pin"]) / 2
                draw.text(
                    (x_p, y_pinyin),
                    item["pinyin"],
                    font=font_pinyin,
                    fill=(200, 200, 200, 255),
                )

                x_c = curr_x + (item["cell_width"] - item["w_char"]) / 2
                draw.text(
                    (x_c, y_hanzi),
                    item["char"],
                    font=font_hanzi,
                    fill=(255, 230, 0, 255),
                )

                curr_x += item["cell_width"] + spacing

            current_y += fs_hanzi + fs_pinyin + 10

    # ==================== Main Method ====================

    def create_book_layout_clip(
        self,
        visual_clip,
        text: str,
        duration: float,
        video_size: tuple,
        subtitle_cn: str = "",
    ):
        """
        创建图书布局clip（重构后的主方法）

        现在这个方法只负责协调各个辅助方法
        """
        W, H = video_size

        # 1. 创建背景
        bg_clip = ImageClip(np.full((H, W, 3), 0, dtype=np.uint8)).set_duration(
            duration
        )

        # 2. 调整视觉clip
        logger.info(
            f"📝 字幕渲染: text='{text[:30]}...', subtitle_cn='{subtitle_cn[:20] if subtitle_cn else 'None'}...'"
        )
        logger.info(
            f"   双语模式={C.ENABLE_BILINGUAL_MODE}, has_subtitle_cn={bool(subtitle_cn)}"
        )

        v_clip_resized = self._resize_visual_to_fill(visual_clip, video_size)

        # 3. 计算布局参数
        layout = self._calculate_text_layout_params(video_size)

        # 4. 创建文本图层
        txt_img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(txt_img)

        # 5. 渲染字幕
        is_english = self._is_english_title(text)

        if C.ENABLE_BILINGUAL_MODE and subtitle_cn:
            self._render_bilingual_subtitle(
                draw, text, subtitle_cn, layout, video_size, draw
            )
        elif is_english:
            self._render_english_only_subtitle(draw, text, layout, video_size, draw)
        else:
            self._render_chinese_only_subtitle(draw, text, layout, video_size, draw)

        # 6. 合成
        txt_clip = ImageClip(np.array(txt_img)).set_duration(duration)
        return CompositeVideoClip([bg_clip, v_clip_resized, txt_clip], size=video_size)

    def _render_english_only_subtitle(self, draw, text, layout, video_size, draw_obj):
        """渲染纯英文字幕"""
        W, H = video_size
        base_font_size = int(W * 0.06)
        font = font_manager.get_font("english", base_font_size)

        # Wrap text
        lines = self._wrap_english_text(text, font, layout["text_area_w"], draw_obj)

        # Adjust font size if too many lines
        max_lines = 4
        while len(lines) > max_lines and base_font_size > 20:
            base_font_size = int(base_font_size * 0.9)
            font = font_manager.get_font("english", base_font_size)
            lines = self._wrap_english_text(text, font, layout["text_area_w"], draw_obj)

        # Calculate vertical positioning
        line_height = int(base_font_size * 1.4)
        total_h = len(lines) * line_height
        start_y = (
            layout["text_start_y"]
            + (layout.get("text_area_h", H * 0.35 - W * 0.08) - total_h) / 2
        )

        # Draw background box
        box_pad = 15
        bg_box = [
            layout["text_start_x"] - box_pad,
            start_y - box_pad,
            layout["text_start_x"] + layout["text_area_w"] + box_pad,
            start_y + total_h + box_pad,
        ]
        draw.rounded_rectangle(bg_box, radius=10, fill=(0, 0, 0, 140))

        # Draw text lines
        current_y = start_y
        for line in lines:
            w_line = draw_obj.textbbox((0, 0), line, font=font)[2]
            x_line = layout["text_start_x"] + (layout["text_area_w"] - w_line) / 2
            draw.text((x_line, current_y), line, font=font, fill=(255, 255, 255, 255))
            current_y += line_height

    def _render_chinese_only_subtitle(self, draw, text, layout, video_size, draw_obj):
        """渲染纯中文字幕"""
        W, H = video_size
        text_area_w = layout["text_area_w"]
        text_area_h = layout.get("text_area_h", int(H * 0.35) - 2 * int(W * 0.04))

        # Calculate font sizes
        fs_w = text_area_w / 20
        fs_h = text_area_h / 5
        font_size_hanzi = int(min(fs_w, fs_h))
        font_size_hanzi = max(font_size_hanzi, 24)
        font_size_pinyin = int(font_size_hanzi * 0.6)

        font_hanzi = font_manager.get_font("chinese", font_size_hanzi)
        font_pinyin = font_manager.get_font("chinese", font_size_pinyin)

        # Wrap text into lines
        chars_per_line = int(text_area_w / font_size_hanzi)
        chars_per_line = max(chars_per_line, 8)
        lines = [
            text[i : i + chars_per_line] for i in range(0, len(text), chars_per_line)
        ]

        # Calculate vertical positioning
        line_height = font_size_hanzi + font_size_pinyin + int(font_size_hanzi * 0.4)
        total_content_h = len(lines) * line_height
        start_y_offset = (text_area_h - total_content_h) / 2
        current_y = layout["text_start_y"] + max(start_y_offset, 0)

        # Render each line
        for line in lines:
            total_line_width = 0
            char_data = []
            pinyin_list = pypinyin.pinyin(line, style=pypinyin.Style.TONE)

            for i, char in enumerate(line):
                bbox_c = draw.textbbox((0, 0), char, font=font_hanzi)
                w_char = bbox_c[2] - bbox_c[0]

                p_str = ""
                if pinyin_list and i < len(pinyin_list) and pinyin_list[i]:
                    try:
                        p_str = pinyin_list[i][0]
                    except:
                        pass

                bbox_p = draw.textbbox((0, 0), p_str, font=font_pinyin)
                w_pin = bbox_p[2] - bbox_p[0]
                cell_width = max(w_char, w_pin)
                char_data.append([char, w_char, p_str, w_pin, cell_width])
                total_line_width += cell_width + 4

            # Draw line centered
            line_start_x = layout["text_start_x"] + (text_area_w - total_line_width) / 2
            current_x = line_start_x
            y_p = current_y
            y_h = y_p + font_size_pinyin + 3

            for c, wc, ps, wp, cw in char_data:
                cell_h = (y_h + font_size_hanzi) - y_p + 4
                draw.rectangle(
                    [current_x - 2, y_p - 2, current_x + cw + 2, y_p + cell_h + 2],
                    fill=(0, 0, 0, 140),
                )
                draw.text(
                    (current_x + (cw - wc) / 2, y_h),
                    c,
                    font=font_hanzi,
                    fill=(255, 255, 255, 255),
                )
                draw.text(
                    (current_x + (cw - wp) / 2, y_p),
                    ps,
                    font=font_pinyin,
                    fill=(200, 200, 200, 255),
                )
                current_x += cw + 4

            current_y += line_height
