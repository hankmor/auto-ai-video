from config.config import C
from steps.video.base import VideoAssemblerBase
from steps.video.generic import GenericVideoAssembler
from steps.video.book import BookVideoAssembler

class VideoAssemblerFactory:
    @staticmethod
    def get_assembler(category: str) -> VideoAssemblerBase:
        layout_mode = "movie"
        if category in C.CATEGORY_LAYOUTS:
            layout_mode = C.CATEGORY_LAYOUTS[category]
        
        if layout_mode == "book":
            return BookVideoAssembler()
        return GenericVideoAssembler()
