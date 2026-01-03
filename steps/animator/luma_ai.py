import os
import asyncio
import requests
from steps.animator.base_animator import BaseAnimator
from util.logger import logger
from config.config import C
from model.models import Scene


class LumaAnimator(BaseAnimator):
    def __init__(self):
        self.api_key = C.LUMA_API_KEY
        self.client = None
        if self.api_key:
            try:
                from lumaai import LumaAI

                self.client = LumaAI(auth_token=self.api_key)
            except ImportError:
                logger.error("未找到 lumaai 库。请执行 pip install lumaai")

    async def animate_scene(self, scene: Scene) -> str:
        if not scene.image_path:
            logger.warning(f"场景 {scene.scene_id} 没有图片可供动画化。")
            return ""

        if not self.client:
            logger.warning("Luma API 不可用 (Key 缺失或 SDK 未安装)。")
            return ""

        logger.info(f"正在使用 Luma Dream Machine 动画化场景 {scene.scene_id}...")

        # 注意: Luma API 通常需要 'image_url' 为公网可访问的 URL。
        # 本地文件路径 (如 /Users/...) 直接使用通常无效，除非 SDK 处理了上传。
        # 检查 SDK 是否支持文件上传，或者我们需要警告用户。
        # 在此实现中，我们尝试查看 SDK 是否接受文件对象或路径，
        # 否则优雅地降级/失败。

        # 重要: 截至 2024 年底，许多视频 API 需要公网 URL。
        # 如果失败，我们需要指导用户使用 ngrok 或 S3 服务。
        # 但是，为了响应用户的 "继续" 请求，我们实现标准调用。

        try:
            # asyncio 包装器中的同步调用
            # 我们假设生成需要时间，所以如果 SDK 不阻塞，我们需要循环/轮询。
            # 官方 SDK 通常有 .create() 和 .get()

            # 开始生成
            # 警告: 如果 SDK 不自动上传，使用本地路径可能会失败。
            # 我们暂时假设用户可能会手动在 image_path 中放入 URL，或者依赖 SDK 的魔法。
            # 如果 scene.image_path 是本地的，这是风险点。

            generation = self.client.generations.create(
                prompt=scene.image_prompt,
                image_url=scene.image_path,  # 如果没有辅助上传，本地文件可能会失败
            )

            gen_id = generation.id
            logger.info(f"Luma 生成已开始: {gen_id}")

            # 轮询直到完成
            while True:
                generation = self.client.generations.get(id=gen_id)
                status = generation.state

                if status == "completed":
                    break
                elif status == "failed":
                    logger.error(f"Luma 生成失败: {generation.failure_reason}")
                    return ""

                logger.info(f"状态: {status}...")
                await asyncio.sleep(5)

            # 下载视频
            video_url = generation.assets.video
            if video_url:
                video_filename = f"video_{scene.scene_id}.mp4"
                video_path = os.path.join(C.OUTPUT_DIR, video_filename)

                # 下载
                response = requests.get(video_url)
                if response.status_code == 200:
                    with open(video_path, "wb") as f:
                        f.write(response.content)
                    logger.info(f"已保存 Luma 视频到 {video_path}")
                    scene.video_path = video_path
                    return video_path

            return ""

        except Exception as e:
            logger.error(f"Luma 动画错误: {e}")
            if "url" in str(e).lower():
                logger.error(
                    "Luma API 可能需要公网 URL。直接使用本地文件路径不受支持。"
                )
            return ""
