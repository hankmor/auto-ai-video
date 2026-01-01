from .base import ScriptGeneratorBase

class GenericScriptGenerator(ScriptGeneratorBase):
    def _build_script_prompt(
        self, 
        topic: str, 
        prompt_topic: str, 
        subtitle: str, 
        min_scenes: int, 
        max_scenes: int, 
        category: str, 
        topic_display: str
    ) -> str:
        
        prompt = f"""请为主题【{topic_display}】编写一个详细的视频脚本。
        要求：
        1. 严格遵守上述 SYSTEM PROMPT 的所有规则（场景数量、JSON格式、时长限制）。
        2. 这是一个“{category}”类视频，请务必使用对应的语言风格和画面风格。
        
        请直接开始生成 JSON。
        
        上下文：
        主标题: {topic}
        副标题/章节: {subtitle if subtitle else "无"}
        
        ⚠️ 如果这是书籍的某一章节，请只专注于本章节的内容，不要重述整本书的故事。
        
        ⚠️ 核心要求：必须生成 **{min_scenes}-{max_scenes} 个场景**！不能少于 {min_scenes} 个！⚠️

        请参考系统提示中的扩展方法和示例，将故事充分展开。每个动作、每个情绪变化都应该是独立的场景。
        请务必使用英文详细描述画面（image_prompt），用指定语言写旁白（narration）。"""
        
        return prompt
