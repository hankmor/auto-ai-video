# 配置指南（与当前仓库结构一致）

本项目的配置集中在 `config/config.py`，会优先从环境变量读取密钥与默认值，并在启动时加载项目根目录的 `config.yaml`。

## 环境变量

在运行程序前，请确保设置了以下必要的环境变量：

| 变量名 | 必填 | 描述 | 示例 |
| --- | --- | --- | --- |
| `VOLC_ACCESS_KEY` | 否 | 火山引擎 AK（用于图像等服务） | `AK...` |
| `VOLC_SECRET_KEY` | 否 | 火山引擎 SK（用于图像等服务） | `SK...` |
| `ARK_API_KEY` | 否 | Ark API Key（可选，用于 LLM） | `sk-...` |
| `OPENAI_API_KEY` | 否 | OpenAI Key（用于 LLM/图像，视你选择的 provider） | `sk-...` |
| `GEMINI_API_KEY` | 否 | Gemini Key（用于 LLM/图像，视你选择的 provider） | `AIza...` |
| `LUMA_API_KEY` | 否 | Luma Dream Machine（图生视频） | `kp-...` |
| `STABILITY_API_KEY` | 否 | Stability（图生视频） | `sk-...` |

## 🔑 API 申请地址

| 服务商            | 用途           | 申请官网                                                               | 说明                            |
| ----------------- | -------------- | ---------------------------------------------------------------------- | ------------------------------- |
| **OpenAI**        | LLM, DALL-E 3  | [platform.openai.com](https://platform.openai.com/api-keys)            | 核心依赖，必须申请              |
| **Luma Labs**     | Image-to-Video | [lumalabs.ai/dream-machine/api](https://lumalabs.ai/dream-machine/api) | 让画面动起来 (需申请内测或付费) |
| **Stability AI**  | Image-to-Video | [platform.stability.ai](https://platform.stability.ai/)                | 备选动画方案                    |
| **Google Gemini** | LLM            | [aistudio.google.com](https://aistudio.google.com/)                    | 免费额度较高，可作为 GPT 备选   |

## 配置文件（`config.yaml`）

我们推荐在项目根目录创建 `config.yaml` 进行统一管理，优先级高于代码默认值。

**示例 `config.yaml`**:

```yaml
# 项目设置（注意：使用 main.py 时会按“products/<类目>/<主题>”覆盖输出目录）
project:
  output_dir: "./output"

models:
  # 文案/脚本模型
  llm:
    provider: "volcengine"   # 或 openai / google
    model: "ep-xxxx"         # 替换为你的 Endpoint ID / 模型名

  # 图像模型
  image:
    provider: "volcengine"   # 或 openai / google
    model: "doubao-3.0"      # 或 jimeng-4.0 / dall-e-3 / mock

  # 动画（图生视频，可选）
  animator: "mock"           # luma / stability / mock

  # TTS
  tts_voice: "zh-CN-YunxiNeural"

  # 类目→风格键 / 别名 / 布局 / 语音池 / BGM 等（详见仓库自带 config.yaml 注释）
  category_defaults: {}
  category_aliases: {}
  category_layouts: {}
  category_voices: {}
  category_bgm: {}

features:
  enable_animation: false
  enable_subtitles: true
```

## 代码配置类（`config/config.py`）

如果不使用 YAML，也可以修改代码中的 `Config` 类：

```python
@dataclass
class Config:
    # ...

    # LLM 模型选型
    LLM_MODEL: str = "gpt-4o"

    # 绘图模型
    IMAGE_MODEL: str = "dall-e-3"

    # 配音角色 (Edge-TTS)
    # 常用中文角色:
    # - zh-CN-YunxiNeural (男声, 沉稳)
    # - zh-CN-XiaoxiaoNeural (女声, 亲切)
    TTS_VOICE: str = "zh-CN-YunxiNeural"
```

## 输出目录

默认情况下（不经过 `main.py` 的目录重写逻辑），会使用 `config.yaml` 的 `project.output_dir`（默认为 `./output`）。

当你通过 `python main.py ...` 运行主流程时，会自动按如下结构组织产物，便于批量管理：

```
products/<类目>/<主题>/
```

目录中常见产物包括：

1. 生成的脚本日志
2. 分镜图片 (`scene_N.png`)
3. 旁白音频 (`scene_N.mp3`)
4. 封面 (`cover.png`) 与标题配音 (`title_audio.mp3`)
5. 最终视频（如 `final_video.mp4`）

**注意**: 每次运行都会覆盖同名的输出文件，建议在 `output/` 下手动归档重要结果。
