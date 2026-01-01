from steps.animator.base_animator import BaseAnimator
from util.logger import logger
from model.models import Scene


class MockAnimator(BaseAnimator):
    """
    用于测试而不花钱。
    只是将图片复制为 5 秒视频 (幻灯片风格) 或什么都不做。
    """

    async def animate_scene(self, scene: Scene) -> str:
        logger.info(f"正在模拟动画化场景 {scene.scene_id}...")
        if not scene.image_path:
            return ""

        # 在真正的 Mock 中，我们可以使用 ffmpeg 制作静态视频
        # 但 VideoAssembler 也可以处理静态图片。
        # 所以如果我们想测试流程，我们就假装生成了视频路径。
        return ""
