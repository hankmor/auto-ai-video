import numpy as np
from PIL import Image
from moviepy.editor import ImageClip
from typing import Optional, Tuple
from util.logger import logger


class ParallaxAnimator:
    """
    深度位移视差动画器 (Depth Displacement Animator)

    不使用图层分离，而是直接根据深度图对像素进行位移。
    优势：
    1. 无黑边：通过边缘像素拉伸解决
    2. 无割裂：深度连续变化，物体不会被切断
    3. 更自然：类似3D投影效果
    """

    def __init__(self, movement_scale: float = 0.05):
        """
        初始化视差动画器

        Args:
            movement_scale: 运动幅度系数 (默认0.05, 即5%画面宽度)
            推荐范围: 0.03 - 0.08
        """
        if movement_scale > 0.1:
            logger.warning(
                f"⚠️ movement_scale {movement_scale} 较大 (>0.1)，可能会导致边缘拉伸变形(Artifacts)"
            )

        self.movement_scale = movement_scale

    def create_parallax_clip(
        self,
        image_path: str,
        depth_map: np.ndarray,
        duration: float,
        action: str = "pan_right",
        fps: int = 24,
        target_size: Optional[Tuple[int, int]] = None,
    ) -> Optional[ImageClip]:
        """
        创建视差动画视频

        Args:
            image_path: 原始图片路径
            depth_map: 深度图 (H, W) 0-255，0=远，255=近
            duration: 时长
            action: 运动类型
            fps: 帧率
            target_size: 目标视频尺寸 (Width, Height)，用于预先Resize优化性能

        Returns:
            ImageClip (包含每帧变换逻辑)
        """
        # 检查动作是否支持 (目前仅支持 Pan, Zoom 建议回退到 Ken Burns)
        if action not in ["pan_right", "pan_left", "pan_up", "pan_down"]:
            logger.info(f"ℹ️ Parallax暂不支持动作 '{action}'，回退到标准Ken Burns效果")
            return None

        try:
            # 1. 准备数据
            # 读取图片并转为numpy数组 (RGB)
            img = Image.open(image_path).convert("RGB")

            # 性能优化：如果指定了 target_size，先缩小图片和深度图
            # 大幅减少 map_coordinates 的计算量 (e.g. 4K -> 1080p)
            if target_size:
                w_target, h_target = target_size
                # 保持比例填充 Resize (Aspect Fill)
                # 计算缩放比例
                org_w, org_h = img.size
                scale = max(w_target / org_w, h_target / org_h)
                new_w = int(org_w * scale)
                new_h = int(org_h * scale)

                # Resize Image
                img = img.resize((new_w, new_h), Image.LANCZOS)

                # Resize Depth Map (First convert to PIL)
                depth_img = Image.fromarray(depth_map)
                depth_img = depth_img.resize((new_w, new_h), Image.BILINEAR)
                depth_map = np.array(depth_img)

                logger.info(
                    f"⚡ Parallax Optimized: Resized input from ({org_w}, {org_h}) to ({new_w}, {new_h})"
                )

            img_arr = np.array(img)

            # 确保深度图尺寸匹配 (此时应该已经匹配了，但为了健壮性保留检查)
            h, w = img_arr.shape[:2]
            if depth_map.shape != (h, w):
                logger.debug(f"调整深度图尺寸: {depth_map.shape} -> {(h, w)}")
                # 使用PIL调整大小
                depth_img = Image.fromarray(depth_map)
                depth_img = depth_img.resize((w, h), Image.BILINEAR)
                depth_map = np.array(depth_img)

            # 归一化深度图 (0.0 - 1.0)
            # 注意：DepthAnything输出通常是 relative depth
            # 我们假设 0=最远(背景), 1=最近(前景)
            norm_depth = depth_map.astype(np.float32) / 255.0

            # 2. 定义每一帧的变换函数
            def make_frame(t):
                # 计算当前时间进度 (0.0 -> 1.0)
                progress = t / duration

                # 使用缓动函数 (Ease In Out Cubic)
                # t: 0->1, eased: 0->1
                if progress < 0.5:
                    eased = 4 * progress * progress * progress
                else:
                    eased = 1 - pow(-2 * progress + 2, 3) / 2

                # 计算当前位移量 (像素)
                # max_shift = 画面宽度 * movement_scale
                max_shift_x = w * self.movement_scale
                max_shift_y = h * self.movement_scale

                offset_x = 0
                offset_y = 0

                # 根据动作计算位移方向
                # 视差原理：前景移动多，背景移动少 (或反之)
                # 这里我们模拟相机移动：
                # 相机向右移 -> 前景向左移(幅度大)，背景向左移(幅度小)
                # 为了简化，我们让 背景不动(或微动)，前景动

                if action == "pan_right":
                    # 此时相机左移，画面右移
                    # 或者：我们让前景往右移
                    offset_x = max_shift_x * eased
                elif action == "pan_left":
                    offset_x = -max_shift_x * eased
                elif action == "pan_up":
                    offset_y = -max_shift_y * eased
                elif action == "pan_down":
                    offset_y = max_shift_y * eased
                elif action == "zoom_in":
                    # 缩放比较特殊，需要对坐标进行中心缩放
                    pass

                # 3. 应用位移映射 (Displacement Mapping)
                return self._apply_displacement(img_arr, norm_depth, offset_x, offset_y)

            # 3. 创建VideoClip
            from moviepy.editor import VideoClip

            clip = VideoClip(make_frame, duration=duration)
            clip.fps = fps

            # 设置尺寸（重要）
            clip.size = (w, h)

            return clip

        except Exception as e:
            logger.error(f"❌ 创建视差动画失败: {str(e)}")
            import traceback

            traceback.print_exc()
            return None

    def _apply_displacement(
        self, img: np.ndarray, depth: np.ndarray, offset_x: float, offset_y: float
    ) -> np.ndarray:
        """
        应用深度位移 (使用SciPy实现)
        """
        try:
            from scipy.ndimage import map_coordinates

            h, w = img.shape[:2]

            # 创建网格坐标 (indexing='ij' for h, w)
            y, x = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")

            # Inverse mapping: Source = Dest - Displacement
            # 深度越大(越近)，位移越大
            src_x = x - offset_x * depth
            src_y = y - offset_y * depth

            # 对每个通道进行重采样
            output = np.zeros_like(img)

            # 坐标必须是 (row_coords, col_coords) 即 (y, x)
            coords = [src_y, src_x]

            for c in range(3):
                # mode='nearest' 实现边缘像素拉伸，解决黑边问题
                # order=1 (线性插值) 保证平滑
                output[:, :, c] = map_coordinates(
                    img[:, :, c], coords, mode="nearest", order=1
                )

            return output

        except ImportError:
            logger.error("❌ scipy未安装，无法执行位移映射")
            return img
