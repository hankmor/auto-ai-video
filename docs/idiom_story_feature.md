# 成语故事功能说明（与当前仓库结构一致）

## 功能说明

当类目为“成语故事”（或类目名称中包含“成语”）时，脚本生成会注入专门的提示词约束，确保**最后一幕包含成语总结**，形成完整的教育闭环。

## 实现位置

### 1）策略类：`IdiomStoryStrategy`

文件：`prompt/prompt_strategy.py`

- 该策略会向系统提示词注入“成语故事特化指令”
- 其中包含：成语总结、字面意思、寓意、近义词与反义词要求等

### 2）工厂路由：`StrategyFactory`

文件：`prompt/factory.py`

- 当 `category == "成语故事"` 或 `category` 字符串包含“成语”时，返回 `IdiomStoryStrategy`

## 使用示例

```bash
# 方法1：直接使用“成语故事”类目
python main.py --topic "守株待兔" --category "成语故事"

# 方法2：类目名称包含“成语”也会触发
python main.py --topic "刻舟求剑" --category "儿童成语"
```

## 推荐配置（`config.yaml` 示例）

> 本项目通过 `models.category_*` 一组映射来配置“类目→风格/布局/配音/BGM”等策略。

```yaml
models:
  category_defaults:
    "成语故事": "ink_wash"          # 或 pop_mart 等

  category_layouts:
    "成语故事": "book"             # 上图下文的绘本式布局

  category_voices:
    "成语故事": ["zh-CN-YunxiNeural", "zh-CN-XiaoyiNeural"]

  category_bgm:
    "成语故事": "guqin.mp3"
```

## 最佳实践

- **生成后检查**：最后一幕是否包含成语总结、近义词与反义词
- **需要微调时**：可手动编辑作品目录下的 `script.json`，再继续执行 `--step image/audio/video`


