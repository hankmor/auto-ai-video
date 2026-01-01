import os
import requests
import asyncio
from typing import List
from openai import AsyncOpenAI
from config.config import config
from model.models import Scene
from util.logger import logger

try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    from volcenginesdkarkruntime import Ark
except ImportError:
    Ark = None


class ImageFactory:
    def __init__(self):
        self.provider = "openai"
        self.client = None

        # Determine provider
        provider_key = config.IMAGE_PROVIDER.lower() if config.IMAGE_PROVIDER else ""
        model_name = config.IMAGE_MODEL.lower()

        if provider_key == "openai" or (not provider_key and "dall-e" in model_name):
            self.provider = "openai"
            from llm.openai_provider import OpenAIProvider

            try:
                self.client = OpenAIProvider(config).get_image_client()
            except Exception as e:
                logger.error(f"Failed to init OpenAI Provider for Image: {e}")

        elif provider_key == "google" or (
            not provider_key and ("imagen" in model_name or "gemini" in model_name)
        ):
            self.provider = "google"
            from llm.google_provider import GoogleProvider

            self.client = GoogleProvider(config).get_image_client()  # Might be None

        elif provider_key in ["doubao", "volcengine"] or (
            not provider_key
            and (
                "doubao" in model_name
                or "volc" in model_name
                or "ep-" in model_name
                or "jimeng" in model_name
            )
        ):
            self.provider = "doubao"

            from llm.volcengine_provider import VolcengineProvider

            try:
                self.volc_provider = VolcengineProvider(config)
                # We will lazy load specific clients (Ark vs Visual) in _generate_one_image depending on the model
                # But to fail fast on auth, we can check basic validity
                if not self.volc_provider.validate_config():
                    logger.warning(
                        "Volcengine config invalid (Missing keys). Doubao/Jimeng might fail."
                    )

            except Exception as e:
                logger.error(f"Failed to initialize Volcengine Provider: {e}")
                raise e

    async def generate_images(self, scenes: List[Scene], force: bool = False):
        logger.info(
            f"Starting image generation for {len(scenes)} scenes using {config.IMAGE_MODEL}..."
        )

        tasks = []
        for scene in scenes:
            tasks.append(self._generate_one_image(scene, force))

        results = await asyncio.gather(*tasks)
        return results

    async def _generate_one_image(self, scene: Scene, force: bool = False) -> str:
        prompt = scene.image_prompt

        # Apply sensitive word filtering
        if hasattr(config, "SENSITIVE_WORDS") and config.SENSITIVE_WORDS:
            for sensitive, replacement in config.SENSITIVE_WORDS.items():
                if sensitive in prompt:
                    logger.info(
                        f"🛡️ Sensitive word detected: replacing '{sensitive}' with '{replacement}'"
                    )
                    prompt = prompt.replace(sensitive, replacement)
        image_filename = f"scene_{scene.scene_id}.png"
        image_path = os.path.join(config.OUTPUT_DIR, image_filename)

        if not force and os.path.exists(image_path) and os.path.getsize(image_path) > 0:
            logger.info(f"Skipping Image {scene.scene_id} (Exists): {image_path}")
            scene.image_path = image_path
            return image_path

        logger.info(f"Generating image for Scene {scene.scene_id}...")

        try:
            if self.provider == "openai":
                response = await self.client.images.generate(
                    model=config.IMAGE_MODEL,
                    prompt=prompt,
                    size=config.IMAGE_SIZE,  # Use config size (e.g. 1024x1792)
                    quality="standard",
                    n=1,
                )
                image_url = response.data[0].url
                await self._download_image(image_url, image_path)

            # ... (Google Skipped) ...

            elif self.provider == "doubao":
                # Determine sub-type (Ark Endpoint or Visual Service)
                is_ark_endpoint = config.IMAGE_MODEL.startswith("ep-")
                is_mock = config.IMAGE_MODEL.strip() == "mock"

                if is_ark_endpoint:
                    print(f"DEBUG: Ark Endpoint Logic")
                    # ...
                    pass
                elif is_mock:
                    print(f"DEBUG: Mock Mode. Path: {image_path}")
                    # Mock Logic
                    logger.info("Mock Mode: Generating placeholder image...")
                    # For mock, we can create a dummy image or use a placeholder
                    # For now, let's just create a blank image
                    from PIL import Image

                    width, height = 1024, 1024
                    if "x" in config.IMAGE_SIZE:
                        parts = config.IMAGE_SIZE.split("x")
                        width, height = int(parts[0]), int(parts[1])

                    img = Image.new("RGB", (width, height), color="red")
                    img.save(image_path)
                    logger.info(f"Mock image saved to {image_path}")
                else:
                    # VisualService (Jimeng, Doubao 3.0, General 1.3)
                    client = self.volc_provider.get_image_client(service_type="visual")

                    # Parsing Size
                    width, height = 1024, 1024
                    if "x" in config.IMAGE_SIZE:
                        parts = config.IMAGE_SIZE.split("x")
                        width, height = int(parts[0]), int(parts[1])

                    # Logic for req_key
                    req_key = "high_aesthetic_t2i"  # Default
                    if (
                        config.IMAGE_MODEL == "doubao-1.5"
                        or "3.0" in config.IMAGE_MODEL
                    ):
                        req_key = "high_aes_general_v30l_zt2i"
                    elif "jimeng" in config.IMAGE_MODEL:
                        if "4.0" in config.IMAGE_MODEL:
                            req_key = "jimeng_t2i_v40"
                        else:
                            req_key = "jimeng_high_aes_general_v21_L"
                    elif config.IMAGE_MODEL != "doubao":
                        req_key = config.IMAGE_MODEL

                    logger.info(
                        f"🎨 Volcengine Visual Req Key: {req_key} | Size: {width}x{height}"
                    )

                    payload = {
                        "req_key": req_key,
                        "prompt": prompt
                        if "jimeng" in req_key or "v30" in req_key
                        else None,
                        "prompt_text": prompt
                        if "high_aesthetic_t2i" == req_key
                        else None,
                        "width": width,
                        "height": height,
                    }

                    # Unified payload logic
                    if payload.get("prompt") is None:
                        if "prompt" in payload:
                            del payload["prompt"]
                    if payload.get("prompt_text") is None:
                        if "prompt_text" in payload:
                            del payload["prompt_text"]

                    # Just in case model is weird, default to prompt_text if both missing
                    if "prompt" not in payload and "prompt_text" not in payload:
                        payload["prompt"] = prompt

                    try:
                        resp = client.cv_process(payload)

                        if isinstance(resp, bytes):
                            import json

                            resp = json.loads(resp)

                        if resp and "data" in resp and "image_urls" in resp["data"]:
                            image_url = resp["data"]["image_urls"][0]
                            await self._download_image(image_url, image_path)
                        elif (
                            resp
                            and "data" in resp
                            and "binary_data_base64" in resp["data"]
                        ):
                            import base64

                            with open(image_path, "wb") as f:
                                f.write(
                                    base64.b64decode(
                                        resp["data"]["binary_data_base64"][0]
                                    )
                                )
                        else:
                            if (
                                resp.get("ResponseMetadata", {})
                                .get("Error", {})
                                .get("Code")
                                == "AccessDenied"
                            ):
                                logger.error(
                                    "❌ IAM Permission Error: ENABLE Visual Intelligence Service."
                                )
                            raise Exception(f"VisualService Error: {resp}")

                    except Exception as e:
                        logger.error(f"VisualService Request Failed: {e}")
                        raise e

            scene.image_path = image_path
            return image_path

        except Exception as e:
            logger.error(f"Failed to generate image for Scene {scene.scene_id}: {e}")
            return ""

    async def _download_image(self, url: str, path: str):
        # Utilizing requests in synchronous way inside async function is blocking,
        # but for simplicity/prototyping it's okay, or use aiohttp.
        # Let's wrap requests in run_in_executor if needed, or just use requests directly as image download is fast.
        # Better: use aiohttp or similar if strictly async. For now, requests.get is blocking.
        # Switching to synchronous download for stability in prototype.
        response = requests.get(url)
        if response.status_code == 200:
            with open(path, "wb") as f:
                f.write(response.content)
            logger.info(f"Saved image to {path}")
        else:
            logger.error(f"Failed to download image from {url}")
