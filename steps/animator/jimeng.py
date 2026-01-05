import os
import requests
import asyncio
from steps.animator.base_animator import BaseAnimator
from util.logger import logger
from config.config import C
from model.models import Scene


class JimengAnimator(BaseAnimator):
    def __init__(self):
        from auto_maker.providers.volcengine_provider import VolcengineProvider

        try:
            self.provider = VolcengineProvider(C)
            self.client = self.provider.get_image_client(service_type="visual")
        except Exception as e:
            logger.traceback_and_raise(Exception(f"初始化 JimengAnimator 失败: {e}"))
            self.client = None

    async def animate_scene(self, scene: Scene) -> str:
        if not scene.image_path:
            logger.traceback_and_raise(
                Exception(f"场景 {scene.scene_id} 没有图片可供动画化。")
            )
            return ""

        if not self.client:
            logger.traceback_and_raise(Exception("Volcengine Visual Client 不可用。"))
            return ""

        logger.info(f"正在使用即梦 (Volcengine) 动画化场景 {scene.scene_id}...")

        try:
            # 1.读取图片并编码为 Base64
            import base64

            if not os.path.exists(scene.image_path):
                logger.traceback_and_raise(Exception(f"找不到图片: {scene.image_path}"))
                return ""

            with open(scene.image_path, "rb") as image_file:
                binary_data = image_file.read()
                base64_data = base64.b64encode(binary_data).decode("utf-8")

            # 2. 构建请求载荷
            # 使用 Jimeng 3.0 (jimeng_i2v_first_v30)
            req_key = (
                C.JIMENG_VIDEO_REQ_KEY
                if hasattr(C, "JIMENG_VIDEO_REQ_KEY")
                else "jimeng_i2v_first_v30"
            )

            # Jimeng API 通常期望输入的 'binary_data_base64' 是一个列表
            final_prompt = scene.image_prompt
            if scene.camera_action:
                camera_map = {
                    "zoom_in": "镜头拉近",
                    "zoom_out": "镜头拉远",
                    "pan_left": "镜头左移",
                    "pan_right": "镜头右移",
                    "pan_up": "镜头上移",
                    "pan_down": "镜头下移",
                    "follow": "镜头跟随",
                    "shake": "镜头晃动",
                    "static": "固定镜头",
                }
                cam_text = camera_map.get(scene.camera_action)
                if cam_text:
                    final_prompt = f"{final_prompt}，{cam_text}"
                    logger.info(
                        f"Adding camera action: {cam_text} ({scene.camera_action})"
                    )

            payload = {
                "req_key": req_key,
                "binary_data_base64": [base64_data],
                "prompt": final_prompt,
                "frames": 121,  # 5s default per docs
            }

            logger.info(
                f"正在向火山引擎提交任务 (key={req_key}, action=CVSync2AsyncSubmitTask)..."
            )
            try:
                # 使用 explicit action
                resp = self.client.common_json_handler(
                    "CVSync2AsyncSubmitTask", payload
                )
            except Exception as e:
                if "50400" in str(e):
                    logger.traceback_and_raise(
                        Exception(
                            "权限拒绝: 请检查 AK/SK 是否有该服务的访问权限 (jimeng_i2v_first_v30)"
                        )
                    )
                else:
                    logger.traceback_and_raise(Exception(f"提交任务失败: {e}"))
                return ""

            # 3. 解析 task_id 并轮询
            task_id = ""
            if isinstance(resp, dict):
                # 标准 JSON 响应
                err_code = resp.get("code")
                if err_code == 10000:
                    task_id = resp.get("data", {}).get("task_id")
                else:
                    logger.traceback_and_raise(
                        Exception(f"提交失败，错误码 {err_code}: {resp.get('message')}")
                    )
                    return ""

            if not task_id:
                logger.traceback_and_raise(Exception(f"未收到有效 Task ID: {resp}"))
                return ""

            logger.info(f"任务已提交，Task ID: {task_id}。开始轮询...")

            # 4. 轮询 (Polling)
            import time
            import asyncio

            max_retries = 60  # 5s * 60 = 5分钟
            for i in range(max_retries):
                # Poll Request
                try:
                    # 使用 CVGetResult 查询
                    poll_payload = {"req_key": req_key, "task_id": task_id}
                    poll_resp = self.client.common_json_handler(
                        "CVGetResult", poll_payload
                    )

                    if not isinstance(poll_resp, dict):
                        logger.warning(f"Poll 响应格式错误: {poll_resp}")
                        continue

                    p_code = poll_resp.get("code")
                    if p_code != 10000:
                        logger.warning(
                            f"Poll 错误 ({p_code}): {poll_resp.get('message')}"
                        )
                        # 部分错误可能是暂时的
                        pass

                    data = poll_resp.get("data", {})
                    status = data.get("status")

                    logger.info(f"轮询中... ({i}/{max_retries}) Status: {status}")

                    if status == "succeeded" or status == "success" or status == "done":
                        # 尝试直接从 data 获取 video_url (Jimeng First Frame)
                        video_url = data.get("video_url")

                        if not video_url:
                            resp_data = data.get("resp_data")
                            # Handle recursive json in resp_data
                            if isinstance(resp_data, str):
                                try:
                                    import json

                                    resp_data_json = json.loads(resp_data)
                                    video_url = resp_data_json.get("video_url")
                                except:
                                    pass
                            elif isinstance(resp_data, dict):
                                video_url = resp_data.get("video_url")

                        if video_url:
                            logger.info(f"生成成功! URL: {video_url}")
                            # Download
                            return await self._save_video(video_url, scene)
                        else:
                            logger.error("成功但未找到 Video URL (可能在不同字段?)")
                            # 调试: 打印完整数据以备查
                            logger.error(f"Resp Data: {resp_data}")
                        return ""

                    elif status == "failed":
                        logger.error(f"生成失败: {data.get('error_msg')}")
                        return ""

                except Exception as e:
                    logger.traceback_and_raise(Exception(f"轮询异常: {e}"))

                await asyncio.sleep(5)

            logger.error("轮询超时。")
            return ""
        except Exception as e:
            logger.traceback_and_raise(Exception(f"Jimeng 动画错误: {e}"))
            return ""

    async def _save_video(self, url, scene):
        video_filename = f"video_{scene.scene_id}.mp4"
        video_path = os.path.join(C.OUTPUT_DIR, video_filename)
        response = requests.get(url)
        if response.status_code == 200:
            with open(video_path, "wb") as f:
                f.write(response.content)
            logger.info(f"已保存 Jimeng 视频到 {video_path}")
            scene.video_path = video_path
            return video_path
        return ""

    async def _save_binary(self, b64_str, scene):
        import base64

        video_filename = f"video_{scene.scene_id}.mp4"
        video_path = os.path.join(C.OUTPUT_DIR, video_filename)
        with open(video_path, "wb") as f:
            f.write(base64.b64decode(b64_str))
        logger.info(f"已保存 Jimeng 视频 (二进制) 到 {video_path}")
        scene.video_path = video_path
        return video_path
