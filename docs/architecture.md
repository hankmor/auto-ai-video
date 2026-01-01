# 系统架构设计

本项目采用模块化的流水线架构，数据在各个处理阶段之间单向流动。

## 架构图

```mermaid
graph TD
    User[用户输入] --> Main[Main Controller]
    Main --> ScriptGen[ScriptGenerator (LLM)]
    ScriptGen --> |生成 Script| ImageWork[ImageFactory]
    ScriptGen --> |生成 Script| AudioWork[AudioStudio]
    ImageWork --> |可选：I2V| Animator[Animator (Luma/Stability/Mock)]

    ImageWork --> |生成 Images| Assets[素材库]
    AudioWork --> |生成 Audio| Assets
    Animator --> |生成 Clips| Assets

    Assets --> VideoEd[VideoAssembler]
    VideoEd --> |合成| Output[最终视频 MP4]
```

## 核心模块

### 1. ScriptGenerator (编剧模块)

- **职责**: 负责内容的创意生成。
- **输入**: 用户的主题 (Topic)。
- **输出**: `VideoScript` 对象，包含多个 `Scene`。
- **关键技术**: 通过 `llm/llm_client.py` 统一调用多家 LLM（火山引擎 / OpenAI / Gemini），并用结构化 JSON 输出分镜。

### 2. ImageFactory (视觉模块)

- **职责**: 将文字描述转化为视觉图像。
- **输入**: `Scene.image_prompt`。
- **输出**: 本地图片路径。
- **关键技术**: 异步并发生成，支持火山引擎（豆包/即梦）、OpenAI（DALL·E）以及 `mock` 占位图模式。

### 3. AudioStudio (音频模块)

- **职责**: 将旁白文本转化为语音。
- **输入**: `Scene.narration`。
- **输出**: 本地 MP3 音频路径。
- **关键技术**: 使用 `edge-tts` 库，无需 API Key 即可获得高质量语音。

### 4. VideoAssembler (剪辑模块)

- **职责**: 将所有素材组装成视频。
- **输入**: 包含图片和音频路径的 `Scene` 列表。
- **输出**: `.mp4` 视频文件。
- **关键技术**: `MoviePy`。逻辑包括：
  - 读取音频获取精准时长。
  - 设置图片显示时长与音频同步。
  - 可选字幕（含中文拼音）、封面生成、背景音乐混音、转场（按类目配置）。

## 数据流转

系统使用 `model/models.py` 中的 dataclass 在各模块间传递数据：

```python
@dataclass
class Scene:
    scene_id: int
    narration: str
    image_prompt: str
    image_path: Optional[str]
    audio_path: Optional[str]
    video_path: Optional[str]  # 可选：图生视频片段
    emotion: Optional[str]     # 可选：情感标签（用于情感 TTS）
    sfx: Optional[str]         # 可选：音效关键词
    camera_action: Optional[str]  # 可选：镜头动作标签
```

这种设计保证了模块间的解耦，方便未来替换具体的实现（例如将 ImageFactory 从 DALL-E 换成 Midjourney）。
