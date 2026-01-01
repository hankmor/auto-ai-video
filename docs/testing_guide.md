# 🧪 测试与调试指南 (Testing Guide)

本项目包含一套完整的自动化集成测试工具，方便开发者在不消耗 API 额度的情况下验证代码逻辑、排版效果和音画合成流程。

## 1. 核心测试脚本: `tests/test_gen.py`

这个脚本用于模拟真实生成流程，支持“端到端”生成一个迷你视频（包含一个场景、封面、音频和字幕）。

### 📍 位置
`tests/test_gen.py`

### 🚀 快速开始

在项目根目录下运行：

```bash
# 1. 基础测试 (默认生成 "成语故事" 类目)
python tests/test_gen.py "测试主题"

# 2. 指定类目 (测试不同排版和BGM)
python tests/test_gen.py "深度睡眠" --category "助眠冥想"

# 3. 使用已有脚本 (跳过 LLM 生成，仅测试后续合成)
python tests/test_gen.py --script tests/output/xxxxx/script_source.json
```

### ⚙️ 参数说明

| 参数 | 说明 | 示例 |
| :--- | :--- | :--- |
| `topic` | (位置参数) 视频主题，用于生成脚本与封面标题。 | `"愚公移山"` |
| `--script` | 指定本地 JSON 脚本路径。若指定此项，将跳过 LLM 步骤，直接使用该脚本生成。 | `--script output/script.json` |
| `--category` | 模拟视频类目。这决定了排版模式 (Movie/Book) 和背景音乐。 | `--category "儿童绘本"` |

---

## 2. 模拟模式 (Mock Mode)

为了节省 API 费用和加快迭代速度，项目支持各种 Mock 模式。

### 🎭 启用方法
修改 `config.yaml` 文件：

```yaml
models:
  # 图像生成 Mock（生成纯色占位图，用于排版/字幕/BGM 测试）
  image:
    provider: "volcengine"
    model: "mock"  # <--- 修改这里（也可保持 provider，不影响 mock）
    
  # LLM 本身通常不建议 Mock，但可以通过提供 --script 参数来跳过 LLM 调用
```

### Mock 模式的特性
*   **速度极快**: 毫秒级生成图片。
*   **0 成本**: 不消耗 Tokens。
*   **易于调试**: 生成的图片上印有分辨率、Prompt 等调试信息，方便检查参数传递是否正确。
*   **格式自适应**: 自动根据配置生成 9:16 或 16:9 的占位图，用于测试排版适配性。

---

## 3. 常见测试场景

### ✅ 场景 A: 验证新的排版样式 (Layout)
1.  修改 `config.yaml` 将 `models.image.model` 设为 `mock`。
2.  运行测试命令：
    ```bash
    python tests/test_gen.py "排版测试" --category "成语故事"
    ```
3.  检查 `tests/output/xxxx/test_video.mp4`，确认字幕、封面位置是否正确。

### ✅ 场景 B: 验证背景音乐逻辑
1.  确保 `config.yaml` 中配置了目标类目的 BGM。
2.  运行测试：
    ```bash
    python tests/test_gen.py "BGM测试" --category "助眠冥想"
    ```
3.  查看控制台输出是否包含 `Found matching BGM` 和 `BGM mixed in`。

### ✅ 场景 C: 完整的真实生成 (Production Test)
1.  修改 `config.yaml` 还原 `models.image.model` 为真实模型 (如 `doubao-3.0`)。
2.  配置好 API Key。
3.  运行测试（建议使用简短主题）：
    ```bash
    python tests/test_gen.py "测试生成"
    ```

## 4. 输出产物
所有测试产物默认保存在 `tests/output/<时间戳>/` 目录下：
*   `script_source.json`: 原始脚本数据
*   `scene_1.png`: 第一幕生成的图片
*   `scene_1.mp3`: 第一幕的配音
*   `cover.png`: 封面图
*   `test_video.mp4`: 最终合成的测试片段
