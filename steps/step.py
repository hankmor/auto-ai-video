import os
from config.config import config
from util.logger import logger
from model.models import VideoScript
from steps.script.factory import ScriptGeneratorFactory
from steps.image.factory import ImageFactory
from steps.animator.luma_ai import LumaAnimator
from steps.animator.stability import StabilityAnimator
from steps.animator.mock import MockAnimator
from steps.animator.jimeng import JimengAnimator
from steps.audio.factory import AudioStudioFactory
from steps.video.factory import VideoAssemblerFactory
from steps.video.metadata_generator import MetadataGenerator

SCRIPT = "script"
IMAGE = "image"
ANIMATE = "animate"
AUDIO = "audio"
VIDEO = "video"
ALL = "all"


async def run_step_script(
    topic: str, subtitle: str = "", force: bool = False, context_topic: str = None
):
    path = os.path.join(config.OUTPUT_DIR, "script.json")
    logger.info("=== STEP: Script Generation ===")
    if not topic:
        logger.error("Topic is required for script generation.")
        return

    if not force and os.path.exists(path):
        logger.info(
            f"📂 Found existing script at {path}, skipping generation. Use --force to overwrite."
        )
        try:
            script = VideoScript.from_json(path)
            # 重新打印摘要以供确认
            print("\n" + "=" * 50)
            print("剧本已加载 (SCRIPT LOADED)")
            print("=" * 50)
            print(f"主题: {script.topic}")
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
        # series_profile 放在同一类目目录下的“书名”文件夹里，便于多章节共享角色/设定
        product_dir = os.path.dirname(config.OUTPUT_DIR)  # .../<output_dir>/<category>

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
    path = os.path.join(config.OUTPUT_DIR, "script.json")
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
    path = os.path.join(config.OUTPUT_DIR, "script.json")
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
    path = os.path.join(config.OUTPUT_DIR, "script.json")
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
    path = os.path.join(config.OUTPUT_DIR, "script.json")
    if not os.path.exists(path):
        logger.error(f"Script file not found at {path}.")
        return

    script = VideoScript.from_json(path)
    # assembler = VideoAssembler()
    assembler = VideoAssemblerFactory.get_assembler(config.CURRENT_CATEGORY)
    output_path = assembler.assemble_video(
        script.scenes,
        topic=topic,
        subtitle=subtitle,
        category=config.CURRENT_CATEGORY,
    )
    if output_path:
        logger.info(f"SUCCESS! Video available at: {output_path}")

        # 生成作品发布信息
        try:
            generator = MetadataGenerator()

            # 使用脚本中的 summary 字段作为摘要
            summary = (
                script.summary
                if script.summary
                else (script.scenes[0].narration if script.scenes else None)
            )

            generator.save_metadata(
                output_dir=config.OUTPUT_DIR,
                topic=topic,
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


async def run_all_with_cover(
    topic: str,
    subtitle: str = "",
    force: bool = False,
    context_topic: str = None,
    cover_title: str = "",
    cover_subtitle: str = "",
):
    """
    全流程：脚本/图片/音频使用 topic+subtitle，封面（视频）使用 cover_title+cover_subtitle。
    不提供 cover_* 时会回退到 topic/subtitle。
    """
    await run_step_script(topic, subtitle, force, context_topic)
    await run_step_image(topic, force)
    if config.ENABLE_ANIMATION and config.ANIMATOR_TYPE != "none":
        await run_step_animate(topic)
    await run_step_audio(topic, force)
    await run_step_video(cover_title or topic, cover_subtitle or subtitle)
