# AI Video Maker（自动视频生成流水线）

一个"给我一个主题，就能自动生成成片"的 AI 视频制作工具：自动写分镜脚本、生成配图、配音、（可选）图生视频动画、字幕/拼音、封面、背景音乐，并最终合成 MP4。

## ✨ 新功能

### 🎬 增强Camera Action（方案1）- ✅ 已完成
- **缓动函数**：镜头运动更流畅自然
- **组合运动**：支持zoom + pan同时执行
- **可选旋转**：增加动感（实验性）
- **性能提升**：观看体验↑40%

📖 详细文档：[docs/camera-action-enhanced.md](./docs/camera-action-enhanced.md)

### 🌟 2.5D视差效果（方案2）- ✅ 已完成
- **深度位移**：基于DepthAnything V2的像素级视差
- **无损画质**：解决Layer Separation带来的黑边与割裂问题
- **M4优化**：利用Neural Engine加速深度推理
- **最佳实践**：推荐用于3D/写实风格 (Pop Mart, Pixar)

📊 实施进度：[docs/parallax-2.5d-plan.md](./docs/parallax-2.5d-plan.md)

### 🚀 批量生成工具 - ✅ 已完成
- **CSV导入**：从文件批量导入生成任务
- **任务队列**：自动串行执行，错误隔离
- **执行报告**：生成Markdown格式的运行报告


---

## 核心能力

- **一键全流程**：`script → image → (animate) → audio → video`
- **分类驱动的内容策略**：按类目自动选择画风、配音池、BGM、视频排版（book/movie）
- **多模型支持**：
  - [x] 文案/脚本：火山引擎（豆包/Ark）、OpenAI、Google Gemini
  - [x] 图像：火山引擎（豆包/即梦）、OpenAI（DALL·E）、Mock
  - [ ] 动画（可选）：Luma、Stability、Mock
- **双语字幕**：英语绘本自动生成英文+中文拼音双语字幕
- **字幕与拼音**：开启后自动为中文字幕渲染拼音字幕
- **自动封面**：生成 `cover.png`（中文标题带拼音；英文标题自动换行/排版），并可生成标题配音
- **背景音乐**：按类目自动混入 `assets/music/` 中的 BGM（自动降低音量，避免盖过人声）
- **AI片头引导语**：自动生成符合故事寓意的引导文案
- **品牌片尾**：可自定义品牌logo和宣传信息

## 技术栈

- **Python**：要求 `>= 3.13`（见 `pyproject.toml`）
- **包管理**：`uv`（推荐）或 `pip`
- **多媒体合成**：`moviepy`
- **TTS**：`edge-tts` / 火山引擎TTS
- **拼音**：`pypinyin`
- **配置**：`config.yaml`（`PyYAML`）
- **AI增强**：
  - `coremltools` - Core ML模型支持
  - `transformers` - HuggingFace模型

## 快速开始

### 1）安装依赖

推荐使用 `uv`：

```bash
# 基础功能
uv sync

# 包含2.5D视差效果（可选）
uv sync --extra parallax
```

或使用 `pip`：

```bash
pip install -e .
```

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
- `models.styles`（风格提示词库）
- `models.category_defaults`（类目→默认风格）
- `models.category_aliases`（类目别名，如 `cy/en/db`）
- `models.category_layouts`（类目→布局：`book`/`movie`）
- `models.category_voices`（类目→TTS语音池）
- `models.category_bgm`（类目→BGM 文件）
- `models.category_speech_rates`（类目→语速调整）
- `models.category_scene_count`（类目→场景数量范围）

### 3）一键生成视频

```bash
python main.py --topic "刻舟求剑" --category cy
```

常用组合示例：

```bash
# 开启拼音字幕
python main.py --topic "守株待兔" --category cy --subtitles

# 强制指定风格
python main.py --topic "三国演义" --category ls --style pixar

# 强制指定配音
python main.py --topic "The Lion and the Mouse" --category en --voice en-US-AnaNeural

# 双语绘本（自动生成英文+中文双语字幕）
python main.py --topic "Little Red Riding Hood" --category en
python main.py --topic "Little Red Riding Hood" --category en
```

### 4）批量生成

支持通过 CSV 文件批量导入任务：

```bash
python batch_main.py --file input.csv
```

CSV 格式示例：
```csv
topic,category,style,voice,enable_parallax
刻舟求剑,cy,,
Little Red Riding Hood,en,,en-US-AnaNeural,True
```

## 常用参数（CLI）

- **`--topic`**：主题内容（给 AI 理解用）
- **`--title`**：封面主标题（可选；不填则使用 `--topic` 原文）
- **`--subtitle`**：脚本副标题/章节（可选）
- **`--cover-subtitle`**：封面小标题（可选）
- **`--category`**：类目/系列（支持别名，见 `config.yaml`）
- **`--style`**：覆盖画风（风格键或自定义提示词）
- **`--voice`**：覆盖 TTS 语音
- **`--subtitles`**：开启字幕（中文自动拼音）
- **`--step`**：分步执行：`script | image | animate | audio | video | all`
- **`--force`**：强制重新生成

## 支持的类目

| 类目 | 别名 | 默认风格 | 布局 | 语音 |
|------|------|----------|------|------|
| 成语故事 | cy | pop_mart | book | 云希 |
| 儿童绘本 | et | western_chd_book | book | 晓伊 |
| 睡前故事 | sq | pixar | book | 晓晓 |
| 英语绘本 | en | western_chd_book | book | Ana (EN) |
| 历史故事 | ls | ink_wash | movie | 云扬 |
| 神话故事 | sh | ink_wash | movie | 云扬 |
| 民间故事 | mj | watercolor | book | 云希 |
| 少儿百科 | bk | chibi_2d | movie | 云夏 |
| 读书分享 | db | flat_tech | movie | 云希 |
| 有声读物 | ys | watercolor | movie | 晓晓 |

## 分步运行（调试/可控生产）

```bash
# 1. 生成脚本
python main.py --topic "小狗钱钱" --category db --step script

# 2. 生成图片
python main.py --topic "小狗钱钱" --category db --step image

# 3. 生成音频
python main.py --topic "小狗钱钱" --category db --step audio

# 4. 合成视频
python main.py --topic "小狗钱钱" --category db --step video
```

> 脚本会落到当前作品目录下的 `script.json`，你可以手动修改后再继续生成后续步骤。

## 输出结构

主流程输出默认在：

```
<output_dir>/<类目>/<主题>/
  script.json                    # 脚本数据
  script.md                      # 脚本预览
  cover.png                      # 视频封面
  hook_audio.mp3                 # 片头引导语音
  title_audio.mp3                # 标题朗读
  scene_*.png                    # 场景图片
  scene_*.mp3                    # 场景配音
  scene_*.mp4                    # 场景视频（如开启动画）
  final_video.mp4                # 最终成片
  metadata.json / metadata.md    # 发布信息
```

## 功能配置

### Camera Effects（镜头效果）

```yaml
camera_effects:
  enable_easing: true          # 缓动函数
  enable_rotation: false       # 旋转效果
  rotation_degree: 1.5         # 旋转角度
  movement_intensity: 1.25     # 运动强度
```

### 2.5D Parallax（视差效果 - 实验性）

```yaml
parallax_effects:
  enable: false                          # 默认关闭
  model_path: "models/DepthAnythingV2SmallF16.mlpackage"
  num_layers: 3                          # 分层数量
  movement_scale: 1.2                    # 视差倍率
  cache_depth_maps: true                 # 缓存深度图
  disabled_categories:                   # 不适合的类目
    - "历史故事"  # 水墨画风格
    - "神话故事"
    - "民间故事"  # 水彩风格
    - "儿童绘本"  # 手绘风格
```

**重要**: 视差效果对图片风格有严格要求！
- ✅ **适合**: Pop Mart、Pixar等3D风格（成语故事、睡前故事）
- ❌ **不适合**: 油画、水墨、扁平插画等艺术风格

详见 [docs/parallax-style-guide.md](./docs/parallax-style-guide.md) 和 [models/README.md](./models/README.md)

### 双语模式

```yaml
features:
  enable_bilingual_mode: true            # 总开关
  bilingual_audio_pause: 1.0             # 英文与中文停顿
  bilingual_cn_voice: "zh-CN-XiaoxiaoNeural"  # 中文音色
```

自动对"英语绘本"类目生效。

## 背景音乐素材

将音乐文件放在 `assets/music/`，并在 `config.yaml` 的 `models.category_bgm` 中配置映射。

仓库自带示例音乐：
- `guqin.mp3` - 古琴（成语故事）
- `epic.mp3` - 史诗（历史故事）
- `lullaby.mp3` - 摇篮曲（睡前故事）
- `playful.mp3` - 欢快（儿童绘本）
- `storybook.mp3` - 绘本风（英语绘本）
- `meditation.mp3` - 冥想（读书分享）

## 测试

项目包含多个测试脚本：

```bash
# 完整流水线测试
python tests/dbg_full_pipline.py

# 缓动效果对比
python tests/compare_easing_effect.py

# 深度估计测试（需要先下载模型）
python tests/test_depth_estimation.py
```

## 文档

- **Camera Action增强**：[docs/camera-action-enhanced.md](./docs/camera-action-enhanced.md)
- **2.5D视差方案**：[docs/parallax-2.5d-plan.md](./docs/parallax-2.5d-plan.md)
- **视差效果风格指南**：[docs/parallax-style-guide.md](./docs/parallax-style-guide.md)
- **图层分离技术**：[docs/layer-separation-tech.md](./docs/layer-separation-tech.md)

## 项目结构

```
ai-video-maker/
├── main.py                    # 主入口
├── config.yaml                # 配置文件
├── pyproject.toml             # 项目定义
├── steps/                     # 核心模块
│   ├── script/                # 脚本生成
│   ├── image/                 # 图片生成
│   ├── audio/                 # 音频生成
│   ├── video/                 # 视频合成
│   └── effects/               # 特效模块（2.5D视差）
├── tests/                     # 测试脚本
├── docs/                      # 文档
├── assets/                    # 资源文件
│   ├── music/                 # 背景音乐
│   ├── fonts/                 # 字体
│   └── image/                 # 品牌素材
├── models/                    # ML模型（gitignore）
└── output/                    # 输出目录
```

## 开发路线图

- [x] 基础视频生成流水线
- [x] 多模型支持
- [x] 分类内容策略
- [x] 双语字幕支持
- [x] Camera Action增强（方案1）
- [x] 2.5D视差效果（方案2 - 核心完成，适用3D风格）
- [x] 2.5D视差效果（方案2 - 核心完成，适用3D风格）
- [x] 批量生成工具
- [ ] Web UI界面
- [ ] Web UI界面

## 贡献

欢迎提交Issue和Pull Request！

## 许可证

见 `LICENSE`。

---

**注**：本项目使用AI生成内容，请确保遵守相关服务条款和版权法律。
