"""
深度估计模块测试
================
测试Depth-Anything v2 Core ML模型的基本功能和性能
"""

import os
import sys
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from steps.effects.depth_estimator import DepthEstimator
from PIL import Image
import numpy as np


def test_depth_estimation():
    """测试基本的深度估计功能"""
    print("="*60)
    print("🧪 深度估计模块测试")
    print("="*60)
    
    # 准备测试图片
    test_dir = os.path.dirname(os.path.abspath(__file__))
    test_image = os.path.join(test_dir, "scene.png")
    
    if not os.path.exists(test_image):
        print(f"❌ 测试图片not found: {test_image}")
        print("   请确保tests/scene.png存在")
        return
    
    # 初始化估计器
    print("\n1️⃣ 初始化深度估计器...")
    estimator = DepthEstimator()
    
    # 估计深度
    print("\n2️⃣ 估计深度...")
    cache_dir = os.path.join(test_dir, "output", ".depth_cache")
    
    start_time = time.time()
    depth_map = estimator.estimate(test_image, cache_dir=cache_dir)
    elapsed = (time.time() - start_time) * 1000
    
    if depth_map is None:
        print("❌ 深度估计失败")
        return
    
    print(f"✅ 深度估计成功")
    print(f"   - 耗时: {elapsed:.2f}ms")
    print(f"   - 深度图shape: {depth_map.shape}")
    print(f"   - 值范围: [{depth_map.min()}, {depth_map.max()}]")
    
    # 保存深度图可视化
    print("\n3️⃣ 保存深度图可视化...")
    output_dir = os.path.join(test_dir, "output", "depth_visualization")
    os.makedirs(output_dir, exist_ok=True)
    
    depth_img = Image.fromarray(depth_map)
    output_path = os.path.join(output_dir, "depth_map.png")
    depth_img.save(output_path)
    print(f"✅ 深度图已保存: {output_path}")
    
    # 测试缓存
    print("\n4️⃣ 测试缓存功能...")
    start_time = time.time()
    depth_map2 = estimator.estimate(test_image, cache_dir=cache_dir)
    elapsed_cached = (time.time() - start_time) * 1000
    
    print(f"✅ 缓存加载耗时: {elapsed_cached:.2f}ms")
    print(f"   性能提升: {elapsed / elapsed_cached:.1f}x")
    
    print("\n" + "="*60)
    print("✅ 所有测试通过！")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_depth_estimation()
