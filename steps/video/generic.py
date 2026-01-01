import numpy as np
import pypinyin
from PIL import Image, ImageDraw
from moviepy.editor import ImageClip, CompositeVideoClip, concatenate_videoclips

from config.config import config
from model.models import Scene
from util.logger import logger
from steps.video.base import VideoAssemblerBase
from steps.image.font_manager import font_manager

class GenericVideoAssembler(VideoAssemblerBase):
    def _compose_scene(self, scene: Scene, visual_clip, duration: float):
        if config.ENABLE_SUBTITLES:
            subtitle_clip = self.create_subtitle_clip(scene.narration, duration, visual_clip.size)
            if subtitle_clip:
                return CompositeVideoClip([visual_clip, subtitle_clip])
        return visual_clip

    def create_subtitle_clip(self, text: str, duration: float, video_size: tuple):
        W, H = video_size
        chars_per_line = 16
        lines = [text[i : i + chars_per_line] for i in range(0, len(text), chars_per_line)]
        if not lines: return None

        duration_per_line = duration / len(lines)
        font_size_hanzi = int(W * 0.045)
        font_size_pinyin = int(font_size_hanzi * 0.6)
        sub_height = int(font_size_hanzi + font_size_pinyin + 20)

        try:
            font_hanzi = font_manager.get_font("chinese", font_size_hanzi)
            font_pinyin = font_manager.get_font("chinese", font_size_pinyin)
        except:
            return None

        outline_color = (0, 0, 0, 255)
        text_color = (255, 255, 255, 255)
        clips = []

        for line in lines:
            img = Image.new("RGBA", (W, sub_height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            def draw_text(x, y, t, f, stroke=2):
                draw.text((x, y), t, font=f, fill=text_color, stroke_width=stroke, stroke_fill=outline_color)

            pinyin_list = pypinyin.pinyin(line, style=pypinyin.Style.TONE)
            total_line_width = 0
            char_data = []
            
            for i, char in enumerate(line):
                bbox_c = draw.textbbox((0, 0), char, font=font_hanzi)
                w_char = bbox_c[2] - bbox_c[0]
                p_str = pinyin_list[i][0] if i < len(pinyin_list) else ""
                bbox_p = draw.textbbox((0, 0), p_str, font=font_pinyin)
                w_pin = bbox_p[2] - bbox_p[0]
                cell_width = max(w_char, w_pin)
                char_data.append({'char': char, 'w_char': w_char, 'p_str': p_str, 'w_pin': w_pin, 'cell_w': cell_width})
                total_line_width += cell_width + 2

            start_x = (W - total_line_width) / 2
            current_x = start_x
            y_base_pinyin = 5
            y_base_hanzi = y_base_pinyin + font_size_pinyin + 5

            for item in char_data:
                x_hanzi = current_x + (item["cell_w"] - item["w_char"]) / 2
                draw_text(x_hanzi, y_base_hanzi, item["char"], font_hanzi, stroke=3)
                x_pin = current_x + (item["cell_w"] - item["w_pin"]) / 2
                draw_text(x_pin, y_base_pinyin, item["p_str"], font_pinyin, stroke=2)
                current_x += item["cell_w"] + 2

            img_np = np.array(img)
            clips.append(ImageClip(img_np).set_duration(duration_per_line))

        if not clips: return None
        final_clip = concatenate_videoclips(clips, method="compose")
        target_y = int(H * 0.675 - sub_height / 2)
        return final_clip.set_position(("center", target_y))
