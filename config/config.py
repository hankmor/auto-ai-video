import os
import yaml
from dataclasses import dataclass, field

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
    ENABLE_BRAND_INTRO: bool = False   # 品牌片头
    ENABLE_BRAND_OUTRO: bool = True    # 品牌片尾
    ENABLE_EMOTIONAL_TTS: bool = False # 情感语音

    # 字体设置
    FONTS: dict = field(default_factory=dict)

    def load_from_yaml(self, path: str = "config.yaml"):
        if not os.path.exists(path):
            return
        
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            
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
            self.ENABLE_BRAND_INTRO = data["features"].get("enable_brand_intro", self.ENABLE_BRAND_INTRO)
            self.ENABLE_BRAND_OUTRO = data["features"].get("enable_brand_outro", self.ENABLE_BRAND_OUTRO)
            self.ENABLE_EMOTIONAL_TTS = data["features"].get("enable_emotional_tts", self.ENABLE_EMOTIONAL_TTS)
    
    def get_speech_rate(self, category: str) -> str:
        """获取指定类目的语速配置，默认-15%"""
        if not hasattr(self, '_category_speech_rates'):
            # 加载语速配置
            self._category_speech_rates = {}
            if os.path.exists("config.yaml"):
                try:
                    with open("config.yaml", 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                        # 从 models 节点读取 category_speech_rates
                        if data and "models" in data:
                            self._category_speech_rates = data["models"].get("category_speech_rates", {})
                            # 调试日志
                            from auto_maker.utils import logger
                            logger.debug(f"Loaded speech rates: {self._category_speech_rates}")
                except Exception as e:
                    from auto_maker.utils import logger
                    logger.warning(f"Failed to load speech rates: {e}")
        
        rate = self._category_speech_rates.get(category, "-15%")
        from auto_maker.utils import logger
        logger.info(f"🎵 Speech rate for '{category}': {rate}")
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
            if os.path.exists("config.yaml"):
                try:
                    with open("config.yaml", 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                        if data and "models" in data:
                            scene_count = data["models"].get("scene_count", {})
                            self._scene_count_config['default_min'] = scene_count.get('min', 18)
                            self._scene_count_config['default_max'] = scene_count.get('max', 24)
                            
                            # 加载分类特定配置
                            category_scene_count = data["models"].get("category_scene_count", {})
                            for cat, range_config in category_scene_count.items():
                                self._scene_count_config['category_overrides'][cat] = (
                                    range_config.get('min', 18),
                                    range_config.get('max', 24)
                                )
                except Exception as e:
                    from auto_maker.utils import logger
                    logger.warning(f"Failed to load scene count config: {e}")
        
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
