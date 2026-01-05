import os
import sys
import numpy as np
from PIL import Image
from moviepy.editor import ImageClip

sys.path.append(os.getcwd())

from config.config import C
from steps.video.book import BookVideoAssembler
from steps.video.base import VideoAssemblerBase
from model.models import Scene


def debug_image_size():
    # 1. Setup Config Mock
    print(f"Initial C.VIDEO_SIZE: {getattr(C, 'VIDEO_SIZE', 'Not Set')}")
    # Force load if valid
    if not hasattr(C, "VIDEO_SIZE"):
        # Simulate loading (simplified)
        # Assuming config.yaml has image_size: "1024x1792"
        C.VIDEO_SIZE = (1024, 1792)
        print(f"Forced C.VIDEO_SIZE: {C.VIDEO_SIZE}")

    # 2. Mock Scene
    scene = Scene(
        scene_id=1,
        narration="Hello world",
        image_prompt="A cute rabbit",
        image_path="tests/output/test_assets/cover_base.png",  # Use exist mock
        narration_cn="你好世界",
    )

    # Ensure image exists
    os.makedirs("tests/output/test_assets", exist_ok=True)
    if not os.path.exists(scene.image_path):
        Image.new("RGB", (1024, 1024), (200, 100, 100)).save(scene.image_path)
        print(f"Created mock image at {scene.image_path} (1024x1024)")
    else:
        print(f"Using mock image at {scene.image_path}")

    # 3. Test _load_visual using BookVideoAssembler
    book_assembler = BookVideoAssembler()
    duration = 2.0

    print("\n--- Testing _load_visual ---")
    visual_clip = book_assembler._load_visual(scene, duration)
    if visual_clip:
        print(f"visual_clip size: {visual_clip.size}")
        print(f"Expected size: {C.VIDEO_SIZE}")
        if visual_clip.size != C.VIDEO_SIZE:
            print("❌ Mismatch in _load_visual return size!")
        else:
            print("✅ _load_visual return size matches C.VIDEO_SIZE")
    else:
        print("❌ _load_visual returned None")
        return

    # 4. Test BookVideoAssembler.create_book_layout_clip
    print("\n--- Testing create_book_layout_clip ---")

    final_clip = book_assembler.create_book_layout_clip(
        visual_clip,
        scene.narration,
        duration,
        visual_clip.size,  # Passing visual_clip.size as video_size
        subtitle_cn=scene.narration_cn,
    )

    print(f"Final Clip Size: {final_clip.size}")

    # 5. Check composition
    output_frame = "tests/output/debug_size_frame.png"
    final_clip.save_frame(output_frame, t=1.0)
    print(f"Saved debug frame to {output_frame}")


if __name__ == "__main__":
    debug_image_size()
