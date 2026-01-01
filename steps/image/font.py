import os
from PIL import ImageFont
from config.config import config

from util.logger import logger

class FontManager:
    """
    管理字体加载，包含配置和缓存。
    通过模块级实例使用单例模式。
    """
    
    def __init__(self):
        self._cache = {} # 键: (path, size) -> 字体对象
        
        # 配置失败时的硬编码回退
        self.default_fallbacks = {
            "chinese": [
                "/System/Library/Fonts/PingFang.ttc",
                "/System/Library/Fonts/STHeiti Medium.ttc",
                "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
            ],
            "english": [
                "/System/Library/Fonts/Helvetica.ttc",
                "/System/Library/Fonts/Arial.ttf"
            ]
        }

    def get_font(self, font_type: str, size: int) -> ImageFont.FreeTypeFont:
        """
        获取已加载的 ImageFont 对象。
        
        Args:
            font_type (str): 'chinese' 或 'english' (config.yaml 中的键)
            size (int): 字体大小
            
        Returns:
            ImageFont: 加载的字体，或者如果全部失败则返回默认 PIL 字体。
        """
        # 1. 从配置中获取候选路径
        candidates = config.FONTS.get(font_type, [])
        
        # 2. 如果列表为空或未配置特定类型，则追加硬编码默认值
        if not candidates:
            candidates = self.default_fallbacks.get(font_type, [])
        
        # 确保它是列表
        if isinstance(candidates, str):
            candidates = [candidates]
            
        # 3. 尝试加载
        for path in candidates:
            # 展开 ~
            path = os.path.expanduser(path)
            
            if not os.path.exists(path):
                continue
                
            cache_key = (path, size)
            if cache_key in self._cache:
                return self._cache[cache_key]
                
            try:
                font = ImageFont.truetype(path, size)
                self._cache[cache_key] = font
                # logger.debug(f"Loaded font: {path} ({size}px)")
                return font
            except Exception as e:
                logger.warning(f"Failed to load font {path}: {e}")
                continue
        
        # 4. 回退到默认值
        if font_type != "default":
            # 如果没办法了，是否尝试用英文回退代替中文，反之亦然？不，直接用默认。
            logger.warning(f"No suitable font found for '{font_type}'. Using system default.")
        
        return ImageFont.load_default()

# 全局实例
font_manager = FontManager()
