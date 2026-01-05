from abc import ABC, abstractmethod
from config.config import C

class PromptStrategy(ABC):
    """
    特定分类提示词生成策略的抽象基类。
    封装系统指令和语言要求的变化。
    """
    
    @abstractmethod
    def get_category_instruction(self) -> str:
        """
        返回要注入到系统提示词中的特定分类指令块。
        这通常对应于规则 #4 或特定的讲故事约束。
        """
        pass

    def get_language_instruction(self) -> str:
        """
        返回旁白的特定语言指令。
        默认为简体中文。其他语言请重写此方法。
        """
        return "1. 使用 **简体中文**。"

class DefaultStrategy(PromptStrategy):
    def get_category_instruction(self) -> str:
        return ""

class HistoryStrategy(PromptStrategy):
    def get_category_instruction(self) -> str:
        return """
        4. **【历史解说特化指令】**:
           - 必须在开篇明确交代：**朝代、具体年份（如公元XXX年）、关键地点**。
           - 叙事必须严谨，包含：任务目标（Want）、行动过程（Action）、阻碍（Obstacle）、最终结果（Result）。
           - 旁白风格要求：**严肃、厚重、像纪录片一样**。
        """

class MeditationStrategy(PromptStrategy):
    def get_category_instruction(self) -> str:
        return """
        4. **【助眠冥想特化指令】**:
           - 旁白必须极其缓慢、温柔，使用引导性语言（“请闭上双眼...”、“感受呼吸...”）。
           - 避免任何冲突或紧张的情节。专注描述自然环境、光影、宁静的感觉。
        """

class EnglishStorybookStrategy(PromptStrategy):
    def get_language_instruction(self) -> str:
        base_inst = "1. **必须严格使用纯正的英文 (English)** 撰写旁白。适合儿童阅读，词汇简单地道。"
        if C.ENABLE_BILINGUAL_MODE:
            return (
                base_inst
                + "\n        2. **双语模式启用**：你必须同时提供中文翻译。\n"
                + "           - 将英文旁白放入 JSON 的 `narration` 字段。\n"
                + "           - 将中文翻译放入 JSON 的 `narration_cn` 字段（不要放入 `narration`）。\n"
                + "           - **必须**在 JSON 根目录提供 `title_cn` 字段，填入标题的中文翻译。"
            )
        return base_inst

    def get_category_instruction(self) -> str:
        return """
        4. **【英语绘本特化指令】**:
           - 这是一个英语学习绘本。旁白将作为字幕和语音播放。
           - 确保语法完美，适合朗读。
        """

class IdiomStoryStrategy(PromptStrategy):
    def get_category_instruction(self) -> str:
        return """
        4. **【成语故事特化指令】**:
           - 这是一个成语故事，必须完整呈现故事和教育意义。
           - **最后一幕必须包含成语总结**：
             * 明确说出完整的成语（如"守株待兔"）
             * 解释成语的字面意思
             * 说明成语的寓意和道理
             * **必须列举 2-3 个近义词** (如: 刻舟求剑、墨守成规)
             * **必须列举 2-3 个反义词** (如: 随机应变、见机行事)
             * 可以用"这个成语告诉我们..."的句式
           - 示例最后一幕旁白：
             "这就是'守株待兔'的故事。意思是死守狭隘经验，不知变通。告诉我们要通过努力获得成功。它的近义词有刻舟求剑、墨守成规；反义词有随机应变、见机行事。"
        """

