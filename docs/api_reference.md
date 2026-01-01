# API 参考文档（与当前仓库结构一致）

本文档面向二次开发/读代码的同学，列出核心模块与主要类/方法，便于快速定位实现。

## 模块结构

- `main.py`：CLI 入口与流程编排（`--step` 分步执行）
- `config/config.py`：配置加载与运行时开关（`config` 单例）
- `model/models.py`：核心数据结构（`Scene` / `VideoScript`）
- `llm/*`：多提供商封装（火山引擎 / OpenAI / Gemini）
- `prompt/*`：类目提示词策略（含 `IdiomStoryStrategy`）
- `steps/script/*`：脚本生成（LLM）与生成器工厂
- `steps/image/*`：图像生成
- `steps/audio/*`：TTS 音频生成
- `steps/video/*`：视频合成（字幕/拼音/封面/BGM/转场/布局）
- `steps/animator/*`：图生视频（可选）

## 类参考

### `ScriptGeneratorBase` / `ScriptGeneratorFactory`

入口位置：

- `steps/script/base.py`：`ScriptGeneratorBase`
- `steps/script/factory.py`：`ScriptGeneratorFactory`

关键方法：

```python
class ScriptGeneratorBase:
    def generate_script(
        self,
        topic: str,
        subtitle: str = "",
        category: str = "",
        series_profile_path: Optional[str] = None,
        context_topic: str = None,
    ) -> VideoScript
```

- **generate_script**：生成 `VideoScript`（含 `summary`、`visual_style`、`character_profiles`、`scenes`）。

```python
class ScriptGeneratorFactory:
    def get_generator(category: str) -> ScriptGeneratorBase
```

- **get_generator**：按类目选择生成器实现（例如某些类目使用“book”式脚本生成器）。

### `ImageFactory`

入口位置：`steps/image/factory.py`

关键方法：

```python
class ImageFactory:
    async def generate_images(self, scenes: List[Scene], force: bool = False) -> List[str]
```

- **generate_images**：并发生成图片，并更新 `Scene.image_path`。

### `AudioStudioBase` / `GenericAudioStudio` / `AudioStudioFactory`

入口位置：

- `steps/audio/base.py`：`AudioStudioBase`
- `steps/audio/generic.py`：`GenericAudioStudio`
- `steps/audio/factory.py`：`AudioStudioFactory`

关键方法：

```python
class GenericAudioStudio(AudioStudioBase):
    async def generate_audio(self, scenes: List[Scene], force: bool = False)
```

- **generate_audio**：为每个 `Scene` 生成 `scene_<id>.mp3`，并更新 `Scene.audio_path`。

### `VideoAssemblerBase` / `VideoAssemblerFactory`

入口位置：

- `steps/video/base.py`：`VideoAssemblerBase`
- `steps/video/generic.py`：`GenericVideoAssembler`（movie 模式）
- `steps/video/book.py`：`BookVideoAssembler`（book 模式）
- `steps/video/factory.py`：`VideoAssemblerFactory`

关键方法：

```python
class VideoAssemblerBase:
    def assemble_video(
        self,
        scenes: List[Scene],
        output_filename: str = "final_video.mp4",
        topic: str = "",
        subtitle: str = "",
        category: str = "",
    ) -> str
```

- **assemble_video**：合成最终 MP4（可包含封面、字幕/拼音、BGM、转场与片尾片头等）。

## 数据结构

入口位置：`model/models.py`

```python
@dataclass
class Scene:
    scene_id: int
    narration: str
    image_prompt: str
    duration_seconds: float = 0.0
    image_path: Optional[str] = None
    audio_path: Optional[str] = None
    video_path: Optional[str] = None
    emotion: Optional[str] = None
    sfx: Optional[str] = None
    camera_action: Optional[str] = None

@dataclass
class VideoScript:
    topic: str
    scenes: List[Scene]
    visual_style: str = ""
    character_profiles: str = ""
    summary: str = ""
```


