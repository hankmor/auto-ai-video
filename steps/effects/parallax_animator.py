"""
视差动画模块
===========
根据图层深度创建2.5D视差动画效果

核心思想：
- 前景移动快（距离相机近）
- 中景移动中等
- 背景移动慢（距离相机远）
"""

import numpy as np
from PIL import Image
from moviepy.editor import ImageClip, CompositeVideoClip
from typing import List, Dict, Tuple
from util.logger import logger


class ParallaxAnimator:
    """
    视差动画器
    
    将多层图片合成为具有视差效果的视频
    """
    
    def __init__(self, movement_scale: float = 1.2):
        """
        初始化视差动画器
        
        Args:
            movement_scale: 视差运动倍率（默认1.2）
        """
        self.movement_scale = movement_scale
    
    def create_parallax_clip(
        self,
        layers: List[Dict],
        duration: float,
        action: str = "pan_right",
        fps: int = 24
    ) -> CompositeVideoClip:
        """
        创建视差动画视频
        
        Args:
            layers: 图层列表（从_separator返回）
            duration: 视频时长（秒）
            action: 运动类型（pan_left/right/up/down, zoom_in/out）
            fps: 帧率
        
        Returns:
            合成后的视频clip
        """
        if not layers:
            logger.error("❌ 图层列表为空")
            return None
        
        try:
            # 1. 为每层创建运动clip
            layer_clips = []
            for layer_info in layers:
                clip = self._create_layer_clip(
                    layer_info,
                    duration,
                    action,
                    fps
                )
                layer_clips.append(clip)
            
            # 2. 合成所有图层（从后往前：背景->中景->前景）
            composite = CompositeVideoClip(
                layer_clips[::-1],  # 反转顺序
                size=layers[0]['image'].size
            ).set_duration(duration).set_fps(fps)
            
            logger.info(f"✅ 视差动画创建成功: {len(layer_clips)}层, {duration}s")
            return composite
            
        except Exception as e:
            logger.error(f"❌ 视差动画创建失败: {e}")
            return None
    
    def _create_layer_clip(
        self,
        layer_info: Dict,
        duration: float,
        action: str,
        fps: int
    ) -> ImageClip:
        """
        为单个图层创建运动clip
        
        Args:
            layer_info: 图层信息
            duration: 时长
            action: 运动类型
            fps: 帧率
        
        Returns:
            ImageClip with position animation
        """
        layer_img = layer_info['image']
        layer_idx = layer_info['layer_index']
        
        # 计算该层的运动速度（前景快，背景慢）
        speed_factor = self._calculate_speed_factor(layer_idx, len(layer_info))
        
        # 创建基础clip
        clip = ImageClip(np.array(layer_img)).set_duration(duration)
        
        # 应用运动
        if action.startswith("pan_"):
            clip = self._apply_pan_motion(clip, action, speed_factor, duration)
        elif action.startswith("zoom_"):
            clip = self._apply_zoom_motion(clip, action, speed_factor, duration)
        
        return clip
    
    def _calculate_speed_factor(self, layer_idx: int, total_layers: int) -> float:
        """
        计算图层运动速度因子
        
        layer_idx = 0 (前景) -> 速度最快
        layer_idx = n-1 (背景) -> 速度最慢
        
        Args:
            layer_idx: 图层索引
            total_layers: 总层数
        
        Returns:
            速度因子 (0.5-1.5)
        """
        if total_layers == 1:
            return 1.0
        
        # 线性插值：前景1.5倍速，背景0.5倍速
        speed = 1.5 - (layer_idx / (total_layers - 1)) * 1.0
        return speed * self.movement_scale
    
    def _apply_pan_motion(
        self,
        clip: ImageClip,
        direction: str,
        speed_factor: float,
        duration: float
    ) -> ImageClip:
        """
        应用平移运动
        
        Args:
            clip: 图层clip
            direction: pan_left/right/up/down
            speed_factor: 速度因子
            duration: 时长
        
        Returns:
            带运动的clip
        """
        w, h = clip.size
        
        # 基础移动距离（10%画面宽度/高度）
        base_distance = min(w, h) * 0.1 * speed_factor
        
        def position_func(t):
            """计算位置随时间变化"""
            progress = t / duration
            
            if direction == "pan_left":
                # 向左移动
                return (int(-base_distance * progress), 'center')
            elif direction == "pan_right":
                # 向右移动
                return (int(base_distance * progress), 'center')
            elif direction == "pan_up":
                # 向上移动
                return ('center', int(-base_distance * progress))
            elif direction == "pan_down":
                # 向下移动
                return ('center', int(base_distance * progress))
            else:
                return ('center', 'center')
        
        return clip.set_position(position_func)
    
    def _apply_zoom_motion(
        self,
        clip: ImageClip,
        direction: str,
        speed_factor: float,
        duration: float
    ) -> ImageClip:
        """
        应用缩放运动
        
        Args:
            clip: 图层clip
            direction: zoom_in/out
            speed_factor: 速度因子
            duration: 时长
        
        Returns:
            带缩放的clip
        """
        def resize_func(t):
            """计算缩放比例随时间变化"""
            progress = t / duration
            
            if direction == "zoom_in":
                # 放大：1.0 -> 1.2
                scale = 1.0 + 0.2 * speed_factor * progress
            else:  # zoom_out
                # 缩小：1.2 -> 1.0
                scale = 1.2 - 0.2 * speed_factor * progress
            
            return scale
        
        return clip.resize(resize_func)
