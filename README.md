# AutoMaker - 自动化短视频生成工坊 🎬

AutoMaker 是一个全自动化的 AI 短视频生成与剪辑工具。它能根据一个简单的主题（Topic），利用 LLM 撰写剧本，调用 AI 绘画生成分镜，使用 TTS 生成配音，最后自动剪辑成片。

## ✨ 核心特性
*   **全流程自动化**: 从创意到成片一键完成。
*   **多模型支持**:
    *   **LLM**: Volcengine (Doubao), OpenAI, Google Gemini
    *   **Image**: Volcengine (Doubao/Jimeng), OpenAI (DALL-E 3)
*   **智能排版**:
    *   **电影模式 (Movie)**: 沉浸式全屏画面 + 底部悬浮字幕。
    *   **绘本模式 (Book)**: 上图下文分屏，大号字体，适合儿童阅读。
*   **丰富的风格库**: 内置水墨、皮克斯、日漫、极简治愈等 10+ 种视觉风格。
*   **手机竖屏优化**: 完美支持 9:16 (TikTok/Douyin/Shorts) 比例。

## 📂 文档索引 (Documentation)

*   **[快速开始 (Quick Start)](README.md#🚀-快速开始)**: 环境安装与基础运行。
*   **[配置指南 (Configuration)](docs/configuration.md)**: 详解 `config.yaml`，包括 API Key 配置、画风自定义、类目绑定。
*   **[测试与调试 (Testing Guide)](docs/testing_guide.md)**: 如何使用 `tests/test_gen.py` 进行低成本的逻辑验证和 Mock 测试。
*   **[架构说明 (Architecture)](docs/architecture.md)**: 系统模块拆解与代码结构。
*   **[API 参考 (API Reference)](docs/api_reference.md)**: 核心类与方法的详细说明。

## 🚀 快速开始

### 1. 安装依赖
```bash
# 建议使用 Python 3.10+
pip install -r requirements.txt
```

### 2. 配置项目
复制配置文件模板（如果有）或直接修改 `config.yaml`:
```yaml
keys:
  volc_access_key: "YOUR_AK"
  volc_secret_key: "YOUR_SK"
```

### 3. 运行生成
```bash
# 生成一个关于“守株待兔”的视频
python auto_maker/main.py --topic "守株待兔" --category "成语故事"
```

### 4. 常用命令
```bash
# 指定视觉风格
python auto_maker/main.py --topic "未来城市" --style cyberpunk

# 运行测试 (不消耗 Token)
python tests/test_gen.py "测试运行" --category "成语故事"
```


## 📚 典型类目示例 (Examples)

### 1. 📖 成语故事 (Idle Stories)
*风格：水墨画 | 音乐：古琴 | 效果：0.8s 叠化*
```bash
python auto_maker/main.py --topic "守株待兔" --category "成语故事"
```

### 2. 🏰 历史解说 (History)
*风格：写实历史画作 | 音乐：史诗 | 效果：0.8s 叠化*
```bash
python auto_maker/main.py --topic "赤壁之战" --category "历史解说"
```

### 3. 🌙 睡前故事 (Bedtime Stories)
*风格：皮克斯3D | 音乐：摇篮曲 | 效果：0.8s 叠化*
```bash
python auto_maker/main.py --topic "小兔子找妈妈" --category "睡前故事"
```

### 4. 🧘 助眠冥想 (Meditation)
*风格：极简禅意 | 音乐：冥想曲 | 效果：2.0s 极慢叠化*
```bash
python auto_maker/main.py --topic "深海漫游引导" --category "助眠冥想"
```

### 5. 📚 儿童绘本 (Picture Book)
*风格：扁平插画 | 音乐：欢快 | 效果：硬切 (翻页感)*
```bash
python auto_maker/main.py --topic "勇敢的小火车" --category "儿童绘本"
```

### 6. 🇬🇧 英语绘本 (English Book)
*风格：迪士尼 | 音乐：管弦乐 | 语言：纯正美音*
```bash
python auto_maker/main.py --topic "The Three Little Pigs" --category "英语绘本"
```

### 7. 💥 漫画解说 (Manga)
*风格：日漫黑白 | 音乐：燃曲 | 效果：硬切 (快节奏)*
```bash
python auto_maker/main.py --topic "进击的巨人第一季解说" --category "漫画解说"
```

### 💡 进阶参数
*   `--force`: 强制重新生成已存在的资源（图片/音频）。默认情况下，再次运行相同命令会自动**断点续传**。
*   `--subtitles`: 强制开启拼音字幕（覆盖默认配置）。

## 🛠️ 项目结构
```
.
├── auto_maker/        # 核心源码
│   ├── image_factory.py  # 图像生成工厂
│   ├── video_editor.py   # 视频剪辑与合成
│   └── ...
├── config.yaml        # 全局配置文件
├── output/            # 生成结果目录
├── tests/             # 测试脚本
└── docs/              # 详细文档
```
