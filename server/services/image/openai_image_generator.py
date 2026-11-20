from __future__ import annotations

from base64 import b64decode
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
)

from server.schema import GeneratedImage, ImageGenerationRequest
from server.storage import AssetStore

from .image_generator import ImageGenerationError, prompt_digest

_MAX_IMAGE_BYTES = 20 * 1024 * 1024


class OpenAIImageGenerator:
    """通过 OpenAI SDK 调用火山方舟图像模型。"""

    def __init__(
        self,
        store: AssetStore,
        *,
        api_key: str,
        model: str,
        base_url: str,
        timeout_seconds: float = 120.0,
        client: OpenAI | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("缺少图像服务 API Key")
        if not model:
            raise ValueError("缺少 ARK_IMAGE_MODEL")
        self.store = store
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.client = client or OpenAI(api_key=api_key, base_url=base_url, max_retries=0)

    def generate(self, request: ImageGenerationRequest) -> GeneratedImage:
        existing = self.store.load(request)
        if existing is not None:
            if existing.provider_model != self.model:
                raise ValueError("request_id 已属于其他模型，请使用新 ID")
            return existing

        try:
            provider_prompt = request.prompt
            if request.negative_prompt:
                provider_prompt += f"\n请避免：{request.negative_prompt}"
            response = self.client.images.generate(
                model=self.model,
                prompt=provider_prompt,
                size=request.size,
                response_format="url",
                extra_body={
                    "watermark": False,
                    "sequential_image_generation": "disabled",
                },
                timeout=self.timeout_seconds,
            )
        except AuthenticationError as exc:
            raise self._error("authentication_failed", request) from exc
        except PermissionDeniedError as exc:
            raise self._error("permission_denied", request) from exc
        except RateLimitError as exc:
            raise self._error("rate_limited", request) from exc
        except BadRequestError as exc:
            raise self._error("request_rejected", request) from exc
        except APITimeoutError as exc:
            raise self._error("generation_timeout", request) from exc
        except APIConnectionError as exc:
            raise self._error("provider_unavailable", request) from exc
        except APIStatusError as exc:
            raise self._error("provider_error", request) from exc

        image = response.data[0] if response.data else None
        remote_url = image.url if image else None
        if remote_url:
            content = self._download(remote_url, request)
        elif image and image.b64_json:
            try:
                content = b64decode(image.b64_json, validate=True)
            except ValueError as exc:
                raise ImageGenerationError(
                    "invalid_image_data",
                    "图像服务返回的 Base64 图片数据无效",
                    request_id=request.request_id,
                ) from exc
        else:
            raise ImageGenerationError(
                "invalid_response",
                "图像服务未返回图片 URL 或 Base64 图片数据",
                request_id=request.request_id,
            )
        if len(content) > _MAX_IMAGE_BYTES:
            raise ImageGenerationError(
                "image_too_large",
                "生成图片超过 20 MiB 上限",
                request_id=request.request_id,
            )
        try:
            return self.store.save(
                request,
                content,
                provider_model=self.model,
                prompt_digest=prompt_digest(request),
                remote_url=remote_url,
            )
        except (OSError, ValueError) as exc:
            raise ImageGenerationError(
                "invalid_image_data",
                "图片内容或落盘结果无效",
                request_id=request.request_id,
            ) from exc

    def _download(self, remote_url: str, request: ImageGenerationRequest) -> bytes:
        parsed = urlparse(remote_url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ImageGenerationError(
                "invalid_image_url",
                "平台返回的图片地址不是有效 HTTPS URL",
                request_id=request.request_id,
            )
        try:
            http_request = Request(
                remote_url, headers={"User-Agent": "ai-comic-drama/0.1"}
            )
            with urlopen(http_request, timeout=self.timeout_seconds) as response:
                # 限制单张图下载上限，避免异常响应占满内存。
                return response.read(_MAX_IMAGE_BYTES + 1)
        except OSError as exc:
            raise ImageGenerationError(
                "download_failed", "生成图片下载失败", request_id=request.request_id
            ) from exc

    @staticmethod
    def _error(code: str, request: ImageGenerationRequest) -> ImageGenerationError:
        # 不把密钥、请求头或平台完整响应混入业务错误。
        messages = {
            "authentication_failed": "图像服务鉴权失败",
            "permission_denied": "没有目标图像模型的调用权限",
            "rate_limited": "图像服务限流",
            "request_rejected": "图像请求被平台拒绝，请检查参数与内容",
            "generation_timeout": "图像生成请求超时，平台结果未知",
            "provider_unavailable": "无法连接图像服务",
            "provider_error": "图像服务返回错误",
        }
        return ImageGenerationError(code, messages[code], request_id=request.request_id)
