"""
缓动效果对比测试
====================
生成两个视频对比缓动函数的效果：
1. 无缓动（线性运动） - easing_off_test.mp4
2. 有缓动（平滑运动） - easing_on_test.mp4

运行命令：
python tests/compare_easing_effect.py
"""

import os
import sys
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import C
from model.models import Scene
from steps.video.factory import VideoAssemblerFactory
from steps.audio.generic import GenericAudioStudio
from util.logger import logger


def get_test_dir():
    return os.path.dirname(os.path.abspath(__file__))


def setup_test_output():
    output_dir = os.path.join(get_test_dir(), "output", "easing_comparison")
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


async def generate_test_video(enable_easing, output_name):
    """生成测试视频"""
    print(f"\n{'='*60}")
    print(f"🎬 生成测试视频: {output_name}")
    print(f"   缓动函数: {'✅ 启用' if enable_easing else '❌ 禁用'}")
    print(f"{'='*60}\n")
    
    test_dir = get_test_dir()
    output_dir = setup_test_output()
    
    # 设置配置
    C.OUTPUT_DIR = output_dir
    C.CURRENT_CATEGORY = "成语故事"
    C.CAMERA_ENABLE_EASING = enable_easing
    C.CAMERA_MOVEMENT_INTENSITY = 1.25  # 使用更明显的运动幅度
    C.ENABLE_CUSTOM_INTRO = False  # 关闭片头，聚焦场景效果
    C.ENABLE_BRAND_OUTRO = False   # 关闭片尾
    
    # 测试图片
    scene_img = os.path.join(test_dir, "scene.png")
    if not os.path.exists(scene_img):
        print(f"❌ 测试图片不存在: {scene_img}")
        return None
    
    # 创建场景 - 使用不同的camera action展示效果
    audio_studio = GenericAudioStudio()
    scenes = []
    
    test_scenarios = [
        ("zoom_in", "这是一个放大镜头的测试场景"),
        ("zoom_out", "这是一个缩小镜头的测试场景"),
        ("pan_right", "这是一个右移镜头的测试场景"),
    ]
    
    for i, (action, text) in enumerate(test_scenarios):
        scene = Scene(
            scene_id=i + 1,
            narration=text,
            image_prompt=f"Test scene {i + 1}",
            image_path=scene_img,
            audio_path="",
            camera_action=action,
        )
        scenes.append(scene)
    
    print(f"📍 创建了 {len(scenes)} 个测试场景")
    
    # 生成音频
    print("🎤 生成音频...")
    await audio_studio.generate_audio(scenes, force=True)
    
    # 组装视频
    print("🎬 组装视频...")
    category = "成语故事"
    assembler = VideoAssemblerFactory.get_assembler(category)
    
    try:
        output_path = assembler.assemble_video(
            scenes,
            output_filename=output_name,
            topic="缓动效果测试",
            subtitle="",
            category=category,
        )
        
        if output_path and os.path.exists(output_path):
            print(f"\n✅ 视频生成成功: {output_path}\n")
            return output_path
        else:
            print(f"\n❌ 视频生成失败\n")
            return None
            
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    print("\n" + "="*60)
    print("🎯 缓动效果对比测试")
    print("="*60)
    
    # 生成两个视频
    video1 = await generate_test_video(enable_easing=False, output_name="easing_off_test.mp4")
    video2 = await generate_test_video(enable_easing=True, output_name="easing_on_test.mp4")
    
    # 总结
    print("\n" + "="*60)
    print("📊 测试完成")
    print("="*60)
    
    if video1:
        print(f"❌ 无缓动: {video1}")
    if video2:
        print(f"✅ 有缓动: {video2}")
    
    print("\n💡 对比观看建议：")
    print("   1. 注意镜头运动的开始和结束是否平滑")
    print("   2. 无缓动版本运动速度恒定（机械感）")
    print("   3. 有缓动版本开始慢→中间快→结束慢（自然感）")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
