# AI Video Maker 文档

欢迎使用本项目的自动视频生成流水线。你只需要提供一个主题（可带副标题），系统即可自动完成：分镜脚本 → 配图 →（可选）图生视频 → 配音 → 字幕/拼音 → 封面 → 背景音乐 → 合成 MP4。

## 🌟 核心功能 (Core Features)

1.  **全自动流程**: 只要一个主题，自动搞定剧本、画图、配音、字幕、剪辑、合成。
2.  **智能分镜**: 利用 LLM (GPT-4/豆包) 自动设计分镜脚本，保证画面连贯。
3.  **多风格支持**:
    - **预设画风**: 水墨风、皮克斯、泡泡玛特、日漫、**迪士尼绘本** (New)、赛博朋克等。
    - **自动匹配**: 按 `config.yaml` 的 `models.category_defaults` 自动选择风格（也可用 `--style` 覆盖）。
4.  **智能配音 (TTS)**:
    - **随机选角**: 自动从预设的“声音池”中随机挑选合适的解说员（支持男/女/童声/方言混合）。
    - **多语言**: 支持纯正美式英语发音（用于英语绘本）。
    - **手动指定**: 支持 `--voice` 强行指定喜欢的配音演员。
5.  **精美字幕 & 封面**:
    - **拼音字幕**: 自动为中文字幕标注拼音（适合儿童教育）。
    - **自动封面**: 自动生成带**大标题+拼音**的精美封面图，并插入视频首帧。
6.  **背景音乐 (BGM)**:
    - 根据分类自动匹配背景音乐（如古琴、史诗、助眠、绘本）。
    - 自动混音并降低 BGM 音量，避免盖过人声。
7.  **低成本引擎**: 支持火山引擎（豆包/即梦）进行文案与图像生成，也可切换 OpenAI / Gemini。

## 🚀 快速开始 (Quick Start)

### 1. 配置 API Key

本项目支持多种模型，推荐使用 **豆包 (Doubao)** 以获得最佳性价比。

在项目根目录创建 `.env` 文件或直接设置环境变量：

```bash
# === 必填项 (LLM & 图像) ===
# 方案 A: 使用豆包 (推荐, 便宜且快)
export ARK_API_KEY="sk-..."          # 用于写文案
export VOLC_ACCESS_KEY="AK..."       # 用于画图 (Volcengine IAM)
export VOLC_SECRET_KEY="SK..."       # 用于画图 (Volcengine IAM)

# 方案 B: 使用 OpenAI
export OPENAI_API_KEY="sk-..."       # 用于文案 & DALL-E 3

# === 选填项 (视频生成) ===
export LUMA_API_KEY="kp-..."         # 若使用 Luma Dream Machine
export STABILITY_API_KEY="sk-..."    # 若使用 Stability SVD
```

同时修改 `config.yaml` 启用对应模型：

```yaml
models:
  llm:
    provider: "volcengine" # 或 openai / google
    model: "ep-xxxx" # 替换为你的 Endpoint ID
  image:
    provider: "volcengine" # 或 openai / google
    model: "doubao-3.0" # 或 jimeng-4.0 / dall-e-3 / mock
```

### 2. 准备背景音乐 (可选)

为了启用 BGM 功能，请将您的 MP3 文件放入 `assets/music/` 目录：

- `guqin.mp3` (用于成语故事)
- `storybook.mp3` (用于英语绘本)
- `ukulele.mp3` (用于可爱风格)
- _(更多文件名映射可在 `config.yaml` 中查看或修改)_

### 3. 一键生成视频

**场景 A: 制作通过成语故事 (自动水墨风 + 古风 BGM + 拼音)**

```bash
python main.py --topic "刻舟求剑" --category cy --subtitles
```

**场景 B: 制作英语绘本 (自动迪士尼风 + 英文女童声)**

```bash
python main.py --topic "The Lion and the Mouse" --category en
```

**场景 C: 强制指定 (我要用皮克斯风格讲历史)**

```bash
python main.py --topic "三国演义" --category ls --style pixar --voice zh-CN-XiaoyiNeural
```

---

## 🛠️ 参数说明

- `--topic`: 视频主题 (必填)
- `--category`: 分类 (决定画风、配音池、BGM、布局)。支持缩写：见 `config.yaml` 的 `models.category_aliases`（例如 `cy/en/db` 等）。
- `--subtitles`: 开启字幕 (中文会自动加拼音)。
- `--style`: 强制指定画风 (覆盖分类默认)。
- `--voice`: 强制指定配音 (覆盖自动随机)。
- `--step`: 调试用，指定运行步骤 (script, image, animate, audio, video, all)。
- `--force`: 强制重新生成（即使产物已存在）。

---

### 4. 分步调试 (Step-by-Step)

支持通过 `--step` 参数分步执行，方便调试或进行精细化控制。中间状态会保存到当前作品目录下的 `script.json`（默认输出在 `products/<类目>/<主题>/`）。

```bash
# 1. 生成剧本
python main.py --step script --topic "故事主题" --category cy

# 2. 生成分镜图片 (可先手动修改 script.json)
python main.py --step image --topic "故事主题" --category cy

# 3. 生成动画 (可选，需配置 Luma/Stability Key；也可在 config.yaml 里关闭 enable_animation)
python main.py --step animate --topic "故事主题" --category cy

# 4. 生成配音
python main.py --step audio --topic "故事主题" --category cy

# 5. 合成视频
python main.py --step video --topic "故事主题" --category cy
```

您也可以创建 `config.yaml` 文件来管理所有配置 (见配置指南)。

- [架构设计 (Architecture)](architecture.md): 了解系统的内部模块与工作流。
- [配置指南 (Configuration)](configuration.md): 详细的环境变量与参数配置说明。
- [API 参考 (API Reference)](api_reference.md): 核心类与函数的开发者文档。
