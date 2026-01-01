from .prompt_strategy import (
    PromptStrategy, 
    DefaultStrategy, 
    HistoryStrategy, 
    MeditationStrategy, 
    EnglishStorybookStrategy,
    IdiomStoryStrategy
)

class StrategyFactory:
    """
    基于类别创建适当 PromptStrategy 的工厂类。
    """
    
    @staticmethod
    def get_strategy(category: str) -> PromptStrategy:
        if category == "历史解说":
            return HistoryStrategy()
        elif category == "助眠冥想":
            return MeditationStrategy()
        elif category == "英语绘本":
            return EnglishStorybookStrategy()
        elif category == "成语故事" or "成语" in category:
            return IdiomStoryStrategy()
        
        return DefaultStrategy()

