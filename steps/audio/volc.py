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
        self, text: str, output_path: str, emotion: str = None, voice_type: str = None
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

            # Determine effective voice type
            effective_voice = voice_type if voice_type else self.voice_type

            header = {"Authorization": f"Bearer;{self.token}"}

            request_json = {
                "app": {
                    "appid": self.appid,
                    "token": self.token,
                    "cluster": self.cluster,
                },
                "user": {"uid": "auto_ai_video_user"},
                "audio": {
                    "voice_type": effective_voice,
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
            # Determine effective emotion
            # Priority: CLI Argument (--emotion) > Scene Attribute (Script) > None
            emotion = (
                C.TTS_EMOTION if C.TTS_EMOTION else getattr(scene, "emotion", None)
            )

            # Determine appropriate voice
            # 1. Try to find a voice for the category
            category_voices = C.CATEGORY_VOICES.get(C.CURRENT_CATEGORY, [])
            current_voice_type = self.voice_type  # Default Fallback

            if category_voices:
                # Use the first voice in the list for consistency, or random?
                # For Volc, we usually want consistency per video so first one is safer.
                # If we want random per video, we should have decided that earlier.
                # But here we are generating per scene. Switching voices mid-video (if random) is bad.
                current_voice_type = category_voices[0]
                logger.debug(f"Volc using category voice: {current_voice_type}")

            # TODO: Map scene.character to specific voice if multiple characters exist

            # Temporarily set instance voice_type for this call?
            # No, 'generate_tts' uses instance attributes implicitly?
            # Wait, 'generate_tts' uses 'self.voice_type'.
            # I should modify 'generate_tts' to accept 'voice_type' argument or change 'self.voice_type' temporarily.
            # Ideally 'generate_tts' should accept 'voice_type'.

            # Modifying generate_tts signature is cleaner.
            # Or just update self.voice_type? No, that's not thread safe (though asyncio here is single threaded mostly).
            # Let's update generate_tts signature in a separate edit, or hack it here.
            # Actually looking at generate_tts implementation (lines 24-112), it uses self.voice_type.

            # Hack: Pass it via a private method or modify generate_tts now.
            # I will modify generate_tts signature in this same file.

            success = await self.generate_tts(
                text, output_path, emotion, voice_type=current_voice_type
            )

            if not success:
                raise Exception("Volc TTS returned false")

            scene.audio_path = output_path

        except Exception as e:
            logger.error(f"Failed to generate audio for Scene {scene.scene_id}: {e}")
            raise e

    async def generate_audio(self, scenes: List[Scene], force: bool = False):
        logger.info(f"Starting Volcengine audio generation for {len(scenes)} scenes...")
        for scene in scenes:
            await self._generate_one_audio(scene, force)
