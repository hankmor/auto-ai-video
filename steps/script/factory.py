from .base import ScriptGeneratorBase
from .generic import GenericScriptGenerator
from .book import BookScriptGenerator


class ScriptGeneratorFactory:
    @staticmethod
    def get_generator(category: str) -> ScriptGeneratorBase:
        if category == "读书分享":
            return BookScriptGenerator()
        return GenericScriptGenerator()
