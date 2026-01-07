"""
图层分离测试
============
测试图层分离功能
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from steps.effects.depth_estimator import DepthEstimator
from steps.effects.layer_separator import LayerSeparator
from PIL import Image


def test_layer_separation():
    """测试图层分离"""
    print("="*60)
    print("🧪 图层分离模块测试")
    print("="*60)
    
    # 准备测试图片
    test_dir = os.path.dirname(os.path.abspath(__file__))
    test_image = os.path.join(test_dir, "scene.png")
    
    if not os.path.exists(test_image):
        print(f"❌ 测试图片未找到: {test_image}")
        return
    
    # 1. 生成深度图
    print("\n1️⃣ 估计深度...")
    estimator = DepthEstimator()
    depth_map = estimator.estimate(test_image)
    
    if depth_map is None:
        print("❌ 深度估计失败")
        return
    
    print(f"✅ 深度图生成: shape={depth_map.shape}")
    
    # 2. 分离图层
    print("\n2️⃣ 分离图层...")
    separator = LayerSeparator(num_layers=3)
    layers = separator.separate(test_image, depth_map)
    
    if not layers:
        print("❌ 图层分离失败")
        return
    
    print(f"✅ 分离完成: {len(layers)}个图层")
    
    # 3. 保存图层可视化
    print("\n3️⃣ 保存图层...")
    output_dir = os.path.join(test_dir, "output", "layer_separation")
    os.makedirs(output_dir, exist_ok=True)
    
    for layer_info in layers:
        idx = layer_info['layer_index']
        layer_img = layer_info['image']
        
        # 保存图层图片
        layer_path = os.path.join(output_dir, f"layer_{idx}.png")
        layer_img.save(layer_path)
        
        print(f"  图层{idx}: {layer_path}")
        print(f"    深度范围: {layer_info['depth_range']}")
        print(f"    有效像素: {layer_info['mask'].sum()}")
    
    print("\n" + "="*60)
    print("✅ 所有测试通过！")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_layer_separation()
