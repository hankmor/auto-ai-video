"""
图层分离模块
===========
基于深度图将图片分离为多个图层，用于视差效果

算法：
- 根据深度值将图片分成N层（默认3层：前景、中景、背景）
- 每层包含：图片数据、mask、深度范围
- 边缘羽化和inpainting填补空缺区域
"""

import os
import numpy as np
from PIL import Image
from typing import List, Dict
from util.logger import logger


class LayerSeparator:
    """
    图层分离器

    将图片根据深度图分离为多个图层
    """

    def __init__(self, num_layers: int = 3):
        """
        初始化图层分离器

        Args:
            num_layers: 分层数量（默认3层）
        """
        self.num_layers = num_layers

    def separate(self, image_path: str, depth_map: np.ndarray) -> List[Dict]:
        """
        分离图层

        Args:
            image_path: 原始图片路径
            depth_map: 深度图 (H, W) 0-255

        Returns:
            图层列表，每层包含:
            {
                'image': PIL.Image,      # 图层图片
                'mask': np.ndarray,       # 图层mask (H, W) bool
                'depth_range': (min, max),  # 深度范围
                'layer_index': int        # 图层索引 (0=前景)
            }
        """
        # 输入验证
        if not self._validate_inputs(image_path, depth_map):
            return []

        try:
            # 1. 加载原始图片
            img = Image.open(image_path).convert("RGBA")
            img_array = np.array(img)

            # 验证图片和深度图尺寸匹配
            if img_array.shape[:2] != depth_map.shape:
                logger.error(
                    f"❌ 图片尺寸 {img_array.shape[:2]} 与深度图尺寸 {depth_map.shape} 不匹配"
                )
                return []

            # 2. 计算深度分层阈值
            thresholds = self._calculate_thresholds(depth_map)
            logger.info(f"🔪 分层阈值: {thresholds}")

            # 3. 为每层创建mask和图层
            layers = []
            for i in range(self.num_layers):
                layer_info = self._create_layer(img_array, depth_map, thresholds, i)

                # 检查图层质量
                if not self._validate_layer(layer_info, i):
                    logger.warning(f"⚠️ 图层{i}质量检查失败，但继续处理")

                layers.append(layer_info)
                logger.info(
                    f"✅ 图层{i}: 深度{layer_info['depth_range']}, "
                    f"像素{layer_info['mask'].sum():,}"
                )

            # 释放资源
            img.close()

            return layers

        except Exception as e:
            logger.error(f"❌ 图层分离失败: {e}")
            import traceback

            logger.debug(traceback.format_exc())
            return []

    def _calculate_thresholds(self, depth_map: np.ndarray) -> List[int]:
        """
                计算分层阈值

        使用均匀分割策略

                Args:
                    depth_map: 深度图

                Returns:
                    阈值列表 [t1, t2, ...] 长度为num_layers-1
        """
        # 简单均匀分割（使用float避免overflow）
        min_depth = float(depth_map.min())
        max_depth = float(depth_map.max())

        # 处理极端情况：深度值都相同
        if min_depth == max_depth:
            logger.warning("⚠️ 深度图值完全一致，将使用默认分割")
            # 使用默认分割 (假设0-255范围)
            min_depth, max_depth = 0.0, 255.0

        thresholds = []
        for i in range(1, self.num_layers):
            # 计算分割点
            ratio = i / self.num_layers
            threshold = min_depth + (max_depth - min_depth) * ratio
            thresholds.append(int(threshold))

        return thresholds

    def _create_layer(
        self,
        img_array: np.ndarray,
        depth_map: np.ndarray,
        thresholds: List[int],
        layer_index: int,
    ) -> Dict:
        """
        创建单个图层

        Args:
            img_array: 原始图片数组 (H, W, 4) RGBA
            depth_map: 深度图 (H, W)
            thresholds: 阈值列表
            layer_index: 图层索引 (0=前景, 最近)

        Returns:
            图层信息字典
        """
        # 1. 根据索引确定深度范围
        if layer_index == 0:
            # 前景：0 到第一个阈值
            depth_min = 0
            depth_max = thresholds[0]
        elif layer_index == self.num_layers - 1:
            # 背景：最后一个阈值到255
            depth_min = thresholds[-1]
            depth_max = 255
        else:
            # 中间层
            depth_min = thresholds[layer_index - 1]
            depth_max = thresholds[layer_index]

        # 2. 创建原始mask
        if layer_index == self.num_layers - 1:
            # 背景层包含最大值
            mask = (depth_map >= depth_min) & (depth_map <= depth_max)
        else:
            mask = (depth_map >= depth_min) & (depth_map < depth_max)

        # 3. 边缘羽化处理
        mask_smoothed = self._smooth_mask_edges(mask)

        # 4. 提取图层图片（保留alpha通道）
        layer_img_array = img_array.copy()

        # 使用平滑的mask来设置alpha通道
        # mask_smoothed的值在0-1之间，需要转换为0-255
        alpha_values = (mask_smoothed * 255).astype(np.uint8)
        layer_img_array[:, :, 3] = np.minimum(layer_img_array[:, :, 3], alpha_values)

        layer_img = Image.fromarray(layer_img_array, mode="RGBA")

        # 5. Inpainting填补透明区域（可选）
        # 注意：这里使用原始mask，不是smoothed的
        if self._should_inpaint(mask):
            layer_img = self._inpaint_layer(layer_img, mask)

        return {
            "image": layer_img,
            "mask": mask,  # 返回原始mask用于统计
            "depth_range": (depth_min, depth_max),
            "layer_index": layer_index,
        }

    def _inpaint_layer(self, layer_img: Image.Image, mask: np.ndarray) -> Image.Image:
        """
        超强inpainting填补图层空缺

        使用多轮膨胀和模糊填充大面积空缺区域

        Args:
            layer_img: 图层图片
            mask: 有效区域mask

        Returns:
            填补后的图层
        """
        try:
            from scipy import ndimage

            img_array = np.array(layer_img)

            # 对RGB通道进行多轮扩展填充
            for channel in range(3):
                channel_data = img_array[:, :, channel].copy()

                # 第一轮：大范围膨胀（50次迭代，填充大面积）
                dilated_mask_1 = ndimage.binary_dilation(mask, iterations=50)
                blurred_1 = ndimage.gaussian_filter(
                    channel_data.astype(float), sigma=6.0
                )
                fill_region_1 = dilated_mask_1 & ~mask
                channel_data[fill_region_1] = blurred_1[fill_region_1]

                # 第二轮：继续扩展（再50次，确保覆盖所有边缘）
                current_mask = dilated_mask_1
                dilated_mask_2 = ndimage.binary_dilation(current_mask, iterations=50)
                blurred_2 = ndimage.gaussian_filter(
                    channel_data.astype(float), sigma=8.0
                )
                fill_region_2 = dilated_mask_2 & ~current_mask
                channel_data[fill_region_2] = blurred_2[fill_region_2]

                img_array[:, :, channel] = channel_data

            return Image.fromarray(img_array, mode="RGBA")
        except ImportError:
            logger.warning("⚠️ scipy未安装，跳过inpainting")
            return layer_img

    def _smooth_mask_edges(self, mask: np.ndarray, sigma: float = 2.5) -> np.ndarray:
        """
        平滑mask边缘，实现抗锯齿效果

        Args:
            mask: 布尔mask数组
            sigma: 高斯模糊的sigma值（默认2.5，更柔和的过渡）

        Returns:
            平滑后的mask (float数组，值在0-1之间)
        """
        try:
            from scipy import ndimage

            # 转换为float
            mask_float = mask.astype(np.float32)

            # 高斯模糊 - 增加sigma让边缘更柔和
            smoothed = ndimage.gaussian_filter(mask_float, sigma=sigma)

            # 确保值在0-1范围内
            smoothed = np.clip(smoothed, 0.0, 1.0)

            return smoothed
        except ImportError:
            logger.warning("⚠️ scipy未安装，跳过边缘平滑")
            return mask.astype(np.float32)

    def _should_inpaint(self, mask: np.ndarray) -> bool:
        """
        判断是否需要进行inpainting

        为了避免黑边，对所有图层都进行inpainting
        """
        # 计算有效像素比例
        valid_ratio = mask.sum() / mask.size

        # 只有在几乎完全空的情况下才跳过
        if valid_ratio < 0.001:
            return False

        # 其他情况都进行inpainting以避免黑边
        return True

    def _validate_inputs(self, image_path: str, depth_map: np.ndarray) -> bool:
        """
        验证输入参数
        """
        if not image_path or not os.path.exists(image_path):
            logger.error(f"❌ 图片文件不存在: {image_path}")
            return False

        if depth_map is None or depth_map.size == 0:
            logger.error("❌ 深度图为空")
            return False

        if depth_map.ndim != 2:
            logger.error(f"❌ 深度图维度错误: {depth_map.ndim}, 期望2")
            return False

        return True

    def _validate_layer(self, layer_info: Dict, layer_index: int) -> bool:
        """
        验证图层质量
        """
        mask = layer_info["mask"]
        pixel_count = mask.sum()
        total_pixels = mask.size

        # 检查是否是空图层
        if pixel_count == 0:
            logger.warning(f"⚠️ 图层{layer_index}为空（无有效像素）")
            return False

        # 检查像素数量是否过少
        min_pixel_ratio = 0.005  # 至少0.5%的像素
        if pixel_count < total_pixels * min_pixel_ratio:
            logger.warning(
                f"⚠️ 图层{layer_index}像素过少: {pixel_count} ({pixel_count / total_pixels * 100:.2f}%)"
            )
            return False

        return True
