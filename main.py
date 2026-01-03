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

    raw_topic = (args.topic or "").strip()
    main_topic = raw_topic
    subtitle = (args.subtitle or "").strip()
    cover_title = (args.title or "").strip()
    context_topic = main_topic

    if not cover_title:
        cover_title = main_topic

    cover_subtitle = (getattr(args, "cover_subtitle", "") or "").strip()
    if not cover_subtitle:
        cover_subtitle = subtitle

    # 目录使用“干净主题 + 副标题”以隔离不同章节产物
    clean_full_topic = f"{main_topic}:{subtitle}" if subtitle else main_topic
    config.setup(
        category=args.category,
        topic=clean_full_topic,
        style_arg=args.style,
        enable_subs=args.subtitles,
        voice_arg=args.voice,
    )

    loop = asyncio.get_event_loop()

    # 兼容 Python 3.9：避免使用 match/case
    if args.step == step.SCRIPT:
        loop.run_until_complete(
            step.run_step_script(main_topic, subtitle, args.force, context_topic)
        )
    elif args.step == step.IMAGE:
        loop.run_until_complete(step.run_step_image(main_topic, args.force))
    elif args.step == step.ANIMATE:
        loop.run_until_complete(step.run_step_animate(main_topic))
    elif args.step == step.AUDIO:
        loop.run_until_complete(step.run_step_audio(main_topic, args.force))
    elif args.step == step.VIDEO:
        loop.run_until_complete(step.run_step_video(cover_title, cover_subtitle))
    elif args.step == step.ALL:
        loop.run_until_complete(
            step.run_all_with_cover(
                topic=main_topic,
                subtitle=subtitle,
                force=args.force,
                context_topic=context_topic,
                cover_title=cover_title,
                cover_subtitle=cover_subtitle,
            )
        )
    else:
        logger.error(f"Unknown step: {args.step}")


if __name__ == "__main__":
    main()
