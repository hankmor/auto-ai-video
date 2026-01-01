from config.config import config
from steps.video.base import VideoAssemblerBase
from steps.video.generic import GenericVideoAssembler
from steps.video.book import BookVideoAssembler

class VideoAssemblerFactory:
    @staticmethod
    def get_assembler(category: str) -> VideoAssemblerBase:
        layout_mode = "movie"
        if category in config.CATEGORY_LAYOUTS:
            layout_mode = config.CATEGORY_LAYOUTS[category]
        
        if layout_mode == "book":
            return BookVideoAssembler()
        return GenericVideoAssembler()
