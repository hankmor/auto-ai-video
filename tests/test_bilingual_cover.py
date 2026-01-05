import os
import sys
from PIL import Image
import numpy as np

sys.path.append(os.getcwd())

from config.config import C
from steps.video.base import VideoAssemblerBase
from steps.video.book import BookVideoAssembler


def test_bilingual_cover():
    assembler = BookVideoAssembler()

    # Mock cover image (create one)
    os.makedirs("tests/output/test_assets", exist_ok=True)
    img_path = "tests/output/test_assets/cover_base.png"
    Image.new("RGB", (1080, 1920), (50, 50, 150)).save(img_path)

    output_path = "tests/output/test_bilingual_cover.png"

    title = "The Rabbit's Journey"
    subtitle = "小兔子的旅程"

    print(f"Generating Cover: {title} / {subtitle}")
    assembler.generate_cover(
        image_path=img_path, title=title, output_path=output_path, subtitle=subtitle
    )

    if os.path.exists(output_path):
        print(f"Generated cover at {output_path}")
    else:
        print("Failed to generate cover")


if __name__ == "__main__":
    test_bilingual_cover()
