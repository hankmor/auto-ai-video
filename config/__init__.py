from util.logger import logger
import os
import random
from .config import C


def setup(
    category: str,
    topic: str,
    style_arg: str = None,
    enable_subs: bool = False,
    voice_arg: str = None,
    emotion_arg: str = None,
):
    """
    设置输出目录并配置图像风格。
    优先级：--style > --category 自动映射 > 配置默认值
    """
    # 如果存在标志，则覆盖字幕配置
    if enable_subs:
        C.ENABLE_SUBTITLES = True
        logger.info("📝 Subtitles Enabled via CLI")

    # 0. 解析分类别名
    final_category = category
    if category in C.CATEGORY_ALIASES:
        raw_cat = category
        final_category = C.CATEGORY_ALIASES[category]
        logger.info(f"🔄 Alias resolved: '{raw_cat}' -> '{final_category}')")
    else:
        logger.traceback_and_raise(Exception("Invalid category: " + category))

    # --- TTS 语音配置 ---
    # 优先级：--voice > category_voices（随机）> 配置默认值
    final_voice = C.TTS_VOICE

    if voice_arg:
        final_voice = voice_arg
        logger.info(f"🎤 Using custom voice override: {final_voice}")
    elif final_category in C.CATEGORY_VOICES:
        # 从列表中随机选择语音
        voice_pool = C.CATEGORY_VOICES[final_category]
        if voice_pool:
            final_voice = random.choice(voice_pool)
            logger.info(
                f"🎤 Randomly selected voice for category '{final_category}': {final_voice}"
            )

    C.TTS_VOICE = final_voice

    # --- TTS 情感配置 ---
    if emotion_arg:
        C.TTS_EMOTION = emotion_arg
        logger.info(f"🎭 Using TTS Emotion Override: {C.TTS_EMOTION}")

    # 1. 设置目录
    # 清理主题以用作文件夹名称
    safe_topic = (
        "".join(c for c in topic if c.isalnum() or c in (" ", "-", "_"))
        .strip()
        .replace(" ", "_")
    )
    if not safe_topic:
        logger.traceback_and_raise(Exception("Invalid topic: " + topic))

    # 输出根目录：优先使用 config.yaml 的 project.output_dir（即 config.OUTPUT_DIR）
    base_output = C.OUTPUT_DIR or os.path.join(os.getcwd(), "output")
    os.makedirs(base_output, exist_ok=True)

    # 分类目录（使用解析后的名称）
    cat_dir = os.path.join(base_output, final_category)

    # 项目目录
    project_dir = os.path.join(cat_dir, safe_topic)

    if not os.path.exists(project_dir):
        os.makedirs(project_dir, exist_ok=True)

    logger.info(f"📂 Output Directory: {project_dir}")
    C.OUTPUT_DIR = project_dir
    C.CURRENT_CATEGORY = final_category

    # 2. 配置图像风格
    final_style = C.IMAGE_STYLE

    first_pass_style = ""

    # 新逻辑：分类 -> 默认风格键 -> 风格提示词
    if final_category in C.CATEGORY_DEFAULTS:
        style_key = C.CATEGORY_DEFAULTS[final_category]
        if style_key in C.STYLES:
            cat_style = C.STYLES[style_key]
            logger.info(f"Category '{final_category}' uses style '{style_key}'.")
            final_style = cat_style
            first_pass_style = cat_style

    # 检查风格参数（最高优先级）
    if style_arg:
        # 检查 style_arg 是否为别名（例如 "cy"）
        resolved_style_key = style_arg
        if style_arg in C.CATEGORY_ALIASES:
            # 如果别名指向某个分类，尝试获取该分类的默认风格
            cat_alias = C.CATEGORY_ALIASES[style_arg]
            if cat_alias in C.CATEGORY_DEFAULTS:
                resolved_style_key = C.CATEGORY_DEFAULTS[cat_alias]
                logger.info(
                    f"Style Argument is an alias for category '{cat_alias}', using style '{resolved_style_key}'"
                )

        # 现在检查参数（或解析后的键）是否对应已定义的风格键
        if resolved_style_key in C.STYLES:
            logger.info(f"Using preset style for key: '{resolved_style_key}'")
            final_style = C.STYLES[resolved_style_key]
        else:
            # 假设它是原始提示词
            logger.info(f"Using custom style from CLI: '{style_arg}'")
            final_style = style_arg

        if first_pass_style and final_style != first_pass_style:
            logger.warning(f"⚠️ Overriding category default style with CLI style.")

    C.IMAGE_STYLE = final_style
    logger.info(f"Final Image Style: {C.IMAGE_STYLE[:60]}...")
