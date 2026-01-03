import argparse
import asyncio
import os
import time

from config.config import C
from model.models import VideoScript
from steps.image.factory import ImageFactory
from steps.script.factory import ScriptGeneratorFactory
from steps.audio.factory import AudioStudioFactory
from steps.video.factory import VideoAssemblerFactory


async def run_test(topic: str, script_path: str = None, category: str = "成语故事"):
    print("🧪 开始集成测试（生成 1 幕迷你视频）")
    print(f"   - LLM: {C.LLM_PROVIDER or 'auto'} / {C.LLM_MODEL}")
    print(f"   - Image: {C.IMAGE_PROVIDER or 'auto'} / {C.IMAGE_MODEL}")
    print(f"   - Category: {category}")

    # 测试默认开启字幕（含拼音）
    C.ENABLE_SUBTITLES = True

    # 产物写入 tests/output/<时间戳>/
    base_output = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    test_out_dir = os.path.join(base_output, str(int(time.time())))
    os.makedirs(test_out_dir, exist_ok=True)

    # 覆盖输出目录与当前类目（影响语速/BGM/布局等）
    original_out = C.OUTPUT_DIR
    original_cat = getattr(C, "CURRENT_CATEGORY", "")
    C.OUTPUT_DIR = test_out_dir
    C.CURRENT_CATEGORY = category

    script: VideoScript | None = None

    try:
        # 1) 获取脚本：加载或生成
        if script_path and os.path.exists(script_path):
            print(f"\n📂 加载已有脚本: {script_path}")
            script = VideoScript.from_json(script_path)
        else:
            if not topic:
                raise ValueError("未提供 topic，且未指定 --script。")
            print(f"\n📝 生成脚本: {topic}（类目：{category}）")
            generator = ScriptGeneratorFactory.get_generator(category)
            script = generator.generate_script(topic=topic, category=category)

        if not script or not script.scenes:
            raise RuntimeError("脚本为空或不包含场景。")

        first_scene = script.scenes[0]
        print(f"\n🎬 使用第 1 幕进行端到端测试: Scene {first_scene.scene_id}")
        print(f"   - 旁白: {first_scene.narration[:60]}...")
        print(f"   - 提示词: {first_scene.image_prompt[:60]}...")

        # 2) 生成图片
        print("\n🎨 [1/3] 生成图片 ...")
        image_factory = ImageFactory()
        await image_factory.generate_images([first_scene], force=True)
        print(f"   ✅ Image: {first_scene.image_path}")

        # 3) 生成音频
        print("\n🔊 [2/3] 生成配音 ...")
        audio_studio = AudioStudioFactory.get_studio(category)
        await audio_studio.generate_audio([first_scene], force=True)
        print(f"   ✅ Audio: {first_scene.audio_path}")

        # 4) 合成视频（包含封面/字幕/布局/BGM 等逻辑）
        print("\n🎞️ [3/3] 合成视频 ...")
        assembler = VideoAssemblerFactory.get_assembler(category)
        final_video_path = assembler.assemble_video(
            [first_scene],
            output_filename="test_video.mp4",
            topic=script.topic,
            category=category,
        )
        print(f"   ✅ Video: {final_video_path}")

        # 保存脚本快照
        save_path = os.path.join(test_out_dir, "script_source.json")
        script.to_json(save_path)
        print(f"\n📦 输出目录: {test_out_dir}")
        print(f"📄 脚本: {save_path}")

    finally:
        C.OUTPUT_DIR = original_out
        C.CURRENT_CATEGORY = original_cat


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="集成测试：生成 1 幕迷你视频（用于排版/字幕/BGM 检查）")
    parser.add_argument("topic", type=str, nargs="?", help="视频主题（不传则必须使用 --script）")
    parser.add_argument("--script", type=str, help="已有 script.json 路径（跳过 LLM 步骤）")
    parser.add_argument("--category", type=str, default="成语故事", help="模拟类目（影响布局/BGM/语速等）")
    args = parser.parse_args()

    asyncio.run(run_test(args.topic, args.script, args.category))
