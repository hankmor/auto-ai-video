import os
from dataclasses import dataclass, field
from util.logger import logger
from typing import Optional

try:
    import yaml  # type: ignore
except ModuleNotFoundError:
    yaml = None

@dataclass
class Config:
    # 项目路径
    ROOT_DIR: str = os.path.dirname(os.path.abspath(__file__))
    ASSETS_DIR: str = os.path.join(ROOT_DIR, "assets")
    
    # 默认为当前目录的输出，或者从 yaml 加载
    OUTPUT_DIR: str = os.path.join(os.getcwd(), "output")

    # API 密钥（环境变量）
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    ARK_API_KEY: str = os.getenv("ARK_API_KEY", "") # Doubao
    LUMA_API_KEY: str = os.getenv("LUMA_API_KEY", "")
    VOLC_ACCESS_KEY: str = os.getenv("VOLC_ACCESS_KEY", "")
    VOLC_SECRET_KEY: str = os.getenv("VOLC_SECRET_KEY", "")
    STABILITY_API_KEY: str = os.getenv("STABILITY_API_KEY", "")

    # LLM 设置
    LLM_MODEL: str = "doubao-pro-32k" 
    LLM_PROVIDER: str = "" # 显式提供商（可选）
    
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
    IMAGE_PROVIDER: str = "volcengine" # openai, google, volcengine
    IMAGE_SIZE: str = "1024x1792" # 9:16 竖屏
    IMAGE_RATIO: str = "9:16"
    IMAGE_STYLE: str = "" # 默认风格
    STYLES: dict = field(default_factory=dict) # 定义：style_key -> prompt
    CATEGORY_DEFAULTS: dict = field(default_factory=dict) # 映射：category -> style_key
    CATEGORY_VOICES: dict = field(default_factory=dict)   # 映射：category -> [voice_list]
    CATEGORY_BGM: dict = field(default_factory=dict)      # 映射：category -> filename
    
    CATEGORY_STYLES: dict = field(default_factory=dict) # 已弃用，保留以实现向后兼容或稍后移除
    CATEGORY_ALIASES: dict = field(default_factory=dict) # 映射：alias -> category
    CATEGORY_LAYOUTS: dict = field(default_factory=dict) # 映射：category -> layout_mode (movie/book)
    SENSITIVE_WORDS: dict = field(default_factory=dict) # 敏感词替换
    
    # 动画设置
    ANIMATOR_TYPE: str = "mock" # luma, stability, mock

    # 音频设置
    TTS_VOICE: str = "zh-CN-XiaoxiaoNeural" # 默认语音
    TTS_VOICE_TITLE: str = "zh-CN-XiaoxiaoNeural" # 默认标题语音

    # 功能标志
    ENABLE_ANIMATION: bool = True
    ENABLE_SUBTITLES: bool = False
    ENABLE_BRAND_OUTRO: bool = True    # 品牌片尾
    ENABLE_EMOTIONAL_TTS: bool = False # 情感语音
    # 片头引导语音（Hook）：封面/标题语音前播放一段引导语
    ENABLE_HOOK_VOICE: bool = False
    HOOK_VOICE_TEXT: str = ""
    CATEGORY_HOOK_VOICE_TEXT: dict = field(default_factory=dict)  # 映射：category -> hook_text
    HOOK_INTRO_PAUSE: float = 0.25
    HOOK_INTRO_FLIP: float = 0.6
    HOOK_INTRO_BG_MODE: str = "brand"  # brand / black
    HOOK_INTRO_SFX_PATH: str = "assets/sfx/whoosh.mp3"
    HOOK_INTRO_SFX_VOLUME: float = 0.5
    HOOK_INTRO_SFX_START: float = 0.22  # 音效起始时间（秒），略晚于画面出现更舒服
    HOOK_INTRO_SFX_TRIM_START: float = 0.08  # 从音效的哪个时间点开始截取（秒）
    HOOK_INTRO_SFX_TRIM_END: float = 0.45    # 截取到哪个时间点（秒），<=0 表示到结尾
    HOOK_INTRO_SFX_FADE_IN: float = 0.02     # 淡入（秒）
    HOOK_INTRO_SFX_FADE_OUT: float = 0.08    # 淡出（秒）
    
    # 片头吉祥物（绘宝）动画：在 brand_intro.png 上叠加“弹入 + 漂浮 + 眨眼”
    ENABLE_MASCOT_INTRO: bool = True
    MASCOT_INTRO_PATH: str = "assets/image/mascot_huibao_transparent.png"
    MASCOT_INTRO_BLINK_PATH: str = "assets/image/mascot_huibao_blink_transparent.png"
    MASCOT_INTRO_SCALE: float = 0.42          # 吉祥物宽度占画面宽度比例
    MASCOT_INTRO_X: float = 0.62              # 吉祥物左上角 x 位置比例（0~1）
    MASCOT_INTRO_Y: float = 0.63              # 吉祥物左上角 y 位置比例（0~1）
    MASCOT_INTRO_ENTRY: float = 0.7           # 弹入时长（秒）
    MASCOT_INTRO_FLOAT: float = 10.0          # 漂浮幅度（像素）
    MASCOT_INTRO_BLINK_INTERVAL: float = 2.2  # 眨眼间隔（秒）
    MASCOT_INTRO_BLINK_DUR: float = 0.12      # 单次眨眼持续（秒）
    MASCOT_INTRO_SHOW_NAME: bool = False      # 是否在片头显示“绘宝”名牌（默认不显示）
    
    # 绘宝“分段出场”动画（用于 hook 片头的更强表演）
    # 目标：
    # 1) 先从左侧中部弹出脑袋并眨眼（1s）
    # 2) 停 0.5s 后全身从左侧跳入到屏幕中间
    # 3) 再停 0.2s 后开始朗读 hook，并在朗读期间做“讲解动作”（轻微摆动/点头）
    MASCOT_STAGE1_DUR: float = 1.0
    MASCOT_STAGE1_BLINKS: int = 2
    MASCOT_STAGE1_BLINK_DUR: float = 0.10
    MASCOT_STAGE2_PAUSE: float = 0.5
    MASCOT_STAGE2_DUR: float = 0.6
    MASCOT_STAGE2_JUMP: float = 0.10  # 跳跃高度（相对屏幕高度比例）
    MASCOT_STAGE3_PAUSE: float = 0.2
    MASCOT_GESTURE_ROT_DEG: float = 6.0   # 讲解时摆动角度（度）
    MASCOT_GESTURE_FREQ: float = 2.0      # 讲解时摆动频率（Hz）
    MASCOT_GESTURE_SHIFT: float = 0.008   # 讲解时左右轻移（相对屏幕宽度比例）
    MASCOT_GESTURE_BOB: float = 0.006     # 讲解时上下轻摆（相对屏幕高度比例）
    
    # 脑袋裁剪（从全身图里裁一块当“脑袋”用），格式：[x, y, w, h]
    # - 如果数值都 <=1：按比例裁剪（推荐）
    # - 如果存在 >1：按像素裁剪
    MASCOT_HEAD_CROP: list = field(default_factory=lambda: [0.10, 0.02, 0.78, 0.60])
    MASCOT_HEAD_SCALE: float = 0.40  # 脑袋宽度占屏幕宽度比例
    MASCOT_HEAD_X: float = 0.06      # 脑袋目标位置（左上角）x 比例
    MASCOT_HEAD_Y: float = 0.36      # 脑袋目标位置（左上角）y 比例
    MASCOT_BODY_CENTER_Y: float = 0.58  # 全身站立中心 y（屏幕高度比例）

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
                logger.warning(f"读取配置文件失败：{self._yaml_path}，错误：{e}")
                self._yaml_data = {}
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
                self.LLM_PROVIDER = "" # 自动检测

            image_val = data["models"].get("image", self.IMAGE_MODEL)
            if isinstance(image_val, dict):
                self.IMAGE_MODEL = image_val.get("model", "")
                self.IMAGE_PROVIDER = image_val.get("provider", "")
            else:
                self.IMAGE_MODEL = image_val
                self.IMAGE_PROVIDER = "" # 自动检测
            self.IMAGE_SIZE = data["models"].get("image_size", self.IMAGE_SIZE) # e.g. "1024x1792"
            self.IMAGE_STYLE = data["models"].get("image_style", self.IMAGE_STYLE)
            
            self.STYLES = data["models"].get("styles", {})
            self.CATEGORY_DEFAULTS = data["models"].get("category_defaults", {})
            self.CATEGORY_VOICES = data["models"].get("category_voices", {})
            self.CATEGORY_BGM = data["models"].get("category_bgm", {})
            self.CATEGORY_STYLES = data["models"].get("category_styles", {}) # 回退
            
            self.CATEGORY_ALIASES = data["models"].get("category_aliases", {}) # 加载别名
            self.CATEGORY_LAYOUTS = data["models"].get("category_layouts", {}) # 加载布局
            self.CATEGORY_HOOK_VOICE_TEXT = data["models"].get("category_hook_voice", {})
            self.ANIMATOR_TYPE = data["models"].get("animator", self.ANIMATOR_TYPE)
            self.TTS_VOICE = data["models"].get("tts_voice", self.TTS_VOICE)
            self.TTS_VOICE_TITLE = data["models"].get("tts_voice_title", self.TTS_VOICE) # 如果未设置，则默认为主语音
            self.SENSITIVE_WORDS = data.get("sensitive_words", {})

        # 密钥（可选，但推荐使用环境变量）
        if "keys" in data:
            if data["keys"].get("openai_api_key"): self.OPENAI_API_KEY = data["keys"]["openai_api_key"]
            if data["keys"].get("gemini_api_key"): self.GEMINI_API_KEY = data["keys"]["gemini_api_key"]
            if data["keys"].get("ark_api_key"): self.ARK_API_KEY = data["keys"]["ark_api_key"]
            if data["keys"].get("luma_api_key"): self.LUMA_API_KEY = data["keys"]["luma_api_key"]
            if data["keys"].get("volc_access_key"): self.VOLC_ACCESS_KEY = data["keys"]["volc_access_key"]
            if data["keys"].get("volc_secret_key"): self.VOLC_SECRET_KEY = data["keys"]["volc_secret_key"]
            if data["keys"].get("stability_api_key"): self.STABILITY_API_KEY = data["keys"]["stability_api_key"]
            if data["keys"].get("sensitive_words"): self.SENSITIVE_WORDS = data["keys"]["sensitive_words"]
            
        # 项目
        if "project" in data:
            out_dir = data["project"].get("output_dir")
            if out_dir:
                self.OUTPUT_DIR = os.path.abspath(out_dir)

        # 功能
        if "features" in data:
            self.ENABLE_ANIMATION = data["features"].get("enable_animation", self.ENABLE_ANIMATION)
            self.ENABLE_SUBTITLES = data["features"].get("enable_subtitles", self.ENABLE_SUBTITLES)
            self.ENABLE_BRAND_OUTRO = data["features"].get("enable_brand_outro", self.ENABLE_BRAND_OUTRO)
            self.ENABLE_EMOTIONAL_TTS = data["features"].get("enable_emotional_tts", self.ENABLE_EMOTIONAL_TTS)
            self.ENABLE_HOOK_VOICE = data["features"].get("enable_hook_voice", self.ENABLE_HOOK_VOICE)
            self.HOOK_VOICE_TEXT = data["features"].get("hook_voice_text", self.HOOK_VOICE_TEXT)
            self.HOOK_INTRO_PAUSE = float(data["features"].get("hook_intro_pause", self.HOOK_INTRO_PAUSE))
            self.HOOK_INTRO_FLIP = float(data["features"].get("hook_intro_flip", self.HOOK_INTRO_FLIP))
            self.HOOK_INTRO_BG_MODE = str(data["features"].get("hook_intro_bg_mode", self.HOOK_INTRO_BG_MODE) or "brand")
            self.HOOK_INTRO_SFX_PATH = str(data["features"].get("hook_intro_sfx_path", self.HOOK_INTRO_SFX_PATH) or "")
            self.HOOK_INTRO_SFX_VOLUME = float(data["features"].get("hook_intro_sfx_volume", self.HOOK_INTRO_SFX_VOLUME))
            self.HOOK_INTRO_SFX_START = float(data["features"].get("hook_intro_sfx_start", self.HOOK_INTRO_SFX_START))
            self.HOOK_INTRO_SFX_TRIM_START = float(data["features"].get("hook_intro_sfx_trim_start", self.HOOK_INTRO_SFX_TRIM_START))
            self.HOOK_INTRO_SFX_TRIM_END = float(data["features"].get("hook_intro_sfx_trim_end", self.HOOK_INTRO_SFX_TRIM_END))
            self.HOOK_INTRO_SFX_FADE_IN = float(data["features"].get("hook_intro_sfx_fade_in", self.HOOK_INTRO_SFX_FADE_IN))
            self.HOOK_INTRO_SFX_FADE_OUT = float(data["features"].get("hook_intro_sfx_fade_out", self.HOOK_INTRO_SFX_FADE_OUT))
            
            # 吉祥物片头动画（可选）
            self.ENABLE_MASCOT_INTRO = bool(data["features"].get("enable_mascot_intro", self.ENABLE_MASCOT_INTRO))
            self.MASCOT_INTRO_PATH = data["features"].get("mascot_intro_path", self.MASCOT_INTRO_PATH)
            self.MASCOT_INTRO_BLINK_PATH = data["features"].get("mascot_intro_blink_path", self.MASCOT_INTRO_BLINK_PATH)
            self.MASCOT_INTRO_SCALE = float(data["features"].get("mascot_intro_scale", self.MASCOT_INTRO_SCALE))
            self.MASCOT_INTRO_X = float(data["features"].get("mascot_intro_x", self.MASCOT_INTRO_X))
            self.MASCOT_INTRO_Y = float(data["features"].get("mascot_intro_y", self.MASCOT_INTRO_Y))
            self.MASCOT_INTRO_ENTRY = float(data["features"].get("mascot_intro_entry", self.MASCOT_INTRO_ENTRY))
            self.MASCOT_INTRO_FLOAT = float(data["features"].get("mascot_intro_float", self.MASCOT_INTRO_FLOAT))
            self.MASCOT_INTRO_BLINK_INTERVAL = float(data["features"].get("mascot_intro_blink_interval", self.MASCOT_INTRO_BLINK_INTERVAL))
            self.MASCOT_INTRO_BLINK_DUR = float(data["features"].get("mascot_intro_blink_dur", self.MASCOT_INTRO_BLINK_DUR))
            self.MASCOT_INTRO_SHOW_NAME = bool(data["features"].get("mascot_intro_show_name", self.MASCOT_INTRO_SHOW_NAME))
            
            # 绘宝分段出场（可选）
            self.MASCOT_STAGE1_DUR = float(data["features"].get("mascot_stage1_dur", self.MASCOT_STAGE1_DUR))
            self.MASCOT_STAGE1_BLINKS = int(data["features"].get("mascot_stage1_blinks", self.MASCOT_STAGE1_BLINKS))
            self.MASCOT_STAGE1_BLINK_DUR = float(data["features"].get("mascot_stage1_blink_dur", self.MASCOT_STAGE1_BLINK_DUR))
            self.MASCOT_STAGE2_PAUSE = float(data["features"].get("mascot_stage2_pause", self.MASCOT_STAGE2_PAUSE))
            self.MASCOT_STAGE2_DUR = float(data["features"].get("mascot_stage2_dur", self.MASCOT_STAGE2_DUR))
            self.MASCOT_STAGE2_JUMP = float(data["features"].get("mascot_stage2_jump", self.MASCOT_STAGE2_JUMP))
            self.MASCOT_STAGE3_PAUSE = float(data["features"].get("mascot_stage3_pause", self.MASCOT_STAGE3_PAUSE))
            self.MASCOT_GESTURE_ROT_DEG = float(data["features"].get("mascot_gesture_rot_deg", self.MASCOT_GESTURE_ROT_DEG))
            self.MASCOT_GESTURE_FREQ = float(data["features"].get("mascot_gesture_freq", self.MASCOT_GESTURE_FREQ))
            self.MASCOT_GESTURE_SHIFT = float(data["features"].get("mascot_gesture_shift", self.MASCOT_GESTURE_SHIFT))
            self.MASCOT_GESTURE_BOB = float(data["features"].get("mascot_gesture_bob", self.MASCOT_GESTURE_BOB))
            # 切脑袋/站位（允许 YAML 覆盖）
            hc = data["features"].get("mascot_head_crop", self.MASCOT_HEAD_CROP)
            if isinstance(hc, (list, tuple)) and len(hc) == 4:
                self.MASCOT_HEAD_CROP = list(hc)
            self.MASCOT_HEAD_SCALE = float(data["features"].get("mascot_head_scale", self.MASCOT_HEAD_SCALE))
            self.MASCOT_HEAD_X = float(data["features"].get("mascot_head_x", self.MASCOT_HEAD_X))
            self.MASCOT_HEAD_Y = float(data["features"].get("mascot_head_y", self.MASCOT_HEAD_Y))
            self.MASCOT_BODY_CENTER_Y = float(data["features"].get("mascot_body_center_y", self.MASCOT_BODY_CENTER_Y))
    
    def get_speech_rate(self, category: str) -> str:
        """获取指定类目的语速配置，默认-15%"""
        if not hasattr(self, '_category_speech_rates'):
            self._ensure_yaml_loaded()
            models = (self._yaml_data or {}).get("models", {}) if self._yaml_data else {}
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
        if not hasattr(self, '_scene_count_config'):
            # 加载场景数量配置
            self._scene_count_config = {
                'default_min': 14,
                'default_max': 24,
                'category_overrides': {}
            }
            self._ensure_yaml_loaded()
            models = (self._yaml_data or {}).get("models", {}) if self._yaml_data else {}
            scene_count = models.get("scene_count", {}) or {}
            self._scene_count_config['default_min'] = scene_count.get('min', 18)
            self._scene_count_config['default_max'] = scene_count.get('max', 24)

            category_scene_count = models.get("category_scene_count", {}) or {}
            for cat, range_config in category_scene_count.items():
                self._scene_count_config['category_overrides'][cat] = (
                    range_config.get('min', 18),
                    range_config.get('max', 24)
                )
        
        # 如果有特定类目的配置，优先使用
        if category and category in self._scene_count_config['category_overrides']:
            return self._scene_count_config['category_overrides'][category]
        
        # 否则使用全局默认值
        return (
            self._scene_count_config['default_min'],
            self._scene_count_config['default_max']
        )

config = Config()
# 尝试从默认位置加载
config.load_from_yaml("config.yaml")

# 确保输出目录存在
if config.OUTPUT_DIR:
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

