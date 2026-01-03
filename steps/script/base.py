import json
import re
import os
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from pydantic import BaseModel, Field

from llm.llm_client import LLMClient
from model.models import VideoScript, Scene
from util.logger import logger
from config.config import C
import config.config
from prompt.factory import StrategyFactory


# --- Pydantic Schemas for Structured Output ---
class VideoDesign(BaseModel):
    visual_style: str = Field(
        ..., description="The defined visual style for the video."
    )
    character_profiles: Dict[str, str] = Field(
        ..., description="Key characters and their visual descriptions."
    )


class ScriptGeneratorBase(ABC):
    def __init__(self):
        self.llm = LLMClient()
        self.language = "en"
        self._detect_language()

    def _detect_language(self):
        # Based on LLM model name
        provider = C.LLM_PROVIDER.lower()
        if any(x in provider for x in [config.MODEL_PROVIDER_VOLCENGINE]):
            self.language = "cn"
            logger.info(
                f"🇨🇳 Detected Chinese LLM {C.LLM_MODEL}. Using Chinese System Prompts."
            )
        else:
            self.language = "en"
            logger.info(
                f"🌎 Using Standard English System Prompts for model: {C.LLM_MODEL}"
            )

    def _sanitize_text(self, text: str) -> str:
        """Replace sensitive words based on config."""
        if not text or not C.SENSITIVE_WORDS:
            return text
        sanitized = text
        for sensitive, safe in C.SENSITIVE_WORDS.items():
            if sensitive in sanitized:
                sanitized = sanitized.replace(sensitive, safe)
        return sanitized

    def _recover_json(self, text: str):
        """Recover valid JSON object from truncated text."""
        try:
            match = re.search(r'"scenes"\s*:\s*\[', text)
            if not match:
                return None
            array_start = match.end()
            content = text[array_start:]
            valid_scenes = []
            depth = 0
            start_idx = -1
            for i, char in enumerate(content):
                if char == "{":
                    if depth == 0:
                        start_idx = i
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0 and start_idx != -1:
                        obj_str = content[start_idx : i + 1]
                        try:
                            obj = json.loads(obj_str)
                            valid_scenes.append(obj)
                        except:
                            pass
                        start_idx = -1
            if valid_scenes:
                logger.info(
                    f"Recovered {len(valid_scenes)} scenes from truncated JSON."
                )
                return {"scenes": valid_scenes}
            return None
        except Exception as e:
            logger.error(f"JSON recovery failed: {e}")
            return None

    def _detect_new_characters(
        self, script_content: str, existing_profiles: Dict[str, str]
    ) -> Dict[str, str]:
        """Ask LLM to identify new characters from the generated script."""
        existing_names = (
            list(existing_profiles.keys())
            if isinstance(existing_profiles, dict)
            else []
        )
        prompt = f"""
        基于以下生成的视频脚本，请识别是否有**该脚本中出现，但不在已有列表中**的关键角色。
        已有角色列表: {existing_names}
        请特别注意：
        1. 检查是否有**主角**或**重要配角**被遗漏。
        2. 根据脚本内容，推断并生成他们的**视觉外貌描述**。
        请返回纯 JSON:
        {{
            "角色名": "视觉描述",
            "角色名2": "视觉描述"
        }}
        视频脚本内容:
        {script_content}
        """
        try:
            response = self.llm.generate_text(prompt)
            response = re.sub(r"```json\n|\n```", "", response).strip()
            if not response.startswith("{"):
                start = response.find("{")
                end = response.rfind("}")
                if start != -1 and end != -1:
                    response = response[start : end + 1]
            new_chars = json.loads(response)
            return new_chars if isinstance(new_chars, dict) else {}
        except Exception as e:
            logger.warning(f"Failed to detect new characters: {e}")
            return {}

    @abstractmethod
    def _build_script_prompt(
        self, topic: str, subtitle: str, min_scenes: int, max_scenes: int, category: str
    ) -> str:
        """
        Abstract method to build the user prompt for script generation.
        This is where Generic vs Book logic differs.
        """
        pass

    def generate_script(
        self,
        topic: str,
        subtitle: str = "",
        category: str = "",
        series_profile_path: Optional[str] = None,
        context_topic: str = None,
    ) -> VideoScript:
        logger.info(
            f"Generating script for topic: {topic}, subtitle: {subtitle} (Category: {category})"
        )
        if context_topic:
            logger.info(f"  Context Topic (for LLM): {context_topic}")

        prompt_topic = context_topic if context_topic else topic
        min_scenes, max_scenes = C.get_scene_count_range(category)
        logger.info(
            f"📊 Scene count target: {min_scenes}-{max_scenes} scenes for category '{category}'"
        )

        # --- Prompts reused from original ---
        SYSTEM_PROMPT_DESIGN = """
        你是一位专业的动画视频美术总监和角色设计师。
        根据用户的主题，你需要设计以下内容：
        1. "visual_style" (视觉风格): 为AI绘画定义一个连贯的艺术风格。
           *请使用中文描述*。
        {style_instruction}
        2. "character_profiles" (角色档案): 描述关键角色的外貌特征。
           - 格式：“角色名: 外貌描述...”
           - **⚠️ 重要规则 (一致性锁死)**: 角色档案一旦定义，后续必须一字不差复制。
           - **⚠️ 重要规则 (动物角色)**: 明确定义 "Anthropomorphic animal" 或 "Realistic animal"。禁止给写实动物添加人类特征。

        请仅返回一个 JSON 对象:
        {{
            "visual_style": "...",
            "character_profiles": "..."
        }}
        """

        SYSTEM_PROMPT_SCRIPT_CN = """
        你是一位专业的视频内容创作者。你的任务是编写一个结构化的视频脚本。
        上下文信息:
        主题: {prompt_topic}
        视觉风格: {visual_style}
        角色档案: {character_profiles}
        ⚠️ **【严格要求】场景数量必须达到 {min_scenes}-{max_scenes} 个，这是硬性指标！** ⚠️
        
        **剧情背景**: 
        你正在制作《{prompt_topic}》的视频脚本。请遵循经典情节。
        
        如何扩展到足够的场景数量：
        1. **环境铺垫**
        2. **角色登场**
        3. **情节推进** (拆分关键动作)
        4. **情绪细节**
        5. **转场过渡**
        6. **高潮细化**
        7. **结尾延展**

        ⚠️ **【关键指令 - 请严格遵守】** ⚠️:
        1. 场景总数必须在 **{min_scenes}-{max_scenes} 个** 之间。
        2. 每个场景只描述一个具体的动作或画面。
        3. 画面提示词必须用中文，且**强制复制**角色档案。
        4. **负面约束**: 动物角色添加“负面提示：人类身体...”。
        
        对于 "narration" (旁白):
        1. {language_instruction}
        2. 语调生动，字数控制在 30-50 字以内。
        {category_instruction}
        
        对于 "emotion" (情感): 选择 cheerful, sad, excited, fearful, affectionate, angry, serious 之一。
        
        对于 "camera_action": 选择 zoom_in, zoom_out, pan_left, pan_right, pan_up, pan_down, follow, shake, static 之一。
        
        对于 "image_prompt": **"主体 + 动作 + 环境"**。

        请仅返回一个纯 JSON 对象:
        {{
            "summary": "一句话概括...",
            "scenes": [
                {{
                    "narration": "...",
                    "image_prompt": "{visual_style}, ...",
                    "emotion": "...",
                    "camera_action": "..."
                }}
            ]
        }}
        """

        # --- Phase 1: Design ---
        style_inst_cn = ""
        if C.IMAGE_STYLE:
            style_inst_cn = f'2. 用户明确指定了风格: "{C.IMAGE_STYLE}"。请务必基于此风格进行扩展和细化。'
        else:
            style_inst_cn = "定义一个最适合该主题的视觉风格。"

        final_design_sys = SYSTEM_PROMPT_DESIGN.format(style_instruction=style_inst_cn)
        prompt_design_user = f"主题: {prompt_topic}\n请设计视觉风格和角色。"

        strategy = StrategyFactory.get_strategy(category)
        lang_inst = strategy.get_language_instruction()
        cat_inst = strategy.get_category_instruction()

        visual_style_prompt = ""
        character_profiles = {}

        existing_profile_data = {}
        if series_profile_path and os.path.exists(series_profile_path):
            try:
                with open(series_profile_path, "r", encoding="utf-8") as f:
                    existing_profile_data = json.load(f)
                logger.info(
                    f"📚 Loaded existing series profile from {series_profile_path}"
                )
                if "visual_style" in existing_profile_data:
                    visual_style_prompt = existing_profile_data["visual_style"]
                if "character_profiles" in existing_profile_data:
                    character_profiles = existing_profile_data["character_profiles"]
            except Exception as e:
                logger.error(f"Failed to load series profile: {e}")

        if not (visual_style_prompt and character_profiles):
            logger.info("Phase 1: Designing Visual Style & Characters...")
            design_response = self.llm.generate_text(
                prompt_design_user, final_design_sys
            )
            design_response = re.sub(r"```json\n|\n```", "", design_response).strip()
            try:
                design_data = json.loads(design_response)
                visual_style_prompt = self._sanitize_text(
                    design_data.get("visual_style", "")
                )
                character_profiles = design_data.get("character_profiles", {})
            except json.JSONDecodeError:
                logger.warning("Failed to parse design JSON. Using defaults.")
                visual_style_prompt = "Cinematic lighting, realistic style"
                character_profiles = {"General": "No specific character focus."}

            if isinstance(character_profiles, str):
                character_profiles = {"Main": character_profiles}

            if not visual_style_prompt:
                logger.error("Failed to generate design.")
                return None

            if series_profile_path and not existing_profile_data:
                try:
                    data_to_save = {
                        "visual_style": visual_style_prompt,
                        "character_profiles": character_profiles,
                    }
                    with open(series_profile_path, "w", encoding="utf-8") as f:
                        json.dump(data_to_save, f, ensure_ascii=False, indent=2)
                    logger.info(f"💾 Saved new series profile to {series_profile_path}")
                except Exception as e:
                    logger.error(f"Failed to save series profile: {e}")
        else:
            logger.info("Skipping Phase 1 (Design) - Using Series Profile.")

        logger.info(f"Visual Style: {visual_style_prompt[:50]}...")
        logger.info(f"Characters: {list(character_profiles.keys())}")

        character_profiles_str = "\n".join(
            [f"{name}: {desc}" for name, desc in character_profiles.items()]
        )
        if not character_profiles_str:
            character_profiles_str = "No specific character focus."

        # --- Phase 2: Script Writing ---
        tipp = (
            f"""
        请注意：
        1. 保持角色的视觉描述与已有的 "{character_profiles_str}" 一致。
        2. 如果有新角色出现，请在脚本中自然描述他们的外貌，但不要与旧角色冲突。
        """
            if character_profiles_str
            else ""
        )

        final_script_sys = (
            SYSTEM_PROMPT_SCRIPT_CN.format(
                prompt_topic=prompt_topic,
                topic=topic,
                visual_style=visual_style_prompt,
                character_profiles=character_profiles_str,
                min_scenes=min_scenes,
                max_scenes=max_scenes,
                language_instruction=lang_inst,
                category_instruction=cat_inst,
                subtitle_info=f"本章标题: {subtitle}" if subtitle else "",
            )
            + tipp
        )

        # Call the abstract method to get user prompt
        # We need to pass the resolved prompt_topic, topic_display etc.
        # But wait, original code constructs topic_display here.
        topic_display = f"{topic}: {subtitle}" if subtitle else topic

        # NOTE: Passing prompt_topic (which might be context_topic) AND original topic
        # The abstract method should handle constructing the prompt string.
        prompt_script_user = self._build_script_prompt(
            topic=topic,
            prompt_topic=prompt_topic,
            subtitle=subtitle,
            min_scenes=min_scenes,
            max_scenes=max_scenes,
            category=category,
            topic_display=topic_display,
        )

        logger.info("Phase 2: Generating Scenes...")
        response_text = self.llm.generate_text(prompt_script_user, final_script_sys)
        full_response = response_text
        response_text = re.sub(r"```json\n|\n```", "", response_text).strip()

        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            logger.warning("JSON parse failed. Attempting to recover truncated JSON...")
            data = self._recover_json(response_text)
            if not data:
                logger.error(
                    f"Failed to decode JSON from LLM: {response_text[:200]}..."
                )
                raise Exception("Script generation failed: Invalid JSON")

        scenes = []
        for i, item in enumerate(data.get("scenes", [])):
            if "narration" in item and "image_prompt" in item:
                scenes.append(
                    Scene(
                        scene_id=i + 1,
                        narration=item["narration"],
                        image_prompt=self._sanitize_text(item["image_prompt"]),
                        emotion=item.get("emotion", "serious"),
                        sfx=item.get("sfx"),
                        camera_action=item.get("camera_action"),
                    )
                )

        if not scenes:
            raise Exception("No valid scenes found in generated script.")

        # Check counts
        scene_count = len(scenes)
        if scene_count < min_scenes:
            logger.warning(
                f"⚠️  Scene count ({scene_count}) is below target ({min_scenes}-{max_scenes})."
            )
        elif scene_count > max_scenes:
            logger.warning(
                f"⚠️  Scene count ({scene_count}) exceeds target ({min_scenes}-{max_scenes})."
            )
        else:
            logger.info(f"✅ Scene count ({scene_count}) meets target range.")

        summary = data.get("summary", "")
        if not summary and scenes:
            summary = scenes[0].narration

        # --- Phase 3: Update Profile ---
        if series_profile_path:
            logger.info("Phase 3: Checking for new characters...")
            try:
                new_chars = self._detect_new_characters(
                    full_response, character_profiles
                )
                if new_chars:
                    logger.info(f"🆕 Detected new characters: {list(new_chars.keys())}")
                    if isinstance(character_profiles, dict):
                        character_profiles.update(new_chars)
                    data_to_save = {
                        "visual_style": visual_style_prompt,
                        "character_profiles": character_profiles,
                    }
                    with open(series_profile_path, "w", encoding="utf-8") as f:
                        json.dump(data_to_save, f, ensure_ascii=False, indent=2)
                    logger.info(f"💾 Updated series profile with new characters.")
                else:
                    logger.info("No new characters detected.")
            except Exception as e:
                logger.error(f"Failed to update series profile: {e}")

        summary = self._sanitize_text(summary)

        return VideoScript(
            topic=topic,
            scenes=scenes,
            visual_style=visual_style_prompt,
            character_profiles=character_profiles,
            summary=summary,
        )
