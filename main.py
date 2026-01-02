import sys
import os
import asyncio

# 将项目根目录添加到 sys.path 以允许作为脚本执行
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from argument import parse_args


def main():
    args = parse_args()

    # 延迟导入：避免在 `-h/--help` 时加载重依赖（例如 pydantic），提升可用性
    import config
    from util.logger import logger
    from steps import step

    # 解析主题/副标题（兼容：既支持 --subtitle，也支持在 --topic 里用冒号写章节）
    raw_topic = (args.topic or "").strip()
    main_topic = raw_topic
    subtitle = (args.subtitle or "").strip()

    if not subtitle:
        # 支持中文冒号和英文冒号
        if "：" in raw_topic:
            parts = raw_topic.split("：", 1)
            main_topic = parts[0].strip()
            subtitle = parts[1].strip()
        elif ":" in raw_topic:
            parts = raw_topic.split(":", 1)
            main_topic = parts[0].strip()
            subtitle = parts[1].strip()

    # 解析封面标题 vs 上下文主题（例如：小狗钱钱|小狗钱钱(少儿版)）
    # cover_title：用于封面/视频标题；context_topic：用于脚本生成时给 LLM 的上下文
    cover_title = (args.title or "").strip()
    context_topic = main_topic

    if "|" in main_topic:
        parts = main_topic.split("|", 1)
        main_topic = parts[0].strip()
        context_topic = parts[1].strip() or main_topic
        logger.info(
            f"📘 主题解析：封面标题='{main_topic}'，上下文主题='{context_topic}'"
        )

    if not cover_title:
        cover_title = main_topic

    cover_subtitle = (getattr(args, "cover_subtitle", "") or "").strip()
    if not cover_subtitle:
        cover_subtitle = subtitle

    # 目录使用“干净主题 + 副标题”以隔离不同章节产物
    clean_full_topic = f"{main_topic}:{subtitle}" if subtitle else main_topic
    config.setup(args.category, clean_full_topic, args.style, args.subtitles, args.voice)

    loop = asyncio.get_event_loop()

    # 兼容 Python 3.9：避免使用 match/case
    if args.step == "script":
        loop.run_until_complete(
            step.run_step_script(main_topic, subtitle, args.force, context_topic)
        )
    elif args.step == "image":
        loop.run_until_complete(step.run_step_image(main_topic, args.force))
    elif args.step == "animate":
        loop.run_until_complete(step.run_step_animate(main_topic))
    elif args.step == "audio":
        loop.run_until_complete(step.run_step_audio(main_topic, args.force))
    elif args.step == "video":
        loop.run_until_complete(step.run_step_video(cover_title, cover_subtitle))
    elif args.step == "all":
        loop.run_until_complete(
            step.run_all_with_cover(
                main_topic,
                subtitle,
                args.force,
                context_topic,
                cover_title=cover_title,
                cover_subtitle=cover_subtitle,
            )
        )
    else:
        logger.error(f"Unknown step: {args.step}")


if __name__ == "__main__":
    main()
