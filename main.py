import argparse
import sys
import os
import random
import asyncio
import sys
import os

# 将项目根目录添加到 sys.path 以允许作为脚本执行
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import config
from util.logger import logger
from model.models import VideoScript
from steps.image.factory import ImageFactory
from steps.animator.luma_ai import LumaAnimator
from steps.animator.stability import StabilityAnimator
from steps.animator.mock import MockAnimator
from steps.script.factory import ScriptGeneratorFactory
from steps.audio.factory import AudioStudioFactory
from steps.video.factory import VideoAssemblerFactory


def setup_config(
    category: str,
    topic: str,
    style_arg: str = None,
    enable_subs: bool = False,
    voice_arg: str = None,
):
    """
    设置输出目录并配置图像风格。
    优先级：--style > --category 自动映射 > 配置默认值
    """
    # 如果存在标志，则覆盖字幕配置
    if enable_subs:
        config.ENABLE_SUBTITLES = True
        logger.info("📝 Subtitles Enabled via CLI")

    # 0. 解析分类别名
    final_category = category
    if category in config.CATEGORY_ALIASES:
        raw_cat = category
        final_category = config.CATEGORY_ALIASES[category]
        logger.info(f"🔄 Alias resolved: '{raw_cat}' -> '{final_category}')")

    # --- TTS 语音配置 ---
    # 优先级：--voice > category_voices（随机）> 配置默认值
    final_voice = config.TTS_VOICE

    if voice_arg:
        final_voice = voice_arg
        logger.info(f"🎤 Using custom voice override: {final_voice}")
    elif final_category in config.CATEGORY_VOICES:
        # 从列表中随机选择语音
        voice_pool = config.CATEGORY_VOICES[final_category]
        if voice_pool:
            final_voice = random.choice(voice_pool)
            logger.info(
                f"🎤 Randomly selected voice for category '{final_category}': {final_voice}"
            )

    config.TTS_VOICE = final_voice

    # 1. 设置目录
    # 清理主题以用作文件夹名称
    safe_topic = (
        "".join(c for c in topic if c.isalnum() or c in (" ", "-", "_"))
        .strip()
        .replace(" ", "_")
    )
    if not safe_topic:
        safe_topic = "untitled"

    # 基础产品目录
    base_products = os.path.join(os.getcwd(), "products")

    # 分类目录（使用解析后的名称）
    cat_dir = os.path.join(base_products, final_category)

    # 项目目录
    project_dir = os.path.join(cat_dir, safe_topic)

    if not os.path.exists(project_dir):
        os.makedirs(project_dir, exist_ok=True)

    logger.info(f"📂 Output Directory: {project_dir}")
    config.OUTPUT_DIR = project_dir
    config.CURRENT_CATEGORY = final_category

    # 2. 配置图像风格
    final_style = config.IMAGE_STYLE  # Start with default from yaml

    first_pass_style = ""

    # 新逻辑：分类 -> 默认风格键 -> 风格提示词
    if final_category in config.CATEGORY_DEFAULTS:
        style_key = config.CATEGORY_DEFAULTS[final_category]
        if style_key in config.STYLES:
            cat_style = config.STYLES[style_key]
            logger.info(f"ℹ️ Category '{final_category}' uses style '{style_key}'.")
            final_style = cat_style
            first_pass_style = cat_style
    # 回退到旧逻辑（如果用户尚未完全更新配置）
    elif final_category in config.CATEGORY_STYLES:
        cat_style = config.CATEGORY_STYLES[final_category]
        logger.info(f"ℹ️ Category '{final_category}' matches preset style (Legacy).")
        final_style = cat_style
        first_pass_style = cat_style

    # 检查风格参数（最高优先级）
    if style_arg:
        # 检查 style_arg 是否为别名（例如 "cygs"）
        resolved_style_key = style_arg
        if style_arg in config.CATEGORY_ALIASES:
            # 如果别名指向某个分类，尝试获取该分类的默认风格
            cat_alias = config.CATEGORY_ALIASES[style_arg]
            if cat_alias in config.CATEGORY_DEFAULTS:
                resolved_style_key = config.CATEGORY_DEFAULTS[cat_alias]
                logger.info(
                    f"🔄 Style Argument is an alias for category '{cat_alias}', using style '{resolved_style_key}'"
                )

        # 现在检查参数（或解析后的键）是否对应已定义的风格键
        if resolved_style_key in config.STYLES:
            logger.info(f"🎨 using preset style for key: '{resolved_style_key}'")
            final_style = config.STYLES[resolved_style_key]
        elif resolved_style_key in config.CATEGORY_STYLES:  # 旧版回退
            logger.info(f"🎨 using preset style for key: '{resolved_style_key}'")
            final_style = config.CATEGORY_STYLES[resolved_style_key]
        else:
            # 假设它是原始提示词
            logger.info(f"🎨 using custom style from CLI: '{style_arg}'")
            final_style = style_arg

        if first_pass_style and final_style != first_pass_style:
            logger.warning(f"⚠️ Overriding category default style with CLI style.")

    config.IMAGE_STYLE = final_style
    logger.info(f"🎨 Final Image Style: {config.IMAGE_STYLE[:60]}...")


def get_script_path() -> str:
    # 既然 config.OUTPUT_DIR 是动态设置的，我们直接使用它即可。
    return os.path.join(config.OUTPUT_DIR, "script.json")


async def run_step_script(
    topic: str, subtitle: str = "", force: bool = False, context_topic: str = None
):
    logger.info("=== STEP: Script Generation ===")
    if not topic:
        logger.error("Topic is required for script generation.")
        return

    # 重要：在此之前必须在 main() 中调用 setup_config
    path = get_script_path()

    if not force and os.path.exists(path):
        logger.info(
            f"📂 Found existing script at {path}, skipping generation. Use --force to overwrite."
        )
        try:
            script = VideoScript.from_json(path)
            # 重新打印摘要以供确认
            print("\n" + "=" * 50)
            print("🎬  剧本已加载 (SCRIPT LOADED)  🎬")
            print("=" * 50)
            print(f"📌 主题: {script.topic}")
            for scene in script.scenes:
                print(f"[{scene.scene_id}] 旁白: {scene.narration[:30]}...")
            print("=" * 50 + "\n")
            return
        except Exception as e:
            logger.warning(
                f"Failed to load existing script, regenerating... Error: {e}"
            )

    # script_gen = ScriptGenerator()
    script_gen = ScriptGeneratorFactory.get_generator(config.CURRENT_CATEGORY)

    # Calculate Series Profile Path
    series_profile_path = None
    if subtitle:
        # config.OUTPUT_DIR is .../products/Category/TopicSubtitle
        # We want to store profile in ".../products/Category/Topic/series_profile.json"

        product_dir = os.path.dirname(config.OUTPUT_DIR)  # .../products/Category
        # However, setup_config cleans the topic name. We need to be careful.
        # But generally, just stripping the subtitle part from the directory name might be tricky if not consistent.
        # Let's rely on the passed 'topic' (which is main_topic) to find the parent folder if possible?
        # Actually, in main(), we pass 'main_topic' as 'topic' arg to this function.
        # So 'topic' here IS 'main_topic' (e.g. "小狗钱钱").

        # We need to find where the Series Directory is.
        # If config.OUTPUT_DIR was created using "小狗钱钱:第一章", then the folder is "小狗钱钱第一章".
        # We probably want a parallel structure or a parent structure?
        # Current logic in main.py seems to flatten it: products/Category/TitleSubtitle.
        # So we can create products/Category/Title as the series root.

        series_dir_name = (
            "".join(c for c in topic if c.isalnum() or c in (" ", "-", "_"))
            .strip()
            .replace(" ", "_")
        )
        series_dir = os.path.join(product_dir, series_dir_name)

        if not os.path.exists(series_dir):
            os.makedirs(series_dir, exist_ok=True)
        series_profile_path = os.path.join(series_dir, "series_profile.json")

    try:
        script = script_gen.generate_script(
            topic,
            subtitle=subtitle,
            category=config.CURRENT_CATEGORY,
            series_profile_path=series_profile_path,
            context_topic=context_topic,  # Explicitly pass context topic
        )
        path = get_script_path()
        script.to_json(path)
        script.to_markdown(path.replace(".json", ".md"))
        logger.info(f"Script saved to {path} and {path.replace('.json', '.md')}")

        print("\n" + "=" * 50)
        print("🎬  剧本生成概要 (SCRIPT SUMMARY)  🎬")
        print("=" * 50)
        print(f"📌 主题: {script.topic}")
        print(f"🎨 风格: {script.visual_style}")
        print("-" * 30)
        for scene in script.scenes:
            print(f"[{scene.scene_id}] 旁白: {scene.narration}")
            print(f"    画面: {scene.image_prompt[:80]}...")
        print("=" * 50 + "\n")

    except Exception as e:
        logger.error(f"Script generation failed: {e}")


async def run_step_image(topic: str, force: bool = False):
    logger.info("=== STEP: Image Generation ===")
    path = get_script_path()
    if not os.path.exists(path):
        logger.error(f"Script file not found at {path}. Run --step script first.")
        return

    script = VideoScript.from_json(path)
    image_factory = ImageFactory()
    await image_factory.generate_images(script.scenes, force=force)
    script.to_json(path)  # 保存更新后的路径
    logger.info("Images generated and script updated.")


async def run_step_animate(topic: str):
    logger.info("=== STEP: Animation (I2V) ===")
    path = get_script_path()
    if not os.path.exists(path):
        logger.error(f"Script file not found at {path}.")
        return

    script = VideoScript.from_json(path)

    animator = None
    if config.ANIMATOR_TYPE == "luma" and config.LUMA_API_KEY:
        logger.info("Using Luma Animator.")
        animator = LumaAnimator()
    elif config.ANIMATOR_TYPE == "stability" and config.STABILITY_API_KEY:
        logger.info("Using Stability Animator.")
        animator = StabilityAnimator()
    elif config.ANIMATOR_TYPE == "jimeng":
        logger.info("Using Jimeng Animator.")
        # Lazy import to avoid circular dependency if any (though animator imports provider which imports config)
        from auto_maker.animator import JimengAnimator

        animator = JimengAnimator()
    elif config.ANIMATOR_TYPE == "mock":
        logger.info("Using Mock Animator.")
        animator = MockAnimator()
    else:
        logger.warning(
            f"Animator type '{config.ANIMATOR_TYPE}' not configured or missing key. Falling back to Mock."
        )
        animator = MockAnimator()

    for scene in script.scenes:
        await animator.animate_scene(scene)

    script.to_json(path)
    logger.info("Animation complete and script updated.")


async def run_step_audio(topic: str, force: bool = False):
    logger.info("=== STEP: Audio Generation ===")
    path = get_script_path()
    if not os.path.exists(path):
        logger.error(f"Script file not found at {path}.")
        return

    script = VideoScript.from_json(path)
    # audio_studio = AudioStudio()
    audio_studio = AudioStudioFactory.get_studio(config.CURRENT_CATEGORY)
    await audio_studio.generate_audio(script.scenes, force=force)
    script.to_json(path)
    logger.info("Audio generated and script updated.")


async def run_step_video(topic: str, subtitle: str = ""):
    logger.info("=== STEP: Video Assembly ===")
    path = get_script_path()
    if not os.path.exists(path):
        logger.error(f"Script file not found at {path}.")
        return

    script = VideoScript.from_json(path)
    # assembler = VideoAssembler()
    assembler = VideoAssemblerFactory.get_assembler(config.CURRENT_CATEGORY)
    output_path = assembler.assemble_video(
        script.scenes,
        topic=script.topic,
        subtitle=subtitle,
        category=config.CURRENT_CATEGORY,
    )
    if output_path:
        logger.info(f"SUCCESS! Video available at: {output_path}")

        # 生成作品发布信息
        try:
            from auto_maker.metadata_generator import MetadataGenerator

            generator = MetadataGenerator()

            # 使用脚本中的 summary 字段作为摘要
            summary = (
                script.summary
                if script.summary
                else (script.scenes[0].narration if script.scenes else None)
            )

            generator.save_metadata(
                output_dir=config.OUTPUT_DIR,
                topic=script.topic,
                category=config.CURRENT_CATEGORY,
                summary=summary,
            )
            logger.info(f"✅ Metadata generated: {config.OUTPUT_DIR}/metadata.md")
        except Exception as e:
            logger.warning(f"Failed to generate metadata: {e}")


async def run_all(
    topic: str, subtitle: str = "", force: bool = False, context_topic: str = None
):
    await run_step_script(topic, subtitle, force, context_topic)
    await run_step_image(topic, force)
    if config.ENABLE_ANIMATION and config.ANIMATOR_TYPE != "none":
        await run_step_animate(topic)
    await run_step_audio(topic, force)
    await run_step_video(topic, subtitle)


def main():
    parser = argparse.ArgumentParser(description="Auto Video Maker")
    parser.add_argument(
        "--topic",
        type=str,
        help="Topic for the video generation",
        default="DefaultTopic",
    )
    parser.add_argument(
        "--category",
        type=str,
        help="Category/Series for organization (e.g. History, Bedtime)",
        default="uncategorized",
    )
    parser.add_argument(
        "--style",
        type=str,
        help="Override image style (e.g. 'Pixar', 'Ink Wash') or use a preset key",
        default=None,
    )
    parser.add_argument(
        "--subtitles", "-sb", action="store_true", help="Enable Pinyin subtitles"
    )
    parser.add_argument(
        "--voice",
        type=str,
        help="Override TTS voice (e.g. zh-CN-YunxiNeural)",
        default=None,
    )
    parser.add_argument(
        "--step",
        type=str,
        help="Step to run: script, image, animate, audio, video, all",
        default="all",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force regeneration of assets even if they exist",
    )
    args = parser.parse_args()

    # 解析主题和副标题
    full_topic = args.topic
    main_topic = full_topic
    subtitle = ""

    # 支持中文冒号和英文冒号
    if "：" in full_topic:
        parts = full_topic.split("：", 1)
        main_topic = parts[0].strip()
        subtitle = parts[1].strip()
    elif ":" in full_topic:
        parts = full_topic.split(":", 1)
        main_topic = parts[0].strip()
        subtitle = parts[1].strip()

    # 解析 Cover vs Context (例如 "小狗钱钱|小狗钱钱(少儿版)")
    context_topic = main_topic  # default
    if "|" in main_topic:
        parts = main_topic.split("|", 1)
        main_topic = parts[0].strip()  # Cover Title (Clean)
        context_topic = parts[1].strip()  # Context Title (Version info)
        logger.info(
            f"📘 Advanced Topic Parsing: Cover='{main_topic}', Context='{context_topic}'"
        )

    if subtitle:
        logger.info(
            f"📖 Detected Multi-part Topic: Title='{main_topic}', Subtitle='{subtitle}'"
        )

    # 设置目录和配置 (使用 Clean Title + Subtitle 以保证目录整洁)
    # Reconstruct a clean topic string for directory generation
    clean_full_topic = f"{main_topic}:{subtitle}" if subtitle else main_topic
    setup_config(
        args.category, clean_full_topic, args.style, args.subtitles, args.voice
    )

    # 确定主题：如果步骤不是 'script' 且主题缺失，我们可能会假设默认值或报错。
    # 但对于 'script' 步骤，主题是必不可少的。
    if args.step == "script" and args.topic == "DefaultTopic":
        logger.warning("Using default topic 'DefaultTopic'. Use --topic to specify.")

    loop = asyncio.get_event_loop()

    if args.step == "script":
        loop.run_until_complete(
            run_step_script(main_topic, subtitle, args.force, context_topic)
        )
    elif args.step == "image":
        loop.run_until_complete(
            run_step_image(main_topic, args.force)
        )  # Image generation doesn't need subtitle explicitly, it reads script
    elif args.step == "animate":
        loop.run_until_complete(run_step_animate(main_topic))
    elif args.step == "audio":
        loop.run_until_complete(run_step_audio(main_topic, args.force))
    elif args.step == "video":
        loop.run_until_complete(run_step_video(main_topic, subtitle))
    elif args.step == "all":
        loop.run_until_complete(
            run_all(main_topic, subtitle, args.force, context_topic)
        )
    else:
        logger.error(f"Unknown step: {args.step}")


if __name__ == "__main__":
    main()
