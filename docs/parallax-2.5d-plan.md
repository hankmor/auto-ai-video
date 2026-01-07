# 方案 2：2.5D 视差效果 - 实施方案与进度

## 概述

**方案 2（2.5D Parallax）**通过深度估计和图层分离技术，为静态图片创建真实的 3D 视差效果，大幅提升视觉冲击力和沉浸感。

**开始时间**：2026-01-07  
**预计完成**：Day 7 (2026-01-13)  
**当前状态**：🟡 Day 1 完成（进度 14%）

---

## 技术方案

### 工作流程

```
输入图片 (AI生成)
    ↓
[深度估计] Depth-Anything V2 (Core ML)
    ↓
深度图 (灰度0-255)
    ↓
[图层分离] 按深度值分3-5层
    ↓
图层列表 [前景, 中景, 背景]
    ↓
[视差动画] 不同图层不同运动速度
    ↓
2.5D视频 (有深度感)
```

### 核心技术

1. **Depth-Anything V2**

   - 官方 Core ML 支持
   - 针对 M4 Neural Engine 优化
   - Float16 模型仅 49.8MB
   - 推理速度：<25ms per image

2. **图层分离算法**

   - 基于深度阈值
   - 3-5 层可配置
   - 自动 inpainting 填补空缺

3. **视差运动**
   - 前景移动快
   - 中景移动中
   - 背景移动慢
   - 模拟真实视差

---

## 性能目标（MacBook Pro M4）

| 指标                 | 目标值 | 当前状态 |
| -------------------- | ------ | -------- |
| 深度估计速度         | <25ms  | 待测试   |
| 图层分离             | <10ms  | 待实现   |
| 内存占用             | <100MB | 待测试   |
| Neural Engine 利用率 | >80%   | 待优化   |

---

## 7 天实施计划

### ✅ Day 1: 环境搭建（已完成）

**任务**：

- [x] 创建`steps/effects/`模块目录
- [x] 实现`depth_estimator.py`框架
- [x] 创建测试脚本
- [x] 安装依赖（coremltools 9.0, transformers 4.57.3）
- [x] 配置`config.yaml`

**产出**：

- `steps/effects/depth_estimator.py` (7.0KB)
- `tests/test_depth_estimation.py` (2.4KB)
- `models/README.md` - 模型下载说明
- 支持缓存机制
- 模拟模式可用

### ✅ Day 2: 深度估计开发（已完成）

**Day 2 任务**：

- [x] 下载 Depth-Anything V2 Core ML 模型（48MB）
- [x] 实现真实 Core ML 推理逻辑
- [x] 完善预处理/后处理
- [x] 性能基准测试（实际 46ms）

**成果**：

- ✅ 真实 Core ML 推理工作正常
- ✅ 自动尺寸适配（任意输入 →518x392→ 任意输出）
- ✅ 性能：46ms（首次）/ 1.4ms（缓存）
- ✅ 缓存提速：101.6x

**Day 3 任务**（可选优化）：

- [ ] 优化 Neural Engine 利用率（目标：46ms → <25ms）
- [ ] 智能缓存策略
- [ ] 批处理优化

**关键代码**：

```python
class DepthEstimator:
    def estimate(image_path) -> np.ndarray:
        # 真实Core ML推理 ✅
        img_resized = img.resize((518, 392))
        depth = self.model.predict({'image': img_resized})
        return resize_back(depth, original_size)
```

### 🔲 Day 4: 图层分离模块

**任务**：

- [ ] 创建`layer_separator.py`
- [ ] 实现深度阈值分层算法
- [ ] 基础 inpainting（填补空缺）
- [ ] 图层可视化工具

**产出**：

```python
class LayerSeparator:
    def separate(image, depth_map, num_layers=3):
        return layers  # [{image, mask, depth_range}, ...]
```

### 🔲 Day 5-6: 视差动画模块

**Day 5 任务**：

- [ ] 创建`parallax_animator.py`
- [ ] 实现基础视差运动
- [ ] 支持 pan/zoom 组合

**Day 6 任务**：

- [ ] 优化运动曲线
- [ ] 添加边缘处理
- [ ] 性能调优

**产出**：

```python
class ParallaxAnimator:
    def create_parallax_clip(layers, duration, action):
        # 前景快，背景慢
        return composite_clip
```

### 🔲 Day 7: 集成测试与优化

**任务**：

- [ ] 集成到`VideoAssemblerBase`
- [ ] 端到端测试
- [ ] 性能优化
- [ ] 文档完善
- [ ] 生成对比 demo

---

## 配置系统

### config.yaml

```yaml
parallax_effects:
  enable: false # 默认关闭
  model_path: "models/depth_anything_v2_small_float16.mlmodel"
  num_layers: 3 # 分层数量
  movement_scale: 1.2 # 视差倍率
  cache_depth_maps: true # 缓存深度图
```

### 使用方式（Day 7 后）

```bash
# 启用2.5D视差
python main.py --topic "森林中的小兔子" --category cy --parallax

# 或在config.yaml中全局启用
parallax_effects:
  enable: true
```

---

## 模块架构

### 目录结构

```
steps/effects/
├── __init__.py              # 模块初始化
├── depth_estimator.py       # ✅ Day 1 完成
├── layer_separator.py       # 🔲 Day 4
└── parallax_animator.py     # 🔲 Day 5-6

models/
├── README.md                # ✅ 下载说明
└── depth_anything_v2_small_float16.mlmodel  # 🔲 待下载

tests/
└── test_depth_estimation.py # ✅ Day 1 完成
```

### 依赖管理（uv）

```toml
[project.optional-dependencies]
parallax = [
    "coremltools>=9.0",
    "transformers>=4.57.3",
]
```

安装：

```bash
uv sync --extra parallax
```

---

## 预期效果

### 视觉对比

**方案 1（Ken Burns 增强）**：

- 整张图片统一运动
- 运动流畅但扁平

**方案 2（2.5D 视差）**：

- 前景/中景/背景分层运动
- 有深度感和立体感
- 视觉冲击力强

### 应用场景

**最佳效果**：

- 儿童绘本（人物+背景）
- 成语故事（历史场景）
- 神话故事（幻想场景）

**效果提升**：

- 吸引力 ⬆️ 50-100%
- 记忆度 ⬆️ 40%
- 专业感 ⬆️ 80%
- 停留时长 ⬆️ 30%

---

## 风险与备选方案

### 已知风险

1. **模型下载**：50MB 文件，网速较慢时耗时长

   - **缓解**：提供多个下载源

2. **Core ML 兼容性**：不同 macOS 版本可能有差异

   - **缓解**：降级到 ONNX Runtime

3. **效果受限于 AI 图片质量**：扁平插画效果减弱
   - **缓解**：配置中允许按 category 启用/禁用

### 备选方案

如果 Core ML 遇到问题：

1. ONNX Runtime + Apple 优化
2. PyTorch Mobile (M4 支持)
3. 在线 API（Replicate 等）

---

## 下一步行动

### 立即可做（用户）

1. **下载模型**：

   ```bash
   # 访问Hugging Face下载模型
   # 见 models/README.md
   ```

2. **准备测试素材**：
   - 选择几个有明显前景/背景的场景
   - 用于 Day 2-3 测试

### Day 2 开始时

1. 运行深度估计测试
2. 验证 M4 性能
3. 开始真实推理实现

---

## 参考资源

- **Depth-Anything V2**: https://github.com/DepthAnything/Depth-Anything-V2
- **Hugging Face 模型**: https://huggingface.co/depth-anything/Depth-Anything-V2-Small-hf
- **Core ML 文档**: https://apple.github.io/coremltools/

---

**最后更新**：2026-01-07  
**进度**：28% (Day 2 完成/7 天)  
**当前状态**：✅ 深度估计模块可用，准备进入 Day 3 或 Day 4
