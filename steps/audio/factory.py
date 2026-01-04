from config.config import C
from steps.audio.base import AudioStudioBase
from steps.audio.generic import GenericAudioStudio
from steps.audio.azure import AzureAudioStudio
from util.logger import logger

class AudioStudioFactory:
    @staticmethod
    def get_studio(category: str) -> AudioStudioBase:
        provider = getattr(C, "TTS_PROVIDER", "edge")

        if provider == "azure":
            logger.info("🎙️ Using Azure Audio Studio")
            return AzureAudioStudio()

        logger.info("🎙️ Using Generic (Edge) Audio Studio")
        return GenericAudioStudio()
