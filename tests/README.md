# 测试脚本说明

本目录包含项目的各类测试脚本。

## 视差效果测试 (2.5D Parallax)

### `test_parallax_animation.py` - 完整测试
完整的2.5D视差流程测试，包括深度估计、图层分离和视差动画生成。

**用途**: 验证整个视差效果流程是否正常工作

**运行**:
```bash
python tests/test_parallax_animation.py
```

**输出**: `tests/output/parallax_test/parallax_demo.mp4`

**流程**:
1. 深度估计 (Depth-Anything V2)
2. 图层分离 (3层)
3. 视差动画 (pan_right, 3秒)
4. 导出MP4视频

**注意**: 需要先安装parallax依赖 (`uv sync --extra parallax`)

---

### `test_depth_estimation.py` - 深度估计
单独测试深度估计模块的性能和准确性。

**用途**: 
- 验证Depth-Anything V2模型加载
- 测试M4 Neural Engine性能
- 验证缓存机制

**运行**:
```bash
python tests/test_depth_estimation.py
```

**输出**: 
- `output/depth_estimation/depth_map.png` - 深度图可视化
- 控制台性能数据

**性能指标**:
- 首次推理: ~46ms (2048x3584)
- 缓存命中: ~1.4ms
- 加速比: 101.6x



---

## 其他测试

### `dbg_full_pipline.py` - 完整流水线
测试整个视频生成流水线 (脚本→图片→音频→视频)。

**运行**:
```bash
python tests/dbg_full_pipline.py
```

---

### `compare_easing_effect.py` - 缓动效果对比
对比有无缓动函数的镜头效果差异。

**运行**:
```bash
python tests/compare_easing_effect.py
```

**输出**: 两个对比视频

---

## 依赖说明

### 基础测试
只需基础依赖即可运行大部分测试：
```bash
uv sync
```

### 视差效果测试
需要额外安装parallax依赖：
```bash
uv sync --extra parallax
```

包括：
- `coremltools` - Core ML支持
- `transformers` - HuggingFace模型
- `scipy` - 科学计算（inpainting和边缘平滑）

---

## 测试数据

测试图片位于 `tests/test_images/`（gitignore）

如需测试，请准备：
- 高分辨率图片 (推荐 >1024px)
- **适合的风格**: 3D渲染、写实照片
- **不适合**: 油画、水墨、扁平插画

详见：[docs/parallax-style-guide.md](../docs/parallax-style-guide.md)

---

## 常见问题

### 1. scipy未安装
```
⚠️ scipy未安装，跳过inpainting
```

**解决**: `uv add scipy` 或 `uv sync --extra parallax`

---

### 2. 模型文件不存在
```
❌ 模型文件不存在: models/DepthAnythingV2SmallF16.mlpackage
```

**解决**: 下载模型，见 [models/README.md](../models/README.md)

---

### 3. 测试图片黑边/割裂
这是正常的，说明图片风格不适合2.5D视差。

**原因**: 深度估计对艺术风格图片效果不佳

**解决**: 
- 使用3D渲染风格图片
- 或禁用视差效果，使用Ken Burns

---

## 性能基准

| 测试 | 图片尺寸 | 耗时 | 备注 |
|------|----------|------|------|
| 深度估计 | 2048x3584 | 46ms | M4 Neural Engine |
| 图层分离 | 2048x3584 | ~1.7s | 3层 + inpainting |
| 视差动画 | 2048x3584 | ~3s | 3秒视频，24fps |

总计: ~5秒生成一个3秒视差视频

---

## 调试技巧

### 查看详细日志
```bash
LOG_LEVEL=DEBUG python tests/test_parallax_animation.py
```

### 只测试某个模块
```python
# test_depth_only.py
from steps.effects.depth_estimator import DepthEstimator

estimator = DepthEstimator(model_path="...")
depth_map = estimator.estimate("test.jpg")
```

### 自定义参数
编辑测试脚本中的参数：
```python
# test_parallax_animation.py
separator = LayerSeparator(num_layers=5)  # 改为5层
animator = ParallaxAnimator(movement_scale=1.5)  # 更大运动幅度
```
