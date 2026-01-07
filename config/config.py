import os
from dataclasses import dataclass, field
from util.logger import logger
from typing import Optional, List, Union

try:
    import yaml  # type: ignore
except ModuleNotFoundError:
    yaml = None

# google 大模型
MODEL_PROVIDER_GOOGLE = "google"
# openai 大模型
MODEL_PROVIDER_OPENAI = "openai"
# 火山大模型
MODEL_PROVIDER_VOLCENGINE = "volcengine"
# google gemini, https://ai.google.dev/gemini-api/docs/image-generation?hl=zh-cn
MODEL_GOOGLE_GEMINI_25 = "gemini-2.5-flash-image"
# google gemini, https://ai.google.dev/gemini-api/docs/image-generation?hl=zh-cn
MODEL_GOOGLE_GEMINI_30 = "gemini-3-pro-image-preview"
# openai gpt,https://platform.openai.com/docs/guides/images-vision
MODEL_OPENAI_GPT_o4_MINI = "o4-mini"
MODEL_OPENAI_GPT_41_MINI = "gpt-4.1-mini"
MODEL_OPENAI_GPT_41_NANO = "gpt-4.1-nano"
MODEL_OPENAI_GPT_5_MINI = "gpt-5-mini"
MODEL_OPENAI_GPT_5_NANO = "gpt-5-nano"
# 即梦2.1文生图，https://www.volcengine.com/docs/85621/1537648?lang=zh
MODEL_VOLCENGINE_JIMENG_21 = "jimeng_high_aes_general_v21_L"
# 即梦3.0文生图，https://www.volcengine.com/docs/85621/1616429?lang=zh
MODEL_VOLCENGINE_JIMENG_30 = "jimeng_t2i_v30"
# 即梦3.1文生图，https://www.volcengine.com/docs/85621/1756900?lang=zh
MODEL_VOLCENGINE_JIMENG_31 = "jimeng_t2i_v31"
# 豆包通用3.0文生图, https://www.volcengine.com/docs/86081/1804549?lang=zh
MODEL_VOLCENGINE_GEN_30 = "high_aes_general_v30l_zt2i"
# 豆包通用2.1文生图, https://www.volcengine.com/docs/86081/1804467?lang=zh
MODEL_VOLCENGINE_GEN_21 = "high_aes_general_v21_L"
# 即梦视频生成3.0 Pro，https://www.volcengine.com/docs/85621/1777001?lang=zh
MODEL_VOLCENGINE_GEN_30_PRO = "jimeng_ti2v_v30_pro"
# 即梦视频生成3.0 1080P, https://www.volcengine.com/docs/85621/1792711?lang=zh
MODEL_VOLCENGINE_GEN_30_1080P = "jimeng_t2v_v30_1080p"
# 即梦动作模仿,https://www.volcengine.com/docs/85621/1798351?lang=zh
MODEL_VOLCENGINE_ACT_M1 = "jimeng_dream_actor_m1_gen_video_cv"


@dataclass
class Config:
    # 项目路径 (Correctly points to project root, not config dir)
    ROOT_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ASSETS_DIR: str = os.path.join(ROOT_DIR, "assets")

    # 默认为当前目录的输出，或者从 yaml 加载
    OUTPUT_DIR: str = os.path.join(os.getcwd(), "output")

    # API 密钥（环境变量）
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    ARK_API_KEY: str = os.getenv("ARK_API_KEY", "")  # Doubao
    LUMA_API_KEY: str = os.getenv("LUMA_API_KEY", "")
    VOLC_ACCESS_KEY: str = os.getenv("VOLC_ACCESS_KEY", "")
    VOLC_SECRET_KEY: str = os.getenv("VOLC_SECRET_KEY", "")
    STABILITY_API_KEY: str = os.getenv("STABILITY_API_KEY", "")

    # LLM 设置
    LLM_MODEL: str = "doubao-pro-32k"
    LLM_PROVIDER: str = ""  # 显式提供商（可选）

    # 运行时上下文
    # OUTPUT_DIR: str = ""  <-- This was overriding line 12
    # CURRENT_CATEGORY: str = ""
    """
    Duplicate field definitions in dataclass causing issues.
    Removed OUTPUT_DIR here. Keeping CURRENT_CATEGORY but moving it if needed or leaving it.
    Actually, to avoid redefinition error if I just comment it out, I should just remove OUTPUT_DIR.
    """
    CURRENT_CATEGORY: str = ""

    # 图像生成设置
    IMAGE_MODEL: str = "mock"
    IMAGE_PROVIDER: str = "volcengine"  # openai, google, volcengine
    IMAGE_SIZE: str = "1024x1792"  # 9:16 竖屏
    IMAGE_RATIO: str = "9:16"
    IMAGE_STYLE: str = ""  # 默认风格
    STYLES: dict = field(default_factory=dict)  # 定义：style_key -> prompt
    CATEGORY_DEFAULTS: dict = field(default_factory=dict)  # 映射：category -> style_key
    CATEGORY_VOICES: dict = field(
        default_factory=dict
    )  # 映射：category -> [voice_list]
    CATEGORY_BGM: dict = field(default_factory=dict)  # 映射：category -> filename

    CATEGORY_STYLES: dict = field(
        default_factory=dict
    )  # 已弃用，保留以实现向后兼容或稍后移除
    CATEGORY_ALIASES: dict = field(default_factory=dict)  # 映射：alias -> category
    CATEGORY_LAYOUTS: dict = field(
        default_factory=dict
    )  # 映射：category -> layout_mode (movie/book)
    SENSITIVE_WORDS: dict = field(default_factory=dict)  # 敏感词替换

    # 动画设置
    ANIMATOR_TYPE: str = "mock"  # luma, stability, mock

    # 语音设置
    TTS_PROVIDER: str = "edge"  # edge, azure
    AZURE_TTS_KEY: str = os.getenv("AZURE_TTS_KEY", "")
    AZURE_TTS_REGION: str = os.getenv("AZURE_TTS_REGION", "eastus")

    # 火山 TTS
    VOLC_TTS_APPID: str = os.getenv("VOLC_TTS_APPID", "")
    VOLC_TTS_TOKEN: str = os.getenv("VOLC_TTS_TOKEN", "")
    VOLC_TTS_VOICE_TYPE: str = "zh_male_dayi_saturn_bigtts"
    VOLC_TTS_CLUSTER: str = os.getenv("VOLC_TTS_CLUSTER", "volcano_tts")

    # 音频设置
    TTS_VOICE: str = "zh-CN-XiaoxiaoNeural"  # 默认语音
    TTS_VOICE_TITLE: str = "zh-CN-XiaoxiaoNeural"  # 默认标题语音
    TTS_EMOTION: Optional[str] = None  # 情感参数 (Global Override)

    # 功能标志
    ENABLE_ANIMATION: bool = True
    ENABLE_SUBTITLES: bool = False
    ENABLE_BRAND_OUTRO: bool = True  # 品牌片尾
    ENABLE_EMOTIONAL_TTS: bool = False  # 情感语音

    # 自定义视频片头
    ENABLE_CUSTOM_INTRO: bool = False
    ENABLE_AI_INTRO_HOOK: bool = True  # 启用 AI 生成的片头引导语
    CUSTOM_INTRO_VIDEO_PATH: Union[str, List[str]] = "assets/videos/intro.mp4"
    CATEGORY_INTROS: dict = field(default_factory=dict)
    CUSTOM_INTRO_TRANSITION: str = "crossfade"
    CUSTOM_INTRO_TRANSITION_DURATION: float = 0.8

    # Custom Intro Dub
    ENABLE_CUSTOM_INTRO_DUB: bool = False
    CUSTOM_INTRO_DUB_VOICE: str = "zh-CN-YunxiNeural"
    CUSTOM_INTRO_DUB_STYLE: str = "cheerful"
    CUSTOM_INTRO_DUB_PITCH: str = "+0Hz"
    CUSTOM_INTRO_DUB_RATE: str = "+0%"

    # Bilingual Mode
    ENABLE_BILINGUAL_MODE: bool = False
    BILINGUAL_AUDIO_PAUSE: float = 1.0
    BILINGUAL_CN_VOICE: str = ""  # 双语模式中文朗读音色，为空则使用默认音色

    # Camera Effects
    CAMERA_ENABLE_EASING: bool = True  # 启用缓动函数
    CAMERA_ENABLE_ROTATION: bool = False  # 启用旋转效果
    CAMERA_ROTATION_DEGREE: float = 1.5  # 旋转角度
    CAMERA_MOVEMENT_INTENSITY: float = 1.15  # 运动强度

    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_CONSOLE_ENABLED: bool = True
    LOG_CONSOLE_LEVEL: str = "INFO"
    LOG_FILE_ENABLED: bool = False
    LOG_FILE_PATH: str = "logs/auto_maker.log"
    LOG_FILE_LEVEL: str = "DEBUG"
    LOG_FILE_MAX_BYTES: int = 10485760  # 10MB
    LOG_FILE_BACKUP_COUNT: int = 5

    # 字体设置
    FONTS: dict = field(default_factory=dict)

    # 内部缓存：避免重复打开/解析 config.yaml
    _yaml_path: str = field(default="config.yaml", init=False, repr=False)
    _yaml_data: Optional[dict] = field(default=None, init=False, repr=False)

    def _ensure_yaml_loaded(self):
        if self._yaml_data is not None:
            return
        if yaml is None:
            logger.warning(
                "未安装 PyYAML，已跳过 config.yaml 加载；将使用默认配置。"
                "你可以通过安装依赖（例如 `pip install pyyaml` 或使用项目的依赖管理工具）来启用 YAML 配置。"
            )
            self._yaml_data = {}
            return
        if os.path.exists(self._yaml_path):
            try:
                with open(self._yaml_path, "r", encoding="utf-8") as f:
                    self._yaml_data = yaml.safe_load(f) or {}
            except Exception as e:
                self._yaml_data = {}
                logger.traceback_and_raise(
                    Exception(f"读取配置文件失败：{self._yaml_path}，错误：{e}")
                )
        else:
            self._yaml_data = {}

    def load_from_yaml(self, path: str = "config.yaml"):
        self._yaml_path = path
        self._yaml_data = None
        self._ensure_yaml_loaded()
        data = self._yaml_data or {}
        if not data:
            return

        # 字体
        if "fonts" in data:
            self.FONTS = data["fonts"]

        # 模型
        if "models" in data:
            llm_val = data["models"].get("llm", self.LLM_MODEL)
            if isinstance(llm_val, dict):
                self.LLM_MODEL = llm_val.get("model", "")
                self.LLM_PROVIDER = llm_val.get("provider", "")
            else:
                self.LLM_MODEL = llm_val
                self.LLM_PROVIDER = ""  # 自动检测

            image_val = data["models"].get("image", self.IMAGE_MODEL)
            if isinstance(image_val, dict):
                self.IMAGE_MODEL = image_val.get("model", "")
                self.IMAGE_PROVIDER = image_val.get("provider", "")
            else:
                self.IMAGE_MODEL = image_val
                self.IMAGE_PROVIDER = ""  # 自动检测
            self.IMAGE_SIZE = data["models"].get(
                "image_size", self.IMAGE_SIZE
            )  # e.g. "1024x1792"
            try:
                w, h = self.IMAGE_SIZE.lower().split("x")
                self.VIDEO_SIZE = (int(w.strip()), int(h.strip()))
            except Exception:
                self.VIDEO_SIZE = (1080, 1920)

            self.IMAGE_STYLE = data["models"].get("image_style", self.IMAGE_STYLE)

            self.STYLES = data["models"].get("styles", {})
            self.CATEGORY_DEFAULTS = data["models"].get("category_defaults", {})
            # Load Voices based on Provider
            # If provider is volc, try to load category_voices_volc
            if self.TTS_PROVIDER == "volc":
                volc_voices = data["models"].get("category_voices_volc", {})
                if volc_voices:
                    self.CATEGORY_VOICES = volc_voices
                    logger.info("🎙️ Loaded Volcengine Voice Mappings")
                else:
                    self.CATEGORY_VOICES = data["models"].get("category_voices", {})
            else:
                self.CATEGORY_VOICES = data["models"].get("category_voices", {})
            self.CATEGORY_BGM = data["models"].get("category_bgm", {})
            self.CATEGORY_ALIASES = data["models"].get(
                "category_aliases", {}
            )  # 加载别名
            self.CATEGORY_LAYOUTS = data["models"].get(
                "category_layouts", {}
            )  # 加载布局
            self.CATEGORY_TRANSITIONS = data["models"].get(
                "category_transitions", {}
            )  # 加载转场配置
            self.ANIMATOR_TYPE = data["models"].get("animator", self.ANIMATOR_TYPE)
            self.TTS_PROVIDER = data["models"].get("tts_provider", self.TTS_PROVIDER)
            self.AZURE_TTS_KEY = data["models"].get("azure_tts_key", self.AZURE_TTS_KEY)
            self.AZURE_TTS_REGION = data["models"].get(
                "azure_tts_region", self.AZURE_TTS_REGION
            )

            # 只有当 YAML 中有值且非空时才覆盖，否则保留环境变量的值
            self.VOLC_TTS_APPID = (
                data["models"].get("volc_tts_appid") or self.VOLC_TTS_APPID
            )
            self.VOLC_TTS_TOKEN = (
                data["models"].get("volc_tts_token") or self.VOLC_TTS_TOKEN
            )

            # Voice Type 默认值如果是空字符串可能不合适，但这里主要防止 YAML 空串覆盖代码默认值
            self.VOLC_TTS_VOICE_TYPE = (
                data["models"].get("volc_tts_voice_type") or self.VOLC_TTS_VOICE_TYPE
            )

            self.VOLC_TTS_CLUSTER = (
                data["models"].get("volc_tts_cluster") or self.VOLC_TTS_CLUSTER
            )

            logger.debug(
                f"Volc Config Loaded -> appid: {self.VOLC_TTS_APPID}, cluster: {self.VOLC_TTS_CLUSTER}"
            )

            self.TTS_VOICE = data["models"].get("tts_voice", self.TTS_VOICE)
            self.TTS_VOICE_TITLE = data["models"].get(
                "tts_voice_title", self.TTS_VOICE
            )  # 如果未设置，则默认为主语音
            self.SENSITIVE_WORDS = data.get("sensitive_words", {})

        # 密钥（可选，但推荐使用环境变量）
        if "keys" in data:
            if data["keys"].get("openai_api_key"):
                self.OPENAI_API_KEY = data["keys"]["openai_api_key"]
            if data["keys"].get("gemini_api_key"):
                self.GEMINI_API_KEY = data["keys"]["gemini_api_key"]
            if data["keys"].get("ark_api_key"):
                self.ARK_API_KEY = data["keys"]["ark_api_key"]
            if data["keys"].get("luma_api_key"):
                self.LUMA_API_KEY = data["keys"]["luma_api_key"]
            if data["keys"].get("volc_access_key"):
                self.VOLC_ACCESS_KEY = data["keys"]["volc_access_key"]
            if data["keys"].get("volc_secret_key"):
                self.VOLC_SECRET_KEY = data["keys"]["volc_secret_key"]
            if data["keys"].get("stability_api_key"):
                self.STABILITY_API_KEY = data["keys"]["stability_api_key"]
            if data["keys"].get("sensitive_words"):
                self.SENSITIVE_WORDS = data["keys"]["sensitive_words"]

        # 项目
        if "project" in data:
            out_dir = data["project"].get("output_dir")
            if out_dir:
                self.OUTPUT_DIR = os.path.abspath(out_dir)

        # 功能
        if "features" in data:
            self.ENABLE_ANIMATION = data["features"].get(
                "enable_animation", self.ENABLE_ANIMATION
            )
            self.ENABLE_SUBTITLES = data["features"].get(
                "enable_subtitles", self.ENABLE_SUBTITLES
            )
            self.ENABLE_BRAND_OUTRO = data["features"].get(
                "enable_brand_outro", self.ENABLE_BRAND_OUTRO
            )
            self.ENABLE_EMOTIONAL_TTS = data["features"].get(
                "enable_emotional_tts", self.ENABLE_EMOTIONAL_TTS
            )

            # 自定义视频片头
            self.ENABLE_CUSTOM_INTRO = bool(
                data["features"].get("enable_custom_intro", self.ENABLE_CUSTOM_INTRO)
            )
            self.CUSTOM_INTRO_VIDEO_PATH = data["features"].get(
                "custom_intro_video_path", self.CUSTOM_INTRO_VIDEO_PATH
            )
            self.CATEGORY_INTROS = data["features"].get(
                "category_intros", self.CATEGORY_INTROS
            )
            self.CUSTOM_INTRO_TRANSITION = data["features"].get(
                "custom_intro_transition", self.CUSTOM_INTRO_TRANSITION
            )
            self.CUSTOM_INTRO_TRANSITION_DURATION = float(
                data["features"].get(
                    "custom_intro_transition_duration",
                    self.CUSTOM_INTRO_TRANSITION_DURATION,
                )
            )
            self.ENABLE_AI_INTRO_HOOK = data["features"].get(
                "enable_ai_intro_hook", self.ENABLE_AI_INTRO_HOOK
            )
            # 自定义片头配音
            self.ENABLE_CUSTOM_INTRO_DUB = data["features"].get(
                "enable_custom_intro_dub", self.ENABLE_CUSTOM_INTRO_DUB
            )
            self.CUSTOM_INTRO_DUB_VOICE = data["features"].get(
                "custom_intro_dub_voice", self.CUSTOM_INTRO_DUB_VOICE
            )
            self.CUSTOM_INTRO_DUB_STYLE = data["features"].get(
                "custom_intro_dub_style", self.CUSTOM_INTRO_DUB_STYLE
            )
            self.CUSTOM_INTRO_DUB_PITCH = data["features"].get(
                "custom_intro_dub_pitch", self.CUSTOM_INTRO_DUB_PITCH
            )
            self.CUSTOM_INTRO_DUB_RATE = data["features"].get(
                "custom_intro_dub_rate", self.CUSTOM_INTRO_DUB_RATE
            )
            # 双语模式配置 (Bilingual Mode)
            self.ENABLE_BILINGUAL_MODE = data["features"].get(
                "enable_bilingual_mode", self.ENABLE_BILINGUAL_MODE
            )
            self.BILINGUAL_AUDIO_PAUSE = float(
                data["features"].get(
                    "bilingual_audio_pause", self.BILINGUAL_AUDIO_PAUSE
                )
            )
            self.BILINGUAL_CN_VOICE = data["features"].get(
                "bilingual_cn_voice", self.BILINGUAL_CN_VOICE
            )

            # Camera Effects配置
            camera_effects = data["features"].get("camera_effects", {})
            if camera_effects:
                self.CAMERA_ENABLE_EASING = camera_effects.get(
                    "enable_easing", self.CAMERA_ENABLE_EASING
                )
                self.CAMERA_ENABLE_ROTATION = camera_effects.get(
                    "enable_rotation", self.CAMERA_ENABLE_ROTATION
                )
                self.CAMERA_ROTATION_DEGREE = float(
                    camera_effects.get("rotation_degree", self.CAMERA_ROTATION_DEGREE)
                )
                self.CAMERA_MOVEMENT_INTENSITY = float(
                    camera_effects.get(
                        "movement_intensity", self.CAMERA_MOVEMENT_INTENSITY
                    )
                )

        # 加载日志配置
        if "logging" in data:
            log_config = data["logging"]
            self.LOG_LEVEL = log_config.get("level", self.LOG_LEVEL)
            self.LOG_FORMAT = log_config.get("format", self.LOG_FORMAT)

            if "console" in log_config:
                self.LOG_CONSOLE_ENABLED = log_config["console"].get("enabled", True)
                self.LOG_CONSOLE_LEVEL = log_config["console"].get("level", "INFO")

            if "file" in log_config:
                self.LOG_FILE_ENABLED = log_config["file"].get("enabled", False)
                self.LOG_FILE_PATH = log_config["file"].get("path", self.LOG_FILE_PATH)
                self.LOG_FILE_LEVEL = log_config["file"].get("level", "DEBUG")
                self.LOG_FILE_MAX_BYTES = log_config["file"].get("max_bytes", 10485760)
                self.LOG_FILE_BACKUP_COUNT = log_config["file"].get("backup_count", 5)

    def get_speech_rate(self, category: str) -> str:
        """获取指定类目的语速配置，默认-15%"""
        if not hasattr(self, "_category_speech_rates"):
            self._ensure_yaml_loaded()
            models = (
                (self._yaml_data or {}).get("models", {}) if self._yaml_data else {}
            )
            self._category_speech_rates = models.get("category_speech_rates", {}) or {}
            logger.debug(f"已加载语速配置：{self._category_speech_rates}")

        rate = self._category_speech_rates.get(category, "-15%")
        logger.info(f"类目语速：{category} -> {rate}")
        return rate

    def get_scene_count_range(self, category: str = "") -> tuple[int, int]:
        """
        获取场景数量范围配置

        Args:
            category: 类目名称（可选）

        Returns:
            (min_scenes, max_scenes) 元组
        """
        if not hasattr(self, "_scene_count_config"):
            # 加载场景数量配置
            self._scene_count_config = {
                "default_min": 14,
                "default_max": 24,
                "category_overrides": {},
            }
            self._ensure_yaml_loaded()
            models = (
                (self._yaml_data or {}).get("models", {}) if self._yaml_data else {}
            )
            scene_count = models.get("scene_count", {}) or {}
            self._scene_count_config["default_min"] = scene_count.get("min", 18)
            self._scene_count_config["default_max"] = scene_count.get("max", 24)

            category_scene_count = models.get("category_scene_count", {}) or {}
            for cat, range_config in category_scene_count.items():
                self._scene_count_config["category_overrides"][cat] = (
                    range_config.get("min", 18),
                    range_config.get("max", 24),
                )

        # 如果有特定类目的配置，优先使用
        if category and category in self._scene_count_config["category_overrides"]:
            return self._scene_count_config["category_overrides"][category]

        # 否则使用全局默认值
        return (
            self._scene_count_config["default_min"],
            self._scene_count_config["default_max"],
        )

    @property
    def IS_BILINGUAL_MODE_ENABLED(self) -> bool:
        """
        判断当前类目是否启用双语模式
        同时满足两个条件：
        1. enable_bilingual_mode 开关为 True
        2. 当前类目为"英语绘本"
        """
        return self.ENABLE_BILINGUAL_MODE and self.CURRENT_CATEGORY == "英语绘本"


C = Config()
# 尝试从默认位置加载
C.load_from_yaml("config.yaml")

# 重新加载logger以应用配置
try:
    from util.logger import reload_logger

    reload_logger()
except Exception as e:
    # 如果reload失败，忽略错误（使用默认配置）
    pass

# 确保输出目录存在
if C.OUTPUT_DIR:
    os.makedirs(C.OUTPUT_DIR, exist_ok=True)
