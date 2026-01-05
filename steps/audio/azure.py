import os
from typing import List
from config.config import C
from model.models import Scene
from util.logger import logger
from steps.audio.base import AudioStudioBase

try:
    import azure.cognitiveservices.speech as speechsdk
except ImportError:
    speechsdk = None

class AzureAudioStudio(AudioStudioBase):
    def __init__(self):
        self.speech_key = getattr(C, "AZURE_TTS_KEY", "")
        self.service_region = getattr(C, "AZURE_TTS_REGION", "eastus")
        self.voice = getattr(C, "TTS_VOICE", "zh-CN-XiaoxiaoNeural")
        
        if not speechsdk:
            logger.error("Azure SDK not found. Please install `azure-cognitiveservices-speech`.")
        if not self.speech_key:
            logger.warning("AZURE_TTS_KEY not configured.")

    async def generate_tts(self, text: str, output_path: str, emotion: str = None) -> bool:
        """
        Generates TTS audio using Azure Speech SDK with SSML for emotion support.
        """
        if not speechsdk:
            logger.error("Cannot generate audio: Azure SDK missing.")
            return False

        try:
            speech_config = speechsdk.SpeechConfig(subscription=self.speech_key, region=self.service_region)
            # Set audio output to file
            audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)
            
            # Construct SSML
            # Azure SSML structure: <speak ...><voice ...><mstts:express-as style="...">...</mstts:express-as></voice></speak>
            
            ssml_style_tag_open = ""
            ssml_style_tag_close = ""
            
            if C.ENABLE_EMOTIONAL_TTS and emotion and emotion not in ["neutral", "default"]:
                # Azure supports many styles: cheerful, sad, angry, excited, friendly, etc.
                # Assuming 'emotion' string matches Azure style names or mapping is simple.
                ssml_style_tag_open = f'<mstts:express-as style="{emotion}">'
                ssml_style_tag_close = '</mstts:express-as>'
                logger.debug(f"🎭 Azure TTS using style: {emotion}")

            # Apply speech rate if needed (global setting)
            # rate defined in C.TTS_RATE or C.get_speech_rate?
            # Config has 'TTS_RATE' string like "+0%". 
            # We can also wrap in <prosody rate="...">.
            rate = C.get_speech_rate(C.CURRENT_CATEGORY)
            ssml_prosody_open = f'<prosody rate="{rate}">' if rate else ""
            ssml_prosody_close = '</prosody>' if rate else ""

            ssml = (
                f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
                f'xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="zh-CN">\n'
                f'  <voice name="{self.voice}">\n'
                f'    {ssml_style_tag_open}\n'
                f'      {ssml_prosody_open}{text}{ssml_prosody_close}\n'
                f'    {ssml_style_tag_close}\n'
                f'  </voice>\n'
                f'</speak>'
            )

            synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
            
            # Since generate_tts is async in base but Azure SDK is sync/callback based,
            # we can run it in executor or just use the sync method provided by SDK (speak_ssml_async returns strict future).
            # speak_ssml_async().get() blocks.
            
            result = synthesizer.speak_ssml_async(ssml).get()

            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                logger.debug(f"Azure TTS success: {output_path}")
                return True
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                logger.error(f"Azure TTS canceled: {cancellation_details.reason}")
                if cancellation_details.reason == speechsdk.CancellationReason.Error:
                    logger.error(f"Error details: {cancellation_details.error_details}")
                return False
            else:
                logger.error(f"Azure TTS failed with reason: {result.reason}")
                return False

        except Exception as e:
            logger.traceback_and_raise(Exception(f"Azure TTS Exception: {e}"))
            return False

    async def _generate_one_audio(self, scene: Scene, force: bool = False):
        text = scene.narration
        output_filename = f"scene_{scene.scene_id}.mp3"
        output_path = os.path.join(C.OUTPUT_DIR, output_filename)
        
        if not force and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(f"Skipping Audio {scene.scene_id} (Exists): {output_path}")
            scene.audio_path = output_path
            return

        logger.info(f"Generating Azure audio for Scene {scene.scene_id}...")
        
        try:
            emotion = getattr(scene, "emotion", None)
            success = await self.generate_tts(text, output_path, emotion)
            
            if not success:
                 raise Exception("Azure TTS returned false")
            
            scene.audio_path = output_path
            
        except Exception as e:
            logger.traceback_and_raise(
                Exception(f"Failed to generate audio for Scene {scene.scene_id}: {e}")
            )

    async def generate_audio(self, scenes: List[Scene], force: bool = False):
        logger.info(f"Starting Azure audio generation for {len(scenes)} scenes...")
        for scene in scenes:
            await self._generate_one_audio(scene, force)
