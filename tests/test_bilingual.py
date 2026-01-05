import os
import sys
import numpy as np
from PIL import Image
from moviepy.editor import ImageClip

sys.path.append(os.getcwd())

from config.config import C
from steps.video.book import BookVideoAssembler
from steps.image.font import font_manager


def test_bilingual_layout():
    # 1. Setup Config
    C.ENABLE_BILINGUAL_MODE = True

    # 2. Mock Assembler
    assembler = BookVideoAssembler()

    # 3. Mock Data
    video_size = (1080, 1920)
    text_en = "One day, a little rabbit went out to find waiting for his mother."
    text_cn = "有一天，小兔子出门去找妈妈。"

    # 4. Create Mock Visual Clip (Red background)
    visual_clip = ImageClip(np.full((1920, 1080, 3), 100, dtype=np.uint8)).set_duration(
        2
    )

    # 5. Generate Layout Clip
    print("Generating Layout Clip...")
    layout_clip = assembler.create_book_layout_clip(
        visual_clip, text_en, duration=2.0, video_size=video_size, subtitle_cn=text_cn
    )

    # 6. Save Frame
    output_path = "tests/output/test_bilingual_frame.png"
    os.makedirs("tests/output", exist_ok=True)
    layout_clip.save_frame(output_path, t=1.0)
    print(f"Saved frame to {output_path}")


if __name__ == "__main__":
    test_bilingual_layout()
