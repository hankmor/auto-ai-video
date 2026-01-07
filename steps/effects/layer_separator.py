"""
图层分离模块
===========
基于深度图将图片分离为多个图层，用于视差效果

算法：
- 根据深度值将图片分成N层（默认3层：前景、中景、背景）
- 每层包含：图片数据、mask、深度范围
- 简单inpainting填补空缺区域
"""

import os
import numpy as np
from PIL import Image, ImageFilter
from typing import List, Dict, Tuple
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
        try:
            # 1. 加载原始图片
            img = Image.open(image_path).convert("RGBA")
            img_array = np.array(img)

            # 2. 计算深度分层阈值
            thresholds = self._calculate_thresholds(depth_map)
            logger.info(f"🔪 分层阈值: {thresholds}")

            # 3. 为每层创建mask
            layers = []
            for i in range(self.num_layers):
                layer_info = self._create_layer(img_array, depth_map, thresholds, i)
                layers.append(layer_info)
                logger.info(
                    f"✅ 图层{i}: 深度{layer_info['depth_range']}, "
                    f"像素{layer_info['mask'].sum()}"
                )

            return layers

        except Exception as e:
            logger.error(f"❌ 图层分离失败: {e}")
            return []

    def _calculate_thresholds(self, depth_map: np.ndarray) -> List[int]:
        """
        计算分层阈值

        使用均匀分割或基于直方图的智能分割

        Args:
            depth_map: 深度图

        Returns:
            阈值列表 [t1, t2, ...] 长度为num_layers-1
        """
        # 简单均匀分割（使用float避免overflow）
        min_depth = float(depth_map.min())
        max_depth = float(depth_map.max())

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

        # 2. 创建mask
        mask = (depth_map >= depth_min) & (depth_map < depth_max)

        # 3. 提取图层图片（保留alpha通道）
        layer_img_array = img_array.copy()
        layer_img_array[~mask, 3] = 0  # 不在mask中的区域设为透明

        # 4. （可选）简单inpainting填补透明区域
        # 这里先跳过，后续优化时添加

        layer_img = Image.fromarray(layer_img_array, mode="RGBA")

        return {
            "image": layer_img,
            "mask": mask,
            "depth_range": (depth_min, depth_max),
            "layer_index": layer_index,
        }

    def _inpaint_layer(self, layer_img: Image.Image, mask: np.ndarray) -> Image.Image:
        """
        简单inpainting填补图层空缺

        使用周围像素的平均值填充

        Args:
            layer_img: 图层图片
            mask: 有效区域mask

        Returns:
            填补后的图层
        """
        # TODO: 实现简单的inpainting
        # 可以使用高斯模糊或邻近像素填充
        return layer_img
