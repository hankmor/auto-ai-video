# AI Video Maker（自动视频生成流水线）

一个“给我一个主题，就能自动生成成片”的 AI 视频制作工具：自动写分镜脚本、生成配图、配音、（可选）图生视频动画、字幕/拼音、封面、背景音乐，并最终合成 MP4。

## 核心能力

- **一键全流程**：`script → image → (animate) → audio → video`
- **分类驱动的内容策略**：按类目自动选择画风、配音池、BGM、视频排版（book/movie）
- **多模型支持**：
  - 文案/脚本：火山引擎（豆包/Ark）、OpenAI、Google Gemini
  - 图像：火山引擎（豆包/即梦）、OpenAI（DALL·E）、Mock
  - 动画（可选）：Luma、Stability、Mock
- **字幕与拼音**：开启后自动为中文字幕渲染拼音字幕
- **自动封面**：生成 `cover.png`（中文标题带拼音；英文标题自动换行/排版），并可生成标题配音 `title_audio.mp3`
- **背景音乐**：按类目自动混入 `assets/music/` 中的 BGM（自动降低音量，避免盖过人声）

## 技术栈

- **Python**：要求 `>= 3.13`（见 `pyproject.toml`）
- **多媒体合成**：`moviepy`
- **TTS**：`edge-tts`
- **拼音**：`pypinyin`
- **配置**：`config.yaml`（`PyYAML`）

## 快速开始

### 1）安装依赖

推荐使用 `uv`（仓库包含 `uv.lock`）：

```bash
uv sync
```

或使用 `pip`（示例）：

```bash
pip install -r requirements.txt
```

> 说明：本项目依赖列表以 `pyproject.toml` 为准；如果你使用 `pip`，请自行按环境准备依赖。

### 2）配置模型与密钥

项目会读取环境变量，也支持在 `config.yaml` 的 `keys:` 中填写（推荐用环境变量更安全）。

常见环境变量示例：

```bash
# 火山引擎（LLM + 图像）
export ARK_API_KEY="sk-..."          # 可选（如你用 Ark Key）
export VOLC_ACCESS_KEY="AK..."
export VOLC_SECRET_KEY="SK..."

# OpenAI / Gemini（可选替换）
export OPENAI_API_KEY="sk-..."
export GEMINI_API_KEY="AIza..."

# 动画（可选）
export LUMA_API_KEY="kp-..."
export STABILITY_API_KEY="sk-..."
```

模型选择与内容策略主要在 `config.yaml`：

- `models.llm / models.image / models.animator`
- `models.styles`（风格提示词）
- `models.category_defaults`（类目→默认风格键）
- `models.category_aliases`（类目别名，如 `cy/en/db`）
- `models.category_layouts`（类目→布局：`book`/`movie`）
- `models.category_voices`（类目→随机语音池）
- `models.category_bgm`（类目→BGM 文件名）

### 3）一键生成视频

```bash
python main.py --topic "刻舟求剑" --category cy
```

常用组合示例：

```bash
# 开启拼音字幕
python main.py --topic "守株待兔" --category cy --subtitles

# 强制指定风格（支持风格键，如 pixar / ink_wash / flat_tech，也可直接传自定义提示词）
python main.py --topic "三国演义" --category ls --style pixar

# 强制指定配音（覆盖随机语音池）
python main.py --topic "The Lion and the Mouse" --category en --voice en-US-AnaNeural
```

## 常用参数（CLI）

- **`--topic`**：主题（支持 `标题:副标题`；也支持 `封面标题|上下文标题` 的高级写法）
- **`--category`**：类目/系列（支持别名，见 `config.yaml` 的 `models.category_aliases`）
- **`--style`**：覆盖画风（风格键或自定义提示词）
- **`--voice`**：覆盖 TTS 语音（否则按类目语音池随机）
- **`--subtitles` / `-sb`**：开启字幕（中文自动拼音）
- **`--step`**：分步执行：`script | image | animate | audio | video | all`
- **`--force`**：强制重新生成（即使已存在中间产物）

## 分步运行（调试/可控生产）

```bash
python main.py --topic "小狗钱钱:第一章" --category db --step script
python main.py --topic "小狗钱钱:第一章" --category db --step image
python main.py --topic "小狗钱钱:第一章" --category db --step audio
python main.py --topic "小狗钱钱:第一章" --category db --step video
```

> 脚本会落到当前作品目录下的 `script.json`，你可以手动修改后再继续生成后续步骤。

## 输出结构

主流程输出默认在：

```
products/<类目>/<主题>/
  script.json
  script.md
  cover.png
  title_audio.mp3
  scene_*.png / scene_*.mp3 / scene_*.mp4（视配置而定）
  final_video.mp4
  metadata.json / metadata.md（发布信息，若生成成功）
```

## 背景音乐素材

将音乐文件放在 `assets/music/`，并在 `config.yaml` 的 `models.category_bgm` 中配置映射。仓库已自带示例音乐：

- `assets/music/guqin.mp3`、`epic.mp3`、`lullaby.mp3`、`meditation.mp3`、`playful.mp3`、`storybook.mp3` 等

## 测试（可选）

项目包含集成测试脚本（用于验证排版/BGM/合成逻辑）：

```bash
python tests/test_gen.py "测试主题" --category "成语故事"
```

## 许可证

见 `LICENSE`。
