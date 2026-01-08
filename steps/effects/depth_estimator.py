"""
深度估计模块
===========
使用Depth-Anything v2 Core ML模型估计图像深度

性能目标（M4）：
- 推理速度：< 25ms per image
- 内存占用：< 100MB
- 运行在Neural Engine
"""

import os
import numpy as np
from PIL import Image
from typing import Optional, Tuple
from util.logger import logger


class DepthEstimator:
    """
    深度估计器

    使用Depth-Anything V2 Core ML模型估计单张图片的深度图
    """

    def __init__(self, model_path: Optional[str] = None):
        """
        初始化深度估计器

        Args:
            model_path: Core ML模型路径，如果为None则使用默认路径
        """
        self.model_path = model_path or self._get_default_model_path()
        self.model = None
        self._load_model()

    def _get_default_model_path(self) -> str:
        """获取默认模型路径"""
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "models",
            "DepthAnythingV2SmallF16.mlpackage",
        )

    def _load_model(self):
        """
        加载Core ML模型

        如果模型不存在，会提示用户下载
        """
        if not os.path.exists(self.model_path):
            logger.warning(
                f"⚠️ 深度估计模型未找到: {self.model_path}\n"
                f"   请从以下地址下载模型：\n"
                f"   https://huggingface.co/depth-anything/Depth-Anything-V2-Small-hf"
            )
            return

        try:
            import coremltools as ct

            self.model = ct.models.MLModel(self.model_path)
            logger.info(f"✅ 深度估计模型加载成功: {self.model_path}")
        except Exception as e:
            logger.error(f"❌ 模型加载失败: {e}")
            self.model = None

    def estimate(
        self, image_path: str, cache_dir: Optional[str] = None
    ) -> Optional[np.ndarray]:
        """
        估计图片深度

        Args:
            image_path: 输入图片路径
            cache_dir: 缓存目录，如果提供则会缓存深度图

        Returns:
            深度图 (H, W) numpy array, 值范围 0-255，或None如果失败
        """
        # 输入验证
        if not self._validate_input(image_path):
            return None

        if self.model is None:
            logger.error("❌ 模型未加载，无法进行深度估计")
            return None

        # 检查缓存
        if cache_dir:
            cached_depth = self._load_from_cache(image_path, cache_dir)
            if cached_depth is not None:
                logger.info("✅ 从缓存加载深度图")
                return cached_depth

        try:
            # 1. 加载图片
            img = Image.open(image_path).convert("RGB")
            original_size = img.size  # (W, H)

            # 验证图片尺寸
            if not self._validate_image_size(original_size):
                return None

            # 2. Resize到模型支持的尺寸
            # 模型要求: 较短边518px，较长边是14的倍数
            # 对于这个模型：518x392
            model_size = (518, 392)
            img_resized = img.resize(model_size, Image.Resampling.LANCZOS)

            # 3. Core ML推理
            import time

            start_time = time.time()
            # Core ML推理 - 使用resize后的图片
            prediction = self.model.predict({"image": img_resized})

            # 提取深度图 (输出是PIL Image或numpy array)
            depth_output = prediction.get("depth") or list(prediction.values())[0]

            # 转换为numpy array
            if isinstance(depth_output, Image.Image):
                # Core ML输出已经是PIL Image (Grayscale)
                depth_map = np.array(depth_output)
            elif hasattr(depth_output, "__array__"):
                depth_map = np.array(depth_output)
            else:
                depth_map = depth_output

            # 移除batch维度如果存在 (1, H, W) -> (H, W)
            if isinstance(depth_map, np.ndarray) and depth_map.ndim == 3:
                if depth_map.shape[0] == 1:
                    depth_map = depth_map.squeeze(0)
                elif depth_map.shape[2] == 1:
                    depth_map = depth_map.squeeze(2)

            # 释放中间变量
            del img_resized
            del prediction
            del depth_output

            elapsed = (time.time() - start_time) * 1000
            logger.info(
                f"🔍 深度估计完成，耗时: {elapsed:.2f}ms (输入尺寸: {original_size[0]}x{original_size[1]})"
            )

            # 4. 后处理 (resize回原始尺寸)
            depth_map = self._postprocess(depth_map, original_size)

            # 释放原始图片
            img.close()

            # 5. 缓存
            if cache_dir:
                self._save_to_cache(depth_map, image_path, cache_dir)

            return depth_map

        except MemoryError:
            logger.error(f"❌ 内存不足，无法处理图片: {image_path}")
            return None
        except Exception as e:
            logger.error(f"❌ 深度估计失败: {e}")
            import traceback

            logger.debug(traceback.format_exc())
            return None

    def _preprocess(self, img: Image.Image) -> np.ndarray:
        """
        预处理图片

        Args:
            img: PIL Image

        Returns:
            预处理后的numpy array (H, W, 3) RGB格式
        """
        # Depth-Anything V2需要518x518输入（标准尺寸）
        # 但Core ML模型可以接受任意尺寸
        # 我们保持原始尺寸以避免失真

        # 转换为numpy array (H, W, 3)
        img_array = np.array(img).astype(np.float32)

        # 归一化到0-1 (Core ML ImageType期望的格式)
        img_array = img_array / 255.0

        return img_array

    def _postprocess(
        self, depth: np.ndarray, target_size: Tuple[int, int]
    ) -> np.ndarray:
        """
        后处理深度图

        Args:
            depth: 原始深度输出
            target_size: 目标尺寸 (W, H)

        Returns:
            处理后的深度图 (0-255)
        """
        # 归一化到0-255
        depth_min = depth.min()
        depth_max = depth.max()

        if depth_max > depth_min:
            depth_normalized = (depth - depth_min) / (depth_max - depth_min) * 255
        else:
            depth_normalized = np.zeros_like(depth)

        depth_uint8 = depth_normalized.astype(np.uint8)

        # Resize到原始图片尺寸
        depth_img = Image.fromarray(depth_uint8)
        depth_img_resized = depth_img.resize(target_size, Image.Resampling.LANCZOS)

        return np.array(depth_img_resized)

    def _create_mock_depth(self, img: Image.Image) -> np.ndarray:
        """
        创建模拟深度图（用于测试）

        实际使用时会被Core ML推理代替
        """
        w, h = img.size
        # 创建一个简单的径向渐变作为模拟深度
        y, x = np.ogrid[:h, :w]
        cx, cy = w // 2, h // 2
        distance = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        max_distance = np.sqrt(cx**2 + cy**2)
        depth = (1 - distance / max_distance) * 255
        return depth

    def _load_from_cache(self, image_path: str, cache_dir: str) -> Optional[np.ndarray]:
        """从缓存加载深度图"""
        cache_file = self._get_cache_path(image_path, cache_dir)
        if os.path.exists(cache_file):
            try:
                return np.load(cache_file)
            except Exception:
                return None
        return None

    def _save_to_cache(self, depth_map: np.ndarray, image_path: str, cache_dir: str):
        """保存深度图到缓存"""
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = self._get_cache_path(image_path, cache_dir)
        np.save(cache_file, depth_map)

    def _get_cache_path(self, image_path: str, cache_dir: str) -> str:
        """生成缓存文件路径"""
        import hashlib

        image_hash = hashlib.md5(image_path.encode()).hexdigest()
        return os.path.join(cache_dir, f"depth_{image_hash}.npy")

    def _validate_input(self, image_path: str) -> bool:
        """验证输入参数"""
        if not image_path:
            logger.error("❌ 图片路径为空")
            return False

        if not os.path.exists(image_path):
            logger.error(f"❌ 图片文件不存在: {image_path}")
            return False

        # 检查文件是否可读
        if not os.access(image_path, os.R_OK):
            logger.error(f"❌ 无法读取图片文件: {image_path}")
            return False

        # 检查文件扩展名
        valid_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
        ext = os.path.splitext(image_path)[1].lower()
        if ext not in valid_extensions:
            logger.warning(f"⚠️ 不常见的图片格式: {ext}, 尝试继续处理")

        return True

    def _validate_image_size(self, size: Tuple[int, int]) -> bool:
        """验证图片尺寸是否合理"""
        w, h = size

        # 检查最小尺寸
        min_size = 64
        if w < min_size or h < min_size:
            logger.error(f"❌ 图片尺寸过小: {w}x{h}, 最小要求: {min_size}x{min_size}")
            return False

        # 检查最大尺寸（避免内存溢出）
        max_size = 8192
        if w > max_size or h > max_size:
            logger.warning(f"⚠️ 图片尺寸较大: {w}x{h}, 可能影响性能")
            # 不阻止处理，只是警告

        # 检查总像素数
        max_pixels = 50_000_000  # 50MP
        if w * h > max_pixels:
            logger.error(f"❌ 图片像素过多: {w * h:,}, 最大支持: {max_pixels:,}")
            return False

        return True
