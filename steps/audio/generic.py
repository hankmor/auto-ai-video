import os
import edge_tts
from typing import List
import numpy as np
from moviepy.editor import AudioFileClip, concatenate_audioclips
from moviepy.audio.AudioClip import AudioArrayClip

from config.config import C
from model.models import Scene
from util.logger import logger
from steps.audio.base import AudioStudioBase

class GenericAudioStudio(AudioStudioBase):
    def __init__(self):
        self.voice = C.TTS_VOICE

    async def generate_tts(
        self,
        text: str,
        output_path: str,
        emotion: str = None,
        voice_override: str = None,
    ) -> bool:
        """
        Generates TTS audio with optional emotion simulation using prosody.
        """
        try:
            # 0. Apply Pronunciation Fixes
            if hasattr(C, "PRONUNCIATION_FIXES") and C.PRONUNCIATION_FIXES:
                for target, replacement in C.PRONUNCIATION_FIXES.items():
                    if target in text:
                        text = text.replace(target, replacement)

            # Use voice_override if provided, else default
            voice = voice_override if voice_override else self.voice

            if (
                C.ENABLE_EMOTIONAL_TTS
                and emotion
                and emotion != "neutral"
                and emotion != "serious"
            ):
                emotion_map = {
                    "cheerful": {"pitch": "+15Hz", "rate": "+3%"},
                    "excited": {"pitch": "+20Hz", "rate": "+8%"},
                    "sad": {"pitch": "-15Hz", "rate": "-5%"},
                    "fearful": {"pitch": "+10Hz", "rate": "+10%"},
                    "affectionate": {"pitch": "-8Hz", "rate": "-8%"},
                    "angry": {"pitch": "+5Hz", "rate": "+5%"},
                    "greedy": {"pitch": "+8Hz", "rate": "+5%"},
                    "confident": {"pitch": "+5Hz", "rate": "+0%"},
                    "surprised": {"pitch": "+18Hz", "rate": "+12%"},
                    "gentle": {"pitch": "-5Hz", "rate": "-5%"},
                }
                
                prosody = emotion_map.get(emotion, {"pitch": "+0Hz", "rate": "+0%"})
                
                communicate = edge_tts.Communicate(
                    text, voice, pitch=prosody["pitch"], rate=prosody["rate"]
                )
                logger.debug(f"🎭 Using emotion '{emotion}' (pitch:{prosody['pitch']}, rate:{prosody['rate']})")
            else:
                speech_rate = C.get_speech_rate(C.CURRENT_CATEGORY)
                communicate = edge_tts.Communicate(text, voice, rate=speech_rate)
                
            await communicate.save(output_path)
            return True
        except Exception as e:
            logger.error(f"TTS Generation failed: {e}")
            return False

    async def _generate_one_audio(self, scene: Scene, force: bool = False):
        text = scene.narration
        output_filename = f"scene_{scene.scene_id}.mp3"
        output_path = os.path.join(C.OUTPUT_DIR, output_filename)
        
        if not force and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(f"Skipping Audio {scene.scene_id} (Exists): {output_path}")
            scene.audio_path = output_path
            return

        logger.info(f"Generating audio for Scene {scene.scene_id} ({len(text)} chars)...")
        
        try:
            emotion = getattr(scene, "emotion", None)

            if C.ENABLE_BILINGUAL_MODE and getattr(scene, "narration_cn", None):
                # Bilingual Mode: Generate EN -> Pause -> CN
                path_en = output_path.replace(".mp3", "_en.mp3")
                path_cn = output_path.replace(".mp3", "_cn.mp3")

                logger.info(f"  - Generating Bilingual Audio (EN + CN)")

                # 1. Generate English
                await self.generate_tts(scene.narration, path_en, emotion)
                # 2. Generate Chinese (use configured voice if available)
                cn_voice = C.BILINGUAL_CN_VOICE if C.BILINGUAL_CN_VOICE else None
                await self.generate_tts(
                    scene.narration_cn, path_cn, emotion, voice_override=cn_voice
                )

                if os.path.exists(path_en) and os.path.exists(path_cn):
                    # 3. Concatenate using MoviePy
                    clip_en = AudioFileClip(path_en)
                    clip_cn = AudioFileClip(path_cn)

                    # Silence (Pause)
                    # Create 2 channels of silence
                    # Assuming 44100Hz default from edge-tts usually
                    silence_duration = C.BILINGUAL_AUDIO_PAUSE
                    sr = 44100
                    silence_array = np.zeros((int(sr * silence_duration), 2))
                    silence_clip = AudioArrayClip(silence_array, fps=sr)

                    final_clip = concatenate_audioclips(
                        [clip_en, silence_clip, clip_cn]
                    )
                    final_clip.write_audiofile(output_path, logger=None)

                    clip_en.close()
                    clip_cn.close()
                    final_clip.close()

                    # Cleanup separate files
                    if os.path.exists(path_en):
                        os.remove(path_en)
                    if os.path.exists(path_cn):
                        os.remove(path_cn)

                    scene.audio_path = output_path
                else:
                    raise Exception("Failed to generate bilingual parts")

            else:
                # Normal Mode
                success = await self.generate_tts(text, output_path, emotion)

                if not success:
                    raise Exception("TTS Generation returned false")

                scene.audio_path = output_path
            
        except Exception as e:
            logger.error(f"Failed to generate audio for Scene {scene.scene_id}: {e}")

    async def generate_audio(self, scenes: List[Scene], force: bool = False):
        logger.info(f"Starting audio generation for {len(scenes)} scenes...")
        for scene in scenes:
            await self._generate_one_audio(scene, force)
