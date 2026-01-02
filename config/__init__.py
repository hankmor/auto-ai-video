from util.logger import logger
import os
import random
from .config import config


def setup(
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
    else:
        # 兜底：当 YAML 未加载/别名表为空时，仍保证目录使用全名
        # （避免出现 cy/et/sq/ls 等简称目录）
        builtin_aliases = {
            "cy": "成语故事",
            "et": "儿童绘本",
            "sq": "睡前故事",
            "ls": "历史故事",
        }
        if category in builtin_aliases:
            final_category = builtin_aliases[category]
            logger.info(f"🔄 内置别名解析：'{category}' -> '{final_category}'")

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

    # 输出根目录：优先使用 config.yaml 的 project.output_dir（即 config.OUTPUT_DIR）
    # 之前这里硬编码为 ./products，导致即使配置了 output_dir 也会写到 products 下。
    base_output = config.OUTPUT_DIR or os.path.join(os.getcwd(), "output")
    os.makedirs(base_output, exist_ok=True)

    # 分类目录（使用解析后的名称）
    cat_dir = os.path.join(base_output, final_category)

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
