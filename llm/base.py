from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class BaseProvider(ABC):
    """
    Abstract base class for AI Service Providers.
    A Provider encapsulates authentication and client management for a specific platform 
    (e.g. Volcengine, OpenAI, Google).
    """
    
    def __init__(self, config: Any):
        self.config = config
        self.clients = {} # Cache for initialized clients (e.g. 'llm', 'image')

    @abstractmethod
    def get_llm_client(self) -> Any:
        """Return the native client for LLM operations."""
        pass

    @abstractmethod
    def get_image_client(self) -> Any:
        """Return the native client for Image Generation operations."""
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Check if necessary keys/config are present."""
        pass
