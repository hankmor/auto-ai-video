"""
视差动画测试
============
测试完整的2.5D视差流程
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from steps.effects.depth_estimator import DepthEstimator
from steps.effects.parallax_animator import ParallaxAnimator


def test_parallax_animation():
    """测试完整视差动画"""
    print("="*60)
    print("🎬 视差动画完整测试")
    print("="*60)
    
    # 准备测试图片
    test_dir = os.path.dirname(os.path.abspath(__file__))
    # test_image = os.path.join(test_dir, "popmart_test.png")
    # test_image = os.path.join(test_dir, "scene_popmart.png")
    test_image = os.path.join(test_dir, "scene.png")
    
    if not os.path.exists(test_image):
        print(f"❌ 测试图片未找到: {test_image}")
        # 尝试使用上一级目录的fallback
        fallback = os.path.join(
            os.path.dirname(test_dir), "assets", "image", "test_input.jpg"
        )
        if os.path.exists(fallback):
            print(f"⚠️ 使用fallback图片: {fallback}")
            test_image = fallback
        else:
            return
    
    # 1. 深度估计
    print(f"\n1️⃣ 深度估计... ({os.path.basename(test_image)})")
    estimator = DepthEstimator()
    depth_map = estimator.estimate(test_image)
    
    if depth_map is None:
        print("❌ 深度估计失败")
        return
    
    print(f"✅ 深度图: shape={depth_map.shape}")

    # 2. 视差动画 (直接使用深度图，无需分层)
    print("\n2️⃣ 创建视差动画 (Depth Displacement)...")
    animator = ParallaxAnimator(movement_scale=0.05)  # 3%位移

    # 测试pan_right动作
    parallax_clip = animator.create_parallax_clip(
        image_path=test_image,
        depth_map=depth_map,
        duration=3.0,
        action="pan_right",
        fps=24,
    )
    
    if parallax_clip is None:
        print("❌ 视差动画创建失败")
        return
    
    print(f"✅ 视差动画创建成功")
    print(f"   时长: {parallax_clip.duration}s")
    print(f"   尺寸: {parallax_clip.size}")
    print(f"   FPS: {parallax_clip.fps}")
    
    # 4. 导出视频
    print("\n4️⃣ 导出视频...")
    output_dir = os.path.join(test_dir, "output", "parallax_test")
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, "parallax_demo.mp4")
    
    print(f"   导出中... (这可能需要一些时间)")
    parallax_clip.write_videofile(
        output_path,
        codec='libx264',
        fps=24,
        audio=False,
        preset='medium',
        verbose=False,
        logger=None
    )
    
    print(f"✅ 视频已保存: {output_path}")
    
    print("\n" + "="*60)
    print("✅ 完整测试通过！")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_parallax_animation()
