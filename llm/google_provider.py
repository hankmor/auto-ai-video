from llm.base import BaseProvider
from util.logger import logger

try:
    import google.generativeai as genai
except ImportError:
    genai = None

class GoogleProvider(BaseProvider):
    """
    Provider for Google (Gemini).
    """
    def __init__(self, config):
        super().__init__(config)
        self.client = None

    def validate_config(self) -> bool:
        return bool(self.config.GEMINI_API_KEY)

    def get_llm_client(self):
        """
        Returns configured genai module.
        """
        if self.client:
            return self.client
            
        if not genai:
             raise ImportError("google-generativeai package not installed.")

        if not self.config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set.")
            
        genai.configure(api_key=self.config.GEMINI_API_KEY)
        self.client = genai
        return self.client

    def get_image_client(self):
        """
        Gemini Consumer API currently does not support standardized Image Gen via 'genai' SDK easily.
        """
        logger.warning("Google/Gemini Image Generation not fully supported via API Key yet.")
        return None
