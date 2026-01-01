from abc import ABC, abstractmethod
from typing import List
from model.models import Scene

class AudioStudioBase(ABC):
    @abstractmethod
    async def generate_audio(self, scenes: List[Scene], force: bool = False):
        pass
    
    @abstractmethod
    async def generate_tts(self, text: str, output_path: str, emotion: str = None) -> bool:
        pass
