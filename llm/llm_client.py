import os
from openai import OpenAI
from config.config import config
from util.logger import logger

try:
    import google.generativeai as genai
except ImportError:
    genai = None


try:
    # import volcenginesdkarkruntime.python_sdk as doubao # 此子模块可能不存在
    from volcenginesdkarkruntime import Ark
except ImportError:
    logger.warning("volcengine-python-sdk (Doubao) not installed.")
    Ark = None

class LLMClient:
    def __init__(self):
        # 确定提供商
        provider_key = config.LLM_PROVIDER.lower() if config.LLM_PROVIDER else ""
        model_name = config.LLM_MODEL.lower()

        if provider_key == "google" or (not provider_key and "gemini" in model_name):
            self.provider = "google"
            from llm.google_provider import GoogleProvider
            try:
                self.client = GoogleProvider(config).get_llm_client()
            except Exception as e:
                logger.error(f"Failed to init Google Provider: {e}")
                raise e

        # Volcengine (豆包)
        elif provider_key in ["doubao", "volcengine"] or (not provider_key and ("doubao" in model_name or "ep-" in model_name)):
            self.provider = "doubao"
            from llm.volcengine_provider import VolcengineProvider
            try:
                self.client = VolcengineProvider(config).get_llm_client()
            except Exception as e:
                logger.error(f"Failed to init Volcengine Provider: {e}")
                raise e

        else:
            # 如果显式设置或未找到其他匹配项，则默认为 OpenAI
            self.provider = "openai"
            from llm.openai_provider import OpenAIProvider
            try:
                self.client = OpenAIProvider(config).get_llm_client()
            except Exception as e:
                logger.error(f"Failed to init OpenAI Provider: {e}")
                self.client = None

    def generate_text(self, prompt: str, system_prompt: str = "You are a helpful assistant.") -> str:
        if not self.client:
            raise ValueError(f"LLM Client ({self.provider}) not initialized. Check API Key.")

        try:
            if self.provider == "google":
                # Google GenAI 用法
                model = self.client.GenerativeModel(
                    model_name=config.LLM_MODEL,
                    system_instruction=system_prompt
                )
                response = model.generate_content(prompt)
                return response.text

            elif self.provider == "doubao":
                # 豆包用法（通过 Ark 的 OpenAI 兼容接口）
                # 注意：配置中的模型名称应为端点 ID（例如 ep-2024...）
                response = self.client.chat.completions.create(
                    model=config.LLM_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7
                )
                return response.choices[0].message.content

            else:
                # OpenAI 用法
                response = self.client.chat.completions.create(
                    model=config.LLM_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7
                )
                return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error calling LLM ({self.provider}): {e}")
            raise e
