import os
import sys
import asyncio
from PIL import Image, ImageDraw
import numpy as np

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import C
from model.models import Scene
from steps.video.factory import VideoAssemblerFactory
from util.logger import logger


def create_dummy_assets(output_dir):
    os.makedirs(output_dir, exist_ok=True)

    # 1. Dummy Image (Main Content) - 1080x1920 (9:16)
    img_path = os.path.join(output_dir, "dummy_main.png")
    if not os.path.exists(img_path):
        img = Image.new("RGB", (1080, 1920), color=(73, 109, 137))
        d = ImageDraw.Draw(img)
        d.text((100, 900), "Hello Main Content", fill=(255, 255, 0), font_size=100)
        img.save(img_path)

    # 2. Dummy Audio - 2 seconds of silence (or tone if possible, but silence is easier without deps)
    # We'll use edge-tts to generate a quick generic audio if possible, or just skip if not crucial
    # For now, let's assume the user has a TTS environment or we mock it.
    # Actually, let's generate a simple tone using moviepy?
    # But assemble_video expects a file path.
    # Let's create a placeholder empty mp3 or similar.
    audio_path = os.path.join(output_dir, "dummy_audio.mp3")
    if not os.path.exists(audio_path):
        # Create a simple valid MP3 (header only might fail some players but ffmpeg might handle)
        # Better: use edge-tts if available, or just a known asset.
        # Let's try to find an existing asset?
        possible_asset = "assets/sfx/whoosh.mp3"  # Might exist?
        if os.path.exists(possible_asset):
            import shutil

            shutil.copy(possible_asset, audio_path)
        else:
            # Generate via edge-tts
            import subprocess

            subprocess.run(
                [
                    "edge-tts",
                    "--text",
                    "This is the main video content.",
                    "--write-media",
                    audio_path,
                ],
                check=False,
            )

    return img_path, audio_path


def main():
    # Setup Config
    # Simulate setup
    C.OUTPUT_DIR = "tests/output/debug_intro"
    if not os.path.isabs(C.OUTPUT_DIR):
        C.OUTPUT_DIR = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "output/debug_intro"
        )

    # C.VIDEO_SIZE = (1080, 1920)  # Target 9:16 - Commented out to test config loading
    print(f"DEBUG: C.VIDEO_SIZE from config: {getattr(C, 'VIDEO_SIZE', 'NOT SET')}")
    C.ENABLE_CUSTOM_INTRO = True
    C.ENABLE_CUSTOM_INTRO_DUB = True
    C.ENABLE_BRAND_OUTRO = True  # Enable Outro

    # 显式设置转场参数以方便观察
    # 设置较长的转场时间 (2.0秒) 以便清晰看到叠加淡入效果
    C.CUSTOM_INTRO_TRANSITION = "crossfade"
    C.CUSTOM_INTRO_TRANSITION_DURATION = 0.8
    print(
        f"⚙️ Configured Transition: {C.CUSTOM_INTRO_TRANSITION} ({C.CUSTOM_INTRO_TRANSITION_DURATION}s)"
    )

    # 指向您的通用片头 (确保 assets/videos/1.mp4 存在，或者改为您实际存在的片头)
    # 如果 config.yaml 里已经是 list，这里模拟 pick 一个
    # C.CUSTOM_INTRO_VIDEO_PATH = "assets/videos/1.mp4"
    # 如果想测试 config 读取逻辑，保持 config.yaml 的值, 但为了测试脚本独立性，强制指定一个存在的
    # 假设用户项目里有 assets/videos/1.mp4
    intro_path = "assets/videos/1.mp4"
    if not os.path.exists(intro_path):
        print(
            f"⚠️ Warning: {intro_path} not found. Trying to find any mp4 in assets/videos..."
        )
        v_dir = "assets/videos"
        # Adjust v_dir to be absolute if needed, assuming run from project root
        if not os.path.exists(v_dir):
            v_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "assets/videos",
            )

        if os.path.exists(v_dir):
            mp4s = [f for f in os.listdir(v_dir) if f.endswith(".mp4")]
            if mp4s:
                intro_path = os.path.join(v_dir, mp4s[0])
                print(f"👉 Found {intro_path}")
            else:
                print("❌ No intro videos found. Test will fail to show intro.")

    C.CUSTOM_INTRO_VIDEO_PATH = intro_path

    # Create assets
    print("🛠 Creating dummy assets...")
    img_path, audio_path = create_dummy_assets(C.OUTPUT_DIR)

    if not os.path.exists(audio_path):
        print(
            "❌ Failed to create dummy audio. Please insure edge-tts is installed or put a dummy.mp3 in tests/output/debug_intro/"
        )
        return

    # Create Dummy Scene
    scene = Scene(
        scene_id=1,
        narration="This is the main content following the intro.",
        image_prompt="Test Image",
        image_path=img_path,
        audio_path=audio_path,
    )

    print(f"🎬 Assembling video with intro: {intro_path}")
    print(f"   Target Size: {C.VIDEO_SIZE}")

    # Run Assembly
    assembler = VideoAssemblerFactory.get_assembler("generic")  # or 'history' etc

    output_path = assembler.assemble_video(
        [scene],
        output_filename="debug_intro_test.mp4",
        topic="Debug Intro",
        category="test",
        intro_hook="This is a test AI intro hook generated for debugging purposes. It should be dubbed and the video should be extended.",
    )

    if output_path and os.path.exists(output_path):
        print(f"\n✅ Success! Video generated at: {output_path}")
        print(f"👉 Please check if the intro size is correct (Aspect Fill).")
        # Open it
        os.system(f"open {output_path}")
    else:
        print("\n❌ Failed to generate video.")


if __name__ == "__main__":
    main()
