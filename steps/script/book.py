from .base import ScriptGeneratorBase


class BookScriptGenerator(ScriptGeneratorBase):
    def _build_script_prompt(
        self,
        topic: str,
        prompt_topic: str,
        subtitle: str,
        min_scenes: int,
        max_scenes: int,
        category: str,
        topic_display: str,
    ) -> str:
        prompt_script_user = f"""请为书籍/主题【{topic_display}】编写一个“讲故事风格”的视频脚本。
        
        上下文：
        书籍名称: {prompt_topic} (请注意识别书名中可能包含的 specific version/edition 信息，如"少儿版"、"原著版"等)
        当前章节: {subtitle if subtitle else "全书"} (请注意识别章节序号和章节标题，如"第一章 白色的拉布拉多")
        
        ⚠️ **剧情范围严格限制（Chapter Isolation）**：
        1. **忠实原著**：严格基于《{prompt_topic}》原书剧情。**绝对不要**杜撰原书中不存在的虚构情节！
        2. **章节隔离**：只讲述**当前章节（{subtitle}）**内发生的事件。
           - 不此前情提要（除非是第一章）。
           - 不剧透后续章节。
        3. **严禁重复**：如果这是第二章，严禁再讲上一章的过程。
        4. 直接从这一章的剧情开始，讲这一章发生的新故事或新观点。
        5. 不要试图在这一章里讲完整本书！
        """

        # 动态添加第一章/后续章节的约束
        is_chapter_1 = (
            "第一章" in subtitle
            or "Chapter 1" in subtitle
            or subtitle == "1"
            or not subtitle
        )
        if is_chapter_1:
            prompt_script_user += """
        5. **第一章特别要求**：这是故事的开头！请务必包含主角如何登场、核心冲突如何开始。这是本章的核心！
             """
        else:
            prompt_script_user += """
        5. **情境假设**：假设观众已经看完了第一章。他们认识主角，知道背景。不需要再次介绍这些背景！
        6. **开头检查**：如果你的第一场戏是“主角登场”或类似第一章的内容，请立即删除并重写！仅当这一章确实是第一章时才允许包含这些内容。
             """

        prompt_script_user += f"""
        
        要求：
        1. **提炼核心点**：将本章内容提炼为 {min_scenes}-{max_scenes} 个关键情节或核心观点（Story Beats）。
        2. **画面感**：每个核心点对应一个场景，旁白要讲述这个点发生的故事或表达的观点，画面要配合展示。
        3. **连贯性**：场景之间要有逻辑衔接，像讲一个完整的故事一样。
        
        请直接按 JSON 格式输出场景列表。
        """

        return prompt_script_user
