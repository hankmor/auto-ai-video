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
        # Always use book layout clip
        return self.create_book_layout_clip(visual_clip, scene.narration, duration, visual_clip.size)

    def create_book_layout_clip(self, visual_clip, text: str, duration: float, video_size: tuple):
        W, H = video_size
        bg_clip = ImageClip(np.full((H, W, 3), 0, dtype=np.uint8)).set_duration(duration)
        v_clip_resized = visual_clip.resize(width=W).set_position(("center", "center"))

        pane_height = int(H * 0.35)
        pane_bottom_margin = int(H * 0.15)
        pane_top = H - pane_height - pane_bottom_margin
        
        txt_img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(txt_img)
        
        pane_x_margin = int(W * 0.08)
        text_pad = int(W * 0.04)
        text_area_w = (W - 2 * pane_x_margin) - 2 * text_pad
        text_area_h = pane_height - 2 * text_pad
        text_start_x = pane_x_margin + text_pad
        text_start_y = pane_top + text_pad

        is_english = self._is_english_title(text)

        if is_english:
            base_font_size = int(W * 0.06)
            font = font_manager.get_font("english", base_font_size)
            words = text.split()
            lines = []
            current_line = []
            
            def get_line_width(line_words, f):
                return draw.textbbox((0, 0), " ".join(line_words), font=f)[2]

            for word in words:
                test_line = current_line + [word]
                if get_line_width(test_line, font) <= text_area_w:
                    current_line = test_line
                else:
                    if current_line: lines.append(" ".join(current_line))
                    current_line = [word]
            if current_line: lines.append(" ".join(current_line))

            max_lines = 4
            while len(lines) > max_lines and base_font_size > 20:
                base_font_size = int(base_font_size * 0.9)
                font = font_manager.get_font("english", base_font_size)
                lines = []
                current_line = []
                for word in words:
                    test_line = current_line + [word]
                    if get_line_width(test_line, font) <= text_area_w:
                        current_line = test_line
                    else:
                        if current_line: lines.append(" ".join(current_line))
                        current_line = [word]
                if current_line: lines.append(" ".join(current_line))

            line_height = int(base_font_size * 1.4)
            total_h = len(lines) * line_height
            start_y = text_start_y + (text_area_h - total_h) / 2
            
            box_pad = 15
            bg_box = [text_start_x - box_pad, start_y - box_pad, text_start_x + text_area_w + box_pad, start_y + total_h + box_pad]
            draw.rounded_rectangle(bg_box, radius=10, fill=(0, 0, 0, 140))

            current_y = start_y
            for line in lines:
                w_line = draw.textbbox((0, 0), line, font=font)[2]
                x_line = text_start_x + (text_area_w - w_line) / 2
                draw.text((x_line, current_y), line, font=font, fill=(255, 255, 255, 255))
                current_y += line_height
        
        else:
            fs_w = text_area_w / 20
            fs_h = text_area_h / 5
            font_size_hanzi = int(min(fs_w, fs_h))
            font_size_hanzi = max(font_size_hanzi, 24)
            font_size_pinyin = int(font_size_hanzi * 0.6)
            
            try:
                font_hanzi = font_manager.get_font("chinese", font_size_hanzi)
                font_pinyin = font_manager.get_font("chinese", font_size_pinyin)
            except Exception as e:
                logger.error(f"Failed to load font: {e}")
                return visual_clip
            
            chars_per_line = int(text_area_w / font_size_hanzi)
            chars_per_line = max(chars_per_line, 8)
            lines = [text[i : i + chars_per_line] for i in range(0, len(text), chars_per_line)]
            
            line_height = font_size_hanzi + font_size_pinyin + int(font_size_hanzi * 0.4)
            total_content_h = len(lines) * line_height
            start_y_offset = (text_area_h - total_content_h) / 2
            current_y = text_start_y + max(start_y_offset, 0)
            
            for line in lines:
                total_line_width = 0
                char_data = []
                pinyin_list = pypinyin.pinyin(line, style=pypinyin.Style.TONE)
                for i, char in enumerate(line):
                    bbox_c = draw.textbbox((0, 0), char, font=font_hanzi)
                    w_char = bbox_c[2] - bbox_c[0]
                    p_str = pinyin_list[i][0] if i < len(pinyin_list) else ""
                    bbox_p = draw.textbbox((0, 0), p_str, font=font_pinyin)
                    w_pin = bbox_p[2] - bbox_p[0]
                    cell_width = max(w_char, w_pin)
                    char_data.append([char, w_char, p_str, w_pin, cell_width])
                    total_line_width += cell_width + 4
                
                line_start_x = text_start_x + (text_area_w - total_line_width) / 2
                current_x = line_start_x
                y_p = current_y
                y_h = y_p + font_size_pinyin + 3
                
                for c, wc, ps, wp, cw in char_data:
                    cell_h = (y_h + font_size_hanzi) - y_p + 4
                    draw.rectangle([current_x - 2, y_p - 2, current_x + cw + 2, y_p + cell_h + 2], fill=(0, 0, 0, 140))
                    draw.text((current_x + (cw - wc) / 2, y_h), c, font=font_hanzi, fill=(255, 255, 255, 255))
                    draw.text((current_x + (cw - wp) / 2, y_p), ps, font=font_pinyin, fill=(200, 200, 200, 255))
                    current_x += cw + 4
                current_y += line_height

        txt_clip = ImageClip(np.array(txt_img)).set_duration(duration).set_position(("center", "center"))
        return CompositeVideoClip([bg_clip, v_clip_resized, txt_clip], size=(W, H))
