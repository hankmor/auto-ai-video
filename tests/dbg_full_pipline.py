"""
Debug Video Pipeline Test
==========================
测试完整的视频制作流程：片头 -> 封面 -> 场景 -> 片尾

使用提供的测试图片:
- tests/cover.png: 封面图片
- tests/scene.png: 场景图片

测试目标:
1. 验证图片 Aspect Fill 缩放是否正确 (2048x3840 -> 1080x1920)
2. 验证片头视频拼接
3. 验证封面生成
4. 验证场景合成（双语模式）
5. 验证片尾生成
"""

import os
import sys
import asyncio

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import C
from model.models import Scene
from steps.video.factory import VideoAssemblerFactory
from steps.audio.generic import GenericAudioStudio
from util.logger import logger


def get_test_dir():
    """获取测试目录的绝对路径"""
    return os.path.dirname(os.path.abspath(__file__))


def get_project_root():
    """获取项目根目录"""
    return os.path.dirname(get_test_dir())


def setup_test_output():
    """设置测试输出目录"""
    output_dir = os.path.join(get_test_dir(), "output", "debug_full_pipeline")
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def find_intro_video():
    """查找可用的片头视频"""
    project_root = get_project_root()
    videos_dir = os.path.join(project_root, "assets", "videos")
    
    if os.path.exists(videos_dir):
        mp4s = [f for f in os.listdir(videos_dir) if f.endswith(".mp4")]
        if mp4s:
            return os.path.join(videos_dir, mp4s[0])
    
    return None


async def main():
    print("=" * 60)
    print("🎬 完整视频流水线测试")
    print("=" * 60)
    
    # ==================== 配置 ====================
    test_dir = get_test_dir()
    output_dir = setup_test_output()
    
    # 设置输出目录
    C.OUTPUT_DIR = output_dir
    
    # 设置当前分类 (用于获取语音配置)
    C.CURRENT_CATEGORY = "英语绘本"
    
    # 打印关键配置
    print(f"\n📁 测试目录: {test_dir}")
    print(f"📁 输出目录: {output_dir}")
    print(f"📐 视频目标尺寸: {getattr(C, 'VIDEO_SIZE', 'NOT SET')}")
    
    # ==================== 测试图片 ====================
    cover_img = os.path.join(test_dir, "cover.png")
    scene_img = os.path.join(test_dir, "scene.png")
    
    if not os.path.exists(cover_img):
        print(f"❌ 封面图片不存在: {cover_img}")
        return
    
    if not os.path.exists(scene_img):
        print(f"❌ 场景图片不存在: {scene_img}")
        return
    
    print(f"\n✅ 封面图片: {cover_img}")
    print(f"✅ 场景图片: {scene_img}")
    
    # ==================== 片头配置 ====================
    intro_path = find_intro_video()
    if intro_path:
        print(f"✅ 片头视频: {intro_path}")
        C.ENABLE_CUSTOM_INTRO = True
        C.CUSTOM_INTRO_VIDEO_PATH = intro_path
        C.ENABLE_CUSTOM_INTRO_DUB = True
        C.CUSTOM_INTRO_TRANSITION = "crossfade"
        C.CUSTOM_INTRO_TRANSITION_DURATION = 0.8
    else:
        print("⚠️ 未找到片头视频，跳过片头测试")
        C.ENABLE_CUSTOM_INTRO = False
    
    # 片尾
    C.ENABLE_BRAND_OUTRO = True
    
    # 双语模式 (测试)
    C.ENABLE_BILINGUAL_MODE = True
    C.BILINGUAL_CN_VOICE = "zh-CN-YunxiaNeural"
    
    # ==================== 创建场景 ====================
    print("\n🎬 创建测试场景...")
    
    # 使用项目的 AudioStudio
    audio_studio = GenericAudioStudio()
    
    scenes = []
    camera_actions = ["zoom_in", "pan_left", "zoom_out"]

    # 🔥 只测试1个场景以加快速度
    narrations = [
        ("I have a toy car! It's red and shiny.", "我有一辆玩具汽车！它又红又亮。"),
    ]
    
    for i, (narration_en, narration_cn) in enumerate(narrations):
        scene = Scene(
            scene_id=i + 1,
            narration=narration_en,
            narration_cn=narration_cn,  # 中文字幕/朗读
            image_prompt=f"Scene {i + 1}",
            image_path=scene_img,
            audio_path="",  # 稍后由 AudioStudio 生成
            camera_action=camera_actions[i % len(camera_actions)],
        )
        scenes.append(scene)
        print(f"   📍 场景 {i + 1}: {narration_en[:30]}... ({scene.camera_action})")

    # ==================== 生成双语音频 ====================
    print("\n🎤 生成双语音频（英文 + 中文）...")
    await audio_studio.generate_audio(scenes, force=True)

    # 验证音频生成
    for scene in scenes:
        if not scene.audio_path or not os.path.exists(scene.audio_path):
            print(f"   ❌ 场景 {scene.scene_id} 音频生成失败")
            return
        print(f"   ✅ 场景 {scene.scene_id} 音频: {scene.audio_path}")

    # ==================== 组装视频 ====================
    print("\n🎬 开始组装视频...")
    print(f"   片头: {'✅ 启用' if C.ENABLE_CUSTOM_INTRO else '❌ 禁用'}")
    print(f"   片尾: {'✅ 启用' if C.ENABLE_BRAND_OUTRO else '❌ 禁用'}")
    print(f"   双语: {'✅ 启用' if C.ENABLE_BILINGUAL_MODE else '❌ 禁用'}")

    # 🔥 修复：使用实际的category，让Factory返回正确的assembler
    # "英语绘本" 映射到 "book" layout，会返回 BookVideoAssembler
    category = "英语绘本"
    assembler = VideoAssemblerFactory.get_assembler(category)
    print(f"   使用组装器: {assembler.__class__.__name__}")
    
    try:
        output_path = assembler.assemble_video(
            scenes,
            output_filename="full_pipeline_test.mp4",
            topic="I have a toy car",
            subtitle="我有一辆玩具汽车",
            category=category,
            intro_hook="小朋友们大家好，今天我们来学习一个有趣的故事！",
        )
        
        if output_path and os.path.exists(output_path):
            print("\n" + "=" * 60)
            print(f"✅ 视频生成成功！")
            print(f"📍 输出路径: {output_path}")
            print("=" * 60)
            
            # 打开视频
            # print("\n🎬 正在打开视频...")
            # os.system(f'open "{output_path}"')
        else:
            print("\n❌ 视频生成失败")
            
    except Exception as e:
        print(f"\n❌ 视频组装出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
