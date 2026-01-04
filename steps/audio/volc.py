import os
import uuid
import requests
import base64
from typing import List
from config.config import C
from model.models import Scene
from util.logger import logger
from steps.audio.base import AudioStudioBase


class VolcAudioStudio(AudioStudioBase):
    def __init__(self):
        self.appid = getattr(C, "VOLC_TTS_APPID", "")
        self.token = getattr(C, "VOLC_TTS_TOKEN", "")
        self.cluster = getattr(C, "VOLC_TTS_CLUSTER", "volcano_tts")
        self.voice_type = getattr(C, "VOLC_TTS_VOICE_TYPE", "BV701_streaming")
        self.host = "openspeech.bytedance.com"
        self.api_url = f"https://{self.host}/api/v1/tts"

        if not self.appid or not self.token:
            logger.warning("VOLC_TTS_APPID or VOLC_TTS_TOKEN not configured.")

    async def generate_tts(
        self, text: str, output_path: str, emotion: str = None
    ) -> bool:
        """
        Generates TTS audio using Volcengine API.
        """
        if not self.appid or not self.token:
            logger.error("Cannot generate audio: Volcengine AppID/Token missing.")
            return False

        try:
            # Prepare request
            # Ref: https://www.volcengine.com/docs/6561/96752

            # TODO: Emotion mapping if Volcengine supports it via SSML or params.
            # Volcengine generally sets emotion via 'emotion' param in request, NOT standard SSML.
            # Supported emotions depend on the voice.
            # We will pass 'emotion' if config enables it.

            header = {"Authorization": f"Bearer;{self.token}"}

            request_json = {
                "app": {
                    "appid": self.appid,
                    "token": self.token,
                    "cluster": self.cluster,
                },
                "user": {"uid": "auto_ai_video_user"},
                "audio": {
                    "voice_type": self.voice_type,
                    "encoding": "mp3",
                    "speed_ratio": 1.0,
                    "volume_ratio": 1.0,
                    "pitch_ratio": 1.0,
                },
                "request": {
                    "reqid": str(uuid.uuid4()),
                    "text": text,
                    "text_type": "plain",
                    "operation": "query",
                },
            }

            # Apply speed ratio from config
            rate_str = C.get_speech_rate(C.CURRENT_CATEGORY)
            # rate_str is like "+15%" or "-10%". Convert to ratio 1.15 / 0.9.
            if rate_str:
                try:
                    val = float(rate_str.replace("%", ""))
                    ratio = 1.0 + (val / 100.0)
                    request_json["audio"]["speed_ratio"] = ratio
                except:
                    pass

            # Apply emotion if applicable
            # Note: Not all voices support emotion parameter directly in V1 API this way without specific voice configuration.
            # Usually you just specific voice_type that IS emotional (e.g. story specific voice).
            # But "emotion" param exists for some voices.
            if (
                C.ENABLE_EMOTIONAL_TTS
                and emotion
                and emotion not in ["neutral", "default"]
            ):
                # Map standard emotions to Volcengine emotions if needed.
                # Common volc emotions: happy, sad, angry, fear, surprise
                request_json["audio"]["emotion"] = emotion
                logger.debug(f"🌋 Volc TTS using emotion: {emotion}")

            resp = requests.post(self.api_url, json=request_json, headers=header)

            if "data" in resp.json():
                data = resp.json()["data"]
                # data is base64 encoded audio
                if data:
                    audio_bytes = base64.b64decode(data)
                    with open(output_path, "wb") as f:
                        f.write(audio_bytes)
                    logger.debug(f"Volc TTS success: {output_path}")
                    return True
                else:
                    logger.error(f"Volc TTS response has no data: {resp.text}")
                    return False
            else:
                logger.error(f"Volc TTS failed: {resp.text}")
                return False

        except Exception as e:
            logger.error(f"Volc TTS Exception: {e}")
            return False

    async def _generate_one_audio(self, scene: Scene, force: bool = False):
        text = (
            scene.narration
        )  # Or scene.text if narration is empty? scene.narration IS the script.
        output_filename = f"scene_{scene.scene_id}.mp3"
        output_path = os.path.join(C.OUTPUT_DIR, output_filename)

        if (
            not force
            and os.path.exists(output_path)
            and os.path.getsize(output_path) > 0
        ):
            logger.info(f"Skipping Audio {scene.scene_id} (Exists): {output_path}")
            scene.audio_path = output_path
            return

        logger.info(f"Generating Volcengine audio for Scene {scene.scene_id}...")

        try:
            emotion = getattr(scene, "emotion", None)
            success = await self.generate_tts(text, output_path, emotion)

            if not success:
                raise Exception("Volc TTS returned false")

            scene.audio_path = output_path

        except Exception as e:
            logger.error(f"Failed to generate audio for Scene {scene.scene_id}: {e}")

    async def generate_audio(self, scenes: List[Scene], force: bool = False):
        logger.info(f"Starting Volcengine audio generation for {len(scenes)} scenes...")
        for scene in scenes:
            await self._generate_one_audio(scene, force)
