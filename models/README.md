# Models 目录

此目录存储用于 2.5D 视差效果的机器学习模型。

## 必需模型

### Depth-Anything V2 Small (Float16) - Core ML 版本

**用途**：深度估计，用于视差效果  
**大小**：~50MB  
**格式**：Core ML (.mlpackage)  
**官方来源**：Apple 官方发布的 Core ML 版本

#### 下载说明

**方式 1：使用 Hugging Face CLI（推荐）**

```bash
# 1. 安装 huggingface_hub（如果尚未安装）
pip install huggingface_hub

# 2. 下载 Apple 官方 Core ML 模型
huggingface-cli download apple/coreml-depth-anything-v2-small \
    DepthAnythingV2SmallF16.mlpackage \
    --local-dir models/
```

**方式 2：手动下载**

1. 访问：https://huggingface.co/apple/coreml-depth-anything-v2-small/tree/main
2. 下载整个`DepthAnythingV2SmallF16.mlpackage`文件夹（或 zip）
3. 解压到此目录：`models/DepthAnythingV2SmallF16.mlpackage/`

#### ⚠️ 重要说明

**不要下载 .pth 文件！**

- `.pth` 文件是 PyTorch 格式，不是 Core ML 格式
- 我们需要的是 `.mlpackage` 格式（Apple Core ML）
- 只有 Core ML 格式才能在 M4 的 Neural Engine 上高效运行

**正确的文件结构**：

```
models/
└── DepthAnythingV2SmallF16.mlpackage/
    ├── Data/
    ├── Manifest.json
    └── ...
```

## 验证

下载后，验证文件夹是否存在：

```bash
ls -lh models/DepthAnythingV2SmallF16.mlpackage
# 应显示一个mlpackage目录结构
```

## 注意事项

⚠️ 模型文件**不会**提交到 Git（见`.gitignore`）。  
每个开发者需要自行下载模型到本地。
