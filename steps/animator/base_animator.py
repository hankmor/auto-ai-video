from abc import ABC, abstractmethod
from model.models import Scene
from util.logger import logger


class BaseAnimator(ABC):
    @abstractmethod
    async def animate_scene(self, scene: Scene) -> str:
        """
        接收包含 image_path 的场景对象，生成视频，
        设置 scene.video_path，并返回路径。
        """
        pass