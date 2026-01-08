import argparse


def parse_args():
    parser = argparse.ArgumentParser(description="Auto Video Maker")
    parser.add_argument(
        "--topic",
        "-t",
        type=str,
        help="【必填】主题内容（给 AI 理解用，可包含版本/章节/剧情信息）",
        required=True,
    )
    parser.add_argument(
        "--title",
        "-T",
        type=str,
        help="【可选】封面主标题（不填则直接使用 --topic 原文）",
        default="",
    )
    parser.add_argument(
        "--subtitle",
        "-s",
        type=str,
        help="【可选】脚本副标题/章节（用于让 AI 聚焦到某一章节；不填则不处理子标题）",
        default="",
    )
    parser.add_argument(
        "--cover-subtitle",
        "-S",
        type=str,
        help="【可选】封面小标题（不填则不处理子标题）",
        default="",
    )
    parser.add_argument(
        "--category",
        "-c",
        type=str,
        help="【必填】分类/系列（用于目录组织，例如：history、bedtime；支持别名见 config.yaml）",
        required=True,
    )
    parser.add_argument(
        "--style",
        "-y",
        type=str,
        help="【可选】覆盖图片风格（例如：'Pixar'、'Ink Wash'），或使用预设 key",
        default=None,
    )
    parser.add_argument(
        "--subtitles", 
        "-z", 
        action="store_true", 
        help="【可选】开启字幕（默认关闭；传入后开启，中文会自动加拼音）",
    )
    parser.add_argument(
        "--voice",
        "-v",
        type=str,
        help="【可选】覆盖 TTS 音色（例如：zh-CN-YunxiNeural）",
        default=None,
    )
    parser.add_argument(
        "--parallax",
        "-p",
        type=str,
        help="【可选】视差开关 override (true/false/on/off)",
        default=None,
    )
    parser.add_argument(
        "--emotion",
        "-E",
        type=str,
        help="【可选】TTS 情感参数（例如：happy, sad, angry）；仅部分火山引擎音色支持",
        default=None,
    )
    parser.add_argument(
        "--step",
        "-e",
        type=str,
        help="【可选】要运行的步骤：script, image, animate, audio, video, all（默认：all）",
        default="all",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="【可选】强制重新生成（默认关闭；传入后即使已有产物也会重跑）",
    )
    args = parser.parse_args()
    return args
