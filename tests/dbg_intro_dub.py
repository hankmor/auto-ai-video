import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import edge_tts
from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    concatenate_videoclips,
    ImageClip,
)
from config.config import C

# Configuration
TEST_OUTPUT_DIR = "tests/output/intro_dub"
INTRO_VIDEO_PATH = "assets/videos/1.mp4"
DUB_TEXT = (
    "哈喽小朋友们！欢迎来到智绘童梦！今天，我们要讲一个超级精彩的故事，你们准备好了吗？"
)
VOICE = "zh-CN-YunxiaNeural"
# Style options: cheerful, excited, friendly
STYLE = "cheerful"
PITCH = "+2Hz"
RATE = "+15%"


async def generate_dub_audio(text, output_path):
    print(f"🎤 Generating Dub Audio: {text}")
    print(f"   Voice: {VOICE}, Style: {STYLE}, Pitch: {PITCH}, Rate: {RATE}")

    communicate = edge_tts.Communicate(text, VOICE, pitch=PITCH, rate=RATE)
    await communicate.save(output_path)
    print(f"✅ Audio saved to {output_path}")


def assemble_dubbed_intro(video_path, audio_path, output_path):
    print(f"🎬 Assembling Cubbed Intro...")

    # 1. Load Video & Audio
    video = VideoFileClip(video_path)
    # Mute original
    video = video.without_audio()

    audio = AudioFileClip(audio_path)

    print(f"   Video Duration: {video.duration:.2f}s")
    print(f"   Audio Duration: {audio.duration:.2f}s")

    final_clip = None

    # Logic: If Audio > Video, use Freeze Frame Extension
    if audio.duration > video.duration:
        print("   ⚠️ Audio is longer than Video. Applying Freeze Frame Extension.")
        # Capture last frame
        last_frame_t = max(0, video.duration - 0.1)
        last_frame_img = video.get_frame(last_frame_t)

        # Calculate needed freeze duration
        freeze_dur = audio.duration - video.duration + 0.5  # Add small buffer

        freeze_clip = ImageClip(last_frame_img).set_duration(freeze_dur)

        # Extend video
        video_extended = concatenate_videoclips([video, freeze_clip])

        # Set audio
        final_clip = video_extended.set_audio(audio)
    else:
        print("   ✅ Video is longer than Audio. No extension needed.")
        final_clip = video.set_audio(audio)
        # Optional: Trim video to audio length? Or keep video length?
        # Usually keep video length for intro.

    # Export
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    final_clip.write_videofile(output_path, fps=24)
    print(f"🎉 Dubbed Intro saved to: {output_path}")


async def main():
    os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)
    audio_path = os.path.join(TEST_OUTPUT_DIR, "dub_audio.mp3")
    output_path = os.path.join(TEST_OUTPUT_DIR, "intro_dub_test.mp4")

    # 1. Generate Audio
    await generate_dub_audio(DUB_TEXT, audio_path)

    # 2. Assemble
    if os.path.exists(INTRO_VIDEO_PATH):
        assemble_dubbed_intro(INTRO_VIDEO_PATH, audio_path, output_path)
    else:
        print(f"❌ Intro video not found at {INTRO_VIDEO_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
