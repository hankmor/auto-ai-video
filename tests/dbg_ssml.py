import asyncio
import edge_tts
import os

# SSML with style
SSML = """<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='https://www.w3.org/2001/mstts' xml:lang='zh-CN'>
    <voice name='zh-CN-XiaoxiaoNeural'>
        <mstts:express-as style='cheerful' styledegree="2">
            大家好，我是绘宝！今天是我出生的第一天，我超级开心！
        </mstts:express-as>
    </voice>
</speak>"""


async def main():
    output_dir = "tests/output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "ssml_test.mp3")

    # 读取 t.xml
    with open("tests/t.xml", "r", encoding="utf-8") as f:
        SSML = f.read()
    print(f"Generating SSML TTS to {output_path}...")
    # NOTE: When using SSML, the voice argument in Communicate is often ignored or acts as fallback?
    # But usually we must provide a voice argument anyway.
    communicate = edge_tts.Communicate(SSML.strip())
    await communicate.save(output_path)
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
