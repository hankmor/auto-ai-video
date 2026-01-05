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
        special_instruction = ""
        if category == "有声读物":
            special_instruction = f"""
            ⚠️ 【有声读物特别指令】 ⚠️
            用户提供的“主题”包含了详细的书籍/故事信息（来源、出版社、情节概要等）：
            >>> {topic}
            
            1. **必须理解并利用这些信息**：如果包含了来源（如“中国出版集团”），请在适当位置（如开头或结尾的旁白）提及，确立权威感。
            2. **忠实原作逻辑**：请根据上述提供的情节概要进行扩展，不要凭空捏造与提供信息冲突的剧情。
            3. **深度理解**：AI 必须表现出“懂”这个故事。如果信息中包含特定的教育意义、道理或背景，请务必在脚本中体现出来。
            """

        prompt = f"""请为主题【{topic_display}】编写一个详细的视频脚本。
        {special_instruction}
        
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
        
        【重要：AI 片头引导语生成】
        请根据主题【{topic_display}】即兴创作一句极具吸引力的“片头引导语”（intro_hook）：
        1. **目的**：放在视频最开头，勾起观众的好奇心，提高完播率。
        2. **长度**：短小精悍，1-2 句话，不要太长（语音时长控制在 3-5秒左右）。
        3. **内容**：可以是反问、悬念、震惊事实或情感共鸣。例如：“你真的见过龙吗？” 或 “这个故事的结局，可能会让你泪流满面...”
        4. **格式**：请将这句引导语放入 JSON 的 `intro_hook` 字段中。

        【重要：片尾互动提问】
        请确保 **最后一个场景** 的旁白（narration）必须包含一个与主题相关的、发人深省的互动问题：
        1. **目的**：引导观众（特别是小朋友）思考，并邀请他们在评论区回答。
        2. **内容**：结合故事核心寓意。例如：“小朋友们，你们是否也像叶公一样，并不是真正的喜欢一些东西呢？快来评论区告诉我吧。”
        3. **格式**：直接写在最后一个场景的 narration 中。

        【重要：镜头与运镜】
        为了让视频更生动，请为每一个场景指派一个合适的运镜方式（camera_action）：
        1. **选项**：
           - `zoom_in` (缓慢放大，强调主体)
           - `zoom_out` (缓慢缩小，展示全景)
           - `pan_left` (镜头左移/画面右移，展示右侧内容)
           - `pan_right` (镜头右移/画面左移，展示左侧内容)
           - `pan_up` (镜头上移)
           - `pan_down` (镜头下移)
           - `static` (静止/微动)
        2. **要求**：请根据画面内容和情绪灵活选择，不要全部一样。
        3. **格式**：放入 JSON 下的 `camera_action` 字段。

        请务必使用英文详细描述画面（image_prompt），用指定语言写旁白（narration）。"""
        
        return prompt
