import hashlib
from typing import Protocol

from server.schema import GeneratedImage, ImageGenerationRequest


class ImageGenerationError(RuntimeError):
    """稳定错误类型：工作流不需要分析不同平台的异常文本。"""

    def __init__(self, code: str, message: str, *, request_id: str) -> None:
        super().__init__(message)
        self.code = code
        self.request_id = request_id


class ImageGenerator(Protocol):
    def generate(self, request: ImageGenerationRequest) -> GeneratedImage:
        """生成并持久化一张图，返回项目自己的结果对象。"""
        ...


def prompt_digest(request: ImageGenerationRequest) -> str:
    payload = f"{request.prompt}\n{request.negative_prompt}".encode()
    return hashlib.sha256(payload).hexdigest()[:16]
