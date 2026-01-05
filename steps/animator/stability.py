import os
import asyncio
import requests
import time
from steps.animator.base_animator import BaseAnimator
from util.logger import logger
from config.config import C
from model.models import Scene


class StabilityAnimator(BaseAnimator):
    def __init__(self):
        self.api_key = C.STABILITY_API_KEY
        self.api_host = "https://api.stability.ai"

    async def animate_scene(self, scene: Scene) -> str:
        if not scene.image_path:
            logger.warning(f"场景 {scene.scene_id} 没有图片。")
            return ""

        if not self.api_key:
            logger.warning("未设置 Stability API Key。")
            return ""

        logger.info(f"正在使用 Stability AI (SVD) 动画化场景 {scene.scene_id}...")

        # Stability AI SVD API 实现
        try:
            # 1. 开始生成
            with open(scene.image_path, "rb") as f:
                response = requests.post(
                    f"{self.api_host}/v2beta/image-to-video",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    files={"image": f},
                    data={"seed": 0, "cfg_scale": 1.8, "motion_bucket_id": 127},
                )

            if response.status_code != 200:
                logger.error(
                    f"Stability SVD 错误 ({response.status_code}): {response.text}"
                )
                return ""

            generation_id = response.json().get("id")
            logger.info(f"生成已开始: {generation_id}")

            # 2. 轮询结果
            waiting = True
            video_bytes = None

            start_time = time.time()
            while waiting:
                if time.time() - start_time > 120:  # 2分钟超时
                    logger.error("等待 Stability 动画超时。")
                    break

                response = requests.get(
                    f"{self.api_host}/v2beta/image-to-video/result/{generation_id}",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Accept": "video/*",
                    },
                )

                if response.status_code == 202:
                    # 仍在处理中
                    await asyncio.sleep(5)
                elif response.status_code == 200:
                    video_bytes = response.content
                    waiting = False
                else:
                    logger.error(f"轮询失败 ({response.status_code}): {response.text}")
                    waiting = False

            # 3. 保存视频
            if video_bytes:
                video_filename = f"video_{scene.scene_id}.mp4"
                video_path = os.path.join(C.OUTPUT_DIR, video_filename)
                with open(video_path, "wb") as f:
                    f.write(video_bytes)

                logger.info(f"动画已保存到 {video_path}")
                scene.video_path = video_path
                return video_path

            return ""

        except Exception as e:
            logger.traceback_and_raise(Exception(f"Stability 动画失败: {e}"))
            return ""
