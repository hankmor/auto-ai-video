import sys
import os
import asyncio

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import C
from steps.audio.factory import AudioStudioFactory
from util.logger import logger

async def main():
    print("="*50)
    print("🔊 TTS Debug Tool")
    print("="*50)
    
    # Reload config to ensure we get latest yaml changes? 
    # Config is loaded on import, so it should be fine if script is run fresh.
    
    provider = getattr(C, "TTS_PROVIDER", "unknown")
    print(f"Current Provider: [{provider}]")
    if provider == "volc":
        print(f"  AppID: {getattr(C, 'VOLC_TTS_APPID', '')}")
        print(f"  Token: {getattr(C, 'VOLC_TTS_TOKEN', '')[:5]}******")
        print(f"  Voice: {getattr(C, 'VOLC_TTS_VOICE_TYPE', '')}")
    elif provider == "azure":
        print(f"  Key: {getattr(C, 'AZURE_TTS_KEY', '')[:5]}******")
        print(f"  Region: {getattr(C, 'AZURE_TTS_REGION', '')}")
    else:
        print(f"  Voice: {C.TTS_VOICE}")

    print("-" * 30)
    
    output_dir = "tests/output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"test_tts_{provider}.mp3")
    
    text = "大家好，我是绘宝！欢迎来到智绘童梦，今天我们要讲一个超级精彩的故事，你们准备好了吗？"
    
    print(f"📝 Text: {text}")
    print(f"🚀 Generating audio...")
    
    studio = AudioStudioFactory.get_studio("default")
    
    # Test with default emotion/style logic
    success = await studio.generate_tts(text, output_path, emotion="happy")
    
    if success:
        print(f"✅ Success! Audio saved to: {output_path}")
        print(f"   Size: {os.path.getsize(output_path)} bytes")
    else:
        print("❌ Failed to generate audio.")

if __name__ == "__main__":
    asyncio.run(main())
