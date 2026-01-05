import os
from openai import OpenAI
from config.config import C
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
        provider_key = C.LLM_PROVIDER.lower() if C.LLM_PROVIDER else ""
        model_name = C.LLM_MODEL.lower()

        if provider_key == "google" or (not provider_key and "gemini" in model_name):
            self.provider = "google"
            from llm.google_provider import GoogleProvider
            try:
                self.client = GoogleProvider(C).get_llm_client()
            except Exception as e:
                logger.traceback_and_raise(
                    Exception(f"Failed to init Google Provider: {e}")
                )

        # Volcengine (豆包)
        elif provider_key in ["doubao", "volcengine"] or (not provider_key and ("doubao" in model_name or "ep-" in model_name)):
            self.provider = "doubao"
            from llm.volcengine_provider import VolcengineProvider
            try:
                self.client = VolcengineProvider(C).get_llm_client()
            except Exception as e:
                logger.traceback_and_raise(
                    Exception(f"Failed to init Volcengine Provider: {e}")
                )

        else:
            # 如果显式设置或未找到其他匹配项，则默认为 OpenAI
            self.provider = "openai"
            from llm.openai_provider import OpenAIProvider
            try:
                self.client = OpenAIProvider(C).get_llm_client()
            except Exception as e:
                logger.traceback_and_raise(
                    Exception(f"Failed to init OpenAI Provider: {e}")
                )

    def generate_text(self, prompt: str, system_prompt: str = "You are a helpful assistant.") -> str:
        if not self.client:
            raise ValueError(f"LLM Client ({self.provider}) not initialized. Check API Key.")

        try:
            if self.provider == "google":
                # Google GenAI 用法
                model = self.client.GenerativeModel(
                    model_name=C.LLM_MODEL, system_instruction=system_prompt
                )
                response = model.generate_content(prompt)
                return response.text

            elif self.provider == "doubao":
                # 豆包用法（通过 Ark 的 OpenAI 兼容接口）
                # 注意：配置中的模型名称应为端点 ID（例如 ep-2024...）
                response = self.client.chat.completions.create(
                    model=C.LLM_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.7,
                )
                return response.choices[0].message.content

            else:
                # OpenAI 用法
                response = self.client.chat.completions.create(
                    model=C.LLM_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.7,
                )
                return response.choices[0].message.content

        except Exception as e:
            logger.traceback_and_raise(
                Exception(f"Error calling LLM ({self.provider}): {e}")
            )
