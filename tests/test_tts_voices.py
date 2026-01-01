import asyncio
import edge_tts

# All voices referenced in config.yaml
CANDIDATES = [
    # Female
    "zh-CN-XiaoxiaoNeural",
    "zh-CN-XiaoyiNeural",
    "zh-CN-XiaomoNeural", # Failed?
    "zh-CN-XiaohanNeural", # Failed?
    "zh-CN-XiaoruiNeural",
    "zh-CN-XiaoshuangNeural",
    
    # Male
    "zh-CN-YunxiNeural",
    "zh-CN-YunyangNeural",
    "zh-CN-YunxiaNeural",
    "zh-CN-YunjianNeural",
    "zh-CN-YunfengNeural",
    "zh-CN-YunhaoNeural",
    
    # English
    "en-US-AnaNeural",
    "en-US-ChristopherNeural",
    "en-US-MichelleNeural",
    "en-US-GuyNeural"
]

import os

async def test_voice(voice):
    print(f"Testing {voice}...", end=" ", flush=True)
    try:
        communicate = edge_tts.Communicate("Testing voice availability.", voice)
        await communicate.save(f"test_{voice}.mp3")
        # Check size
        if os.path.exists(f"test_{voice}.mp3") and os.path.getsize(f"test_{voice}.mp3") > 0:
            print("✅ OK")
            os.remove(f"test_{voice}.mp3")
        else:
             print("❌ Empty File")
    except Exception as e:
        print(f"❌ Failed: {str(e)[:50]}")

async def main():
    print(f"Checking {len(CANDIDATES)} voices...")
    for v in CANDIDATES:
        await test_voice(v)

if __name__ == "__main__":
    asyncio.run(main())
