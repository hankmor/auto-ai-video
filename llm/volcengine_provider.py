from llm.base import BaseProvider
from util.logger import logger

# Try imports, handle missing deps
try:
    from volcenginesdkarkruntime import Ark
except ImportError:
    Ark = None

try:
    from volcengine.visual.VisualService import VisualService
except ImportError:
    VisualService = None

class VolcengineProvider(BaseProvider):
    """
    Provider for Volcengine (Doubao / Visual Intelligence).
    Handles unified authentication via AK/SK or API Key.
    """
    
    def __init__(self, config):
        super().__init__(config)
        self.ark_client = None
        self.visual_client = None

    def validate_config(self) -> bool:
        # Check for unified AK/SK
        has_ak_sk = bool(self.config.VOLC_ACCESS_KEY and self.config.VOLC_SECRET_KEY)
        # Check for Ark Key (optional backup)
        has_ark_key = bool(self.config.ARK_API_KEY)
        
        return has_ak_sk or has_ark_key

    def get_llm_client(self):
        """
        Returns initialized Ark Client for LLM.
        """
        if self.ark_client:
            return self.ark_client
            
        if not Ark:
            logger.error("`volcengine-python-sdk` (Ark component) not found.")
            raise ImportError("Missing dependency: volcengine-python-sdk")

        # Priority 1: ARK_API_KEY (Simpler if set)
        if self.config.ARK_API_KEY:
             logger.info("Initializing Ark Client with API Key")
             self.ark_client = Ark(api_key=self.config.ARK_API_KEY)
             return self.ark_client

        # Priority 2: AK/SK (Unified)
        if self.config.VOLC_ACCESS_KEY and self.config.VOLC_SECRET_KEY:
             logger.info("Initializing Ark Client with Volcengine AK/SK")
             self.ark_client = Ark(ak=self.config.VOLC_ACCESS_KEY, sk=self.config.VOLC_SECRET_KEY)
             return self.ark_client
             
        raise ValueError("Volcengine Credentials missing. Set ARK_API_KEY or VOLC_ACCESS_KEY/SECRET_KEY.")

    def get_image_client(self, service_type="visual"):
        """
        Returns initialized Client for Image Gen.
        
        args:
            service_type: 
                - 'visual': VisualService (CV) for Doubao 3.0 / Jimeng / etc.
                - 'ark': Ark Client (if they eventually move image gen to Ark standard endpoint)
        """
        # For now, Doubao/Jimeng image gen is mostly on VisualService (CV).
        # Some endpoints might use Ark (ep-...), handle that.
        
        if service_type == "ark":
            return self.get_llm_client() # Ark client handles both text and image endpoints if they are standard

        # VisualService (CV)
        if self.visual_client:
            return self.visual_client

        if not VisualService:
             logger.error("`volcengine-python-sdk` (Visual component) not found.")
             raise ImportError("Missing dependency: volcenginesdk")

        if self.config.VOLC_ACCESS_KEY and self.config.VOLC_SECRET_KEY:
            logger.info("Initializing VisualService Client with AK/SK")
            self.visual_client = VisualService()
            self.visual_client.set_ak(self.config.VOLC_ACCESS_KEY)
            self.visual_client.set_sk(self.config.VOLC_SECRET_KEY)
            # Region defaults to cn-north-1 usually, explicit setting if needed:
            # self.visual_client.set_region(config.VOLC_REGION) 
            return self.visual_client
        
        raise ValueError("VisualService requires VOLC_ACCESS_KEY and VOLC_SECRET_KEY.")
