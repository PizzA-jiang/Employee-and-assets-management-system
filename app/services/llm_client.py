"""LLM client supporting local model endpoints and MiMo API (OpenAI-compatible)."""
import json
import logging
from typing import List, Optional, Dict, Any
import requests
from requests.exceptions import Timeout, ConnectionError, RequestException

logger = logging.getLogger(__name__)


class LLMError(Exception):
    pass


class LLMTimeoutError(LLMError):
    pass


class LLMClient:
    def __init__(self):
        self._local_endpoint: str = ""
        self._local_enabled: bool = False
        self._api_key: str = ""
        self._base_url: str = "https://api.xiaomimimo.com/v1"
        self._model: str = "mimo-v2.5-pro"
        self._timeout: int = 30
        self._local_available: Optional[bool] = None

    def configure(
        self,
        local_endpoint: str = "",
        local_enabled: bool = True,
        api_key: str = "",
        base_url: str = "",
        model: str = "",
        timeout: int = 30,
    ):
        self._local_endpoint = local_endpoint
        self._local_enabled = local_enabled
        self._api_key = api_key
        if base_url:
            self._base_url = base_url
        if model:
            self._model = model
        self._timeout = timeout
        self._local_available = None

    def _check_local_available(self) -> bool:
        if not self._local_enabled or not self._local_endpoint:
            return False
        try:
            url = self._local_endpoint.rsplit("/", 1)[0] + "/models"
            resp = requests.get(url, timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    @property
    def active_endpoint(self) -> str:
        if self._local_available is None:
            self._local_available = self._check_local_available()
        if self._local_available:
            return self._local_endpoint
        return f"{self._base_url}/chat/completions"

    @property
    def active_model(self) -> str:
        if self._local_available:
            return "local"
        return self._model

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[dict]] = None,
        timeout: Optional[int] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        effective_timeout = timeout or self._timeout
        payload: Dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {"Content-Type": "application/json"}
        if self._api_key and not self._local_available:
            headers["Authorization"] = f"Bearer {self._api_key}"

        url = self.active_endpoint
        try:
            resp = requests.post(
                url, json=payload, headers=headers, timeout=effective_timeout
            )
            resp.raise_for_status()
            return resp.json()
        except Timeout:
            logger.error(f"LLM timeout after {effective_timeout}s: {url}")
            raise LLMTimeoutError(f"LLM调用超时 ({effective_timeout}s)")
        except ConnectionError:
            logger.error(f"LLM connection failed: {url}")
            if self._local_available:
                self._local_available = False
                logger.info("Local LLM unavailable, falling back to API")
                return self.chat(messages, tools, timeout, temperature, max_tokens)
            raise LLMError("无法连接到AI服务")
        except RequestException as e:
            status = getattr(e.response, "status_code", None) if hasattr(e, "response") else None
            logger.error(f"LLM request failed [{status}]: {e}")
            if status == 401:
                raise LLMError("API Key无效或已过期")
            if status == 429:
                raise LLMError("API调用频率超限，请稍后重试")
            raise LLMError(f"AI服务调用失败: {str(e)}")

    def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[dict]] = None,
        timeout: Optional[int] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        effective_timeout = timeout or self._timeout
        payload: Dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {"Content-Type": "application/json"}
        if self._api_key and not self._local_available:
            headers["Authorization"] = f"Bearer {self._api_key}"

        url = self.active_endpoint
        try:
            resp = requests.post(
                url, json=payload, headers=headers, timeout=effective_timeout, stream=True
            )
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                decoded = line.decode("utf-8")
                if decoded.startswith("data: "):
                    data_str = decoded[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        yield chunk
                    except json.JSONDecodeError:
                        continue
        except Timeout:
            logger.error(f"LLM stream timeout after {effective_timeout}s: {url}")
            raise LLMTimeoutError(f"LLM流式调用超时 ({effective_timeout}s)")
        except ConnectionError:
            logger.error(f"LLM stream connection failed: {url}")
            if self._local_available:
                self._local_available = False
                yield from self.chat_stream(messages, tools, timeout, temperature, max_tokens)
                return
            raise LLMError("无法连接到AI服务")
        except RequestException as e:
            status = getattr(e.response, "status_code", None) if hasattr(e, "response") else None
            logger.error(f"LLM stream request failed [{status}]: {e}")
            if status == 401:
                raise LLMError("API Key无效或已过期")
            if status == 429:
                raise LLMError("API调用频率超限，请稍后重试")
            raise LLMError(f"AI服务调用失败: {str(e)}")


llm_client = LLMClient()
