import asyncio
import os
import argparse
import time
from auto_maker.config import config
from auto_maker.script_generator import ScriptGenerator
from auto_maker.image_factory import ImageFactory
from auto_maker.audio_studio import AudioStudio
from auto_maker.video_editor import VideoAssembler
from auto_maker.models import Scene, VideoScript

async def run_test(topic: str, script_path: str = None, category: str = "storybox"):
    print(f"🧪 Starting Integration Test")
    print(f"   LLM: {config.LLM_PROVIDER} / {config.LLM_MODEL}")
    print(f"   Image: {config.IMAGE_PROVIDER} / {config.IMAGE_MODEL}")
    print(f"   Category: {category}")
    
    # Enable Subtitles for this test
    config.ENABLE_SUBTITLES = True
    
    script = None
    
    # 1. Get Script (Load or Generate)
    if script_path and os.path.exists(script_path):
        print(f"\n📂 Loading existing script from: {script_path}")
        try:
            script = VideoScript.from_json(script_path)
            print(f"✅ Script Loaded!")
            print(f"   Title: {script.topic}")
        except Exception as e:
            print(f"❌ Failed to load script: {e}")
            return
    elif topic:
        print(f"\n📝 Generating Script (Design + Scenes) for topic: '{topic}'...")
        try:
            generator = ScriptGenerator()
            script = generator.generate_script(topic)
            print(f"✅ Script Generated!")
            print(f"   Title: {script.topic}")
            print(f"   Style: {script.visual_style}")
            print(f"   Scenes: {len(script.scenes)} generated.")
        except Exception as e:
            print(f"❌ Script Generation Failed: {e}")
            return
    else:
        print("❌ Error: You must provide either a 'topic' or a '--script' path.")
        return

    # 2. Pick First Scene for Full Test
    first_scene = script.scenes[0]
    print(f"\n🎬 Processing Scene 1 for End-to-End Test...")
    print(f"   Narration: {first_scene.narration}")
    print(f"   Prompt (Truncated): {first_scene.image_prompt[:50]}...")
    
    # Ensure output dir exists
    # Ensure output dir exists (tests/output)
    # Use path relative to this script: tests/output
    base_output = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    test_out_dir = os.path.join(base_output, str(int(time.time())))
    os.makedirs(test_out_dir, exist_ok=True)
    
    # Override global config for this run
    original_out = config.OUTPUT_DIR
    config.OUTPUT_DIR = test_out_dir
    
    try:
        # A. Image Generation
        print(f"\n🎨 [1/4] Generating Image...")
        image_factory = ImageFactory()
        img_path = await image_factory._generate_one_image(first_scene)
        print(f"   ✅ Image: {img_path}")
        
        # B. Audio Generation
        print(f"\n🔊 [2/4] Generating Audio (TTS)...")
        audio_studio = AudioStudio()
        await audio_studio._generate_one_audio(first_scene)
        print(f"   ✅ Audio: {first_scene.audio_path}")
        
        # C. Cover Generation
        print(f"\n🖼️ [3/4] Generating Cover...")
        video_assembler = VideoAssembler()
        cover_path = os.path.join(test_out_dir, "cover.png")
        if video_assembler.generate_cover(img_path, script.topic, cover_path):
            print(f"   ✅ Cover: {cover_path}")
        else:
            print(f"   ❌ Cover Generation Failed")

        # D. Video Assembly (Subtitles check)
        print(f"\n🎞️ [4/4] Assembling Mini-Video (checking LAYOUT)...")
        # Initialize video assembler
        # Pass category to test Book Mode layout if configured in config.yaml
        print(f"   ℹ️ Testing Category: {category}")
        
        final_video_path = video_assembler.assemble_video([first_scene], output_filename="test_video.mp4", topic=script.topic, category=category)
        
        # Save the script used
        if not script_path:
            save_path = os.path.join(test_out_dir, "script_test.json")
            script.to_json(save_path)
        else:
            save_path = os.path.join(test_out_dir, "script_source.json")
            script.to_json(save_path)
            
        print(f"\n✨ End-to-End Test Complete!")
        print(f"   📂 Output Directory: {test_out_dir}")
        print(f"   📄 Script: {save_path}")
        print(f"   🎥 Final Video: {final_video_path}")
        
    except Exception as e:
        print(f"❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        config.OUTPUT_DIR = original_out

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Integration Test for AutoMaker")
    parser.add_argument("topic", type=str, nargs='?', help="Topic for the test (optional if --script is used)")
    parser.add_argument("--script", type=str, help="Path to existing script.json to use")
    parser.add_argument("--category", type=str, default="成语故事", help="Category to simulate (determines layout movie/book)")
    args = parser.parse_args()
    
    asyncio.run(run_test(args.topic, args.script, args.category))
