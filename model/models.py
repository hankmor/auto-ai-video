import json
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Scene:
    scene_id: int
    narration: str  # The text to be spoken
    image_prompt: str  # The prompt for image generation
    duration_seconds: float = 0.0  # Estimated or actual duration
    image_path: Optional[str] = None
    audio_path: Optional[str] = None
    video_path: Optional[str] = None  # Path to generated video clip (I2V)
    emotion: Optional[str] = None # Emotion tag for TTS (cheerful, sad, etc.)
    sfx: Optional[str] = None # Sound effect keyword (e.g. "laugh", "rain")
    camera_action: Optional[str] = None # Camera movement tag (e.g. "zoom_in", "pan_left")

@dataclass
class VideoScript:
    topic: str
    scenes: List[Scene]
    visual_style: str = ""
    character_profiles: str = ""
    summary: str = ""  # 一句话剧情摘要
    intro_hook: str = ""  # AI生成的片头引导语

    def to_json(self, path: str):
        with open(path, 'w', encoding='utf-8') as f:
            # Simple recursive dict conversion
            data = {
                "topic": self.topic,
                "visual_style": self.visual_style,
                "character_profiles": self.character_profiles,
                "summary": self.summary,
                "intro_hook": self.intro_hook,
                "scenes": [
                    {
                        "scene_id": s.scene_id,
                        "narration": s.narration,
                        "image_prompt": s.image_prompt,
                        "duration_seconds": s.duration_seconds,
                        "image_path": s.image_path,
                        "audio_path": s.audio_path,
                        "video_path": s.video_path,
                        "emotion": s.emotion,
                        "sfx": s.sfx,
                        "camera_action": s.camera_action,
                    }
                    for s in self.scenes
                ],
            }
            json.dump(data, f, indent=4, ensure_ascii=False)

    def to_markdown(self, path: str):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(f"# {self.topic}\n\n")
            f.write(f"**Visual Style**: {self.visual_style}\n\n")
            f.write(f"**Character Profiles**: {self.character_profiles}\n\n")
            if self.intro_hook:
                f.write(f"**Intro Hook**: {self.intro_hook}\n\n")
            f.write("---\n\n")
            
            for scene in self.scenes:
                f.write(f"## Scene {scene.scene_id}\n")
                f.write(f"**Narration**: {scene.narration}\n\n")
                f.write(f"**Image Prompt**: {scene.image_prompt}\n\n")
                if scene.image_path:
                    f.write(f"![Scene {scene.scene_id}]({scene.image_path})\n\n")
                f.write("---\n\n")

    @classmethod
    def from_json(cls, path: str):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        scenes = []
        for s in data.get("scenes", []):
            scenes.append(Scene(
                scene_id=s["scene_id"],
                narration=s["narration"],
                image_prompt=s["image_prompt"],
                duration_seconds=s.get("duration_seconds", 0.0),
                image_path=s.get("image_path"),
                audio_path=s.get("audio_path"),
                video_path=s.get("video_path"),
                emotion=s.get("emotion"),
                sfx=s.get("sfx"),
                camera_action=s.get("camera_action")
            ))
            
        return cls(
            topic=data.get("topic", ""),
            scenes=scenes,
            visual_style=data.get("visual_style", ""),
            character_profiles=data.get("character_profiles", ""),
            summary=data.get("summary", ""),
            intro_hook=data.get("intro_hook", ""),
        )
