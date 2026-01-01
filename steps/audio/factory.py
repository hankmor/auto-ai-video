from steps.audio.base import AudioStudioBase
from steps.audio.generic import GenericAudioStudio


class AudioStudioFactory:
    @staticmethod
    def get_studio(category: str) -> AudioStudioBase:
        # Currently only Generic exists
        return GenericAudioStudio()
