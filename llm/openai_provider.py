from llm.base import BaseProvider
from openai import OpenAI, AsyncOpenAI

class OpenAIProvider(BaseProvider):
    """
    Provider for OpenAI (GPT & DALL-E).
    """
    def __init__(self, config):
        super().__init__(config)
        self.client = None # Sync client
        self.async_client = None # Async client

    def validate_config(self) -> bool:
        return bool(self.config.OPENAI_API_KEY)

    def get_llm_client(self):
        """
        Returns Sync OpenAI Client for LLM (compatible with current LLMClient usage).
        If async needed, can adapt. Current LLMClient usage seems sync for text.
        """
        if self.client:
            return self.client
            
        if not self.config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not set.")
            
        self.client = OpenAI(api_key=self.config.OPENAI_API_KEY)
        return self.client

    def get_image_client(self):
        """
        Returns Async OpenAI Client for Image Gen (DALL-E).
        Current ImageFactory uses AsyncOpenAI.
        """
        if self.async_client:
            return self.async_client
            
        if not self.config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not set.")
            
        self.async_client = AsyncOpenAI(api_key=self.config.OPENAI_API_KEY)
        return self.async_client
