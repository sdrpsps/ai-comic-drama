import base64

from server.schema import GeneratedImage, ImageGenerationRequest
from server.storage import AssetStore

from .image_generator import ImageGenerationError, prompt_digest

FAKE_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class FakeImageGenerator:
    """可预测替身：可稳定复现成功、限流和内容拒绝。"""

    def __init__(
        self,
        store: AssetStore,
        *,
        failure: str = "none",
        fail_owner_ids: frozenset[str] | None = None,
        fail_purposes: frozenset[str] | None = None,
    ) -> None:
        self.store = store
        self.failure = failure
        # None 表示所有对象；指定集合则只让这些 owner 失败。
        self.fail_owner_ids = fail_owner_ids
        self.generation_calls = 0
        self.fail_purposes = fail_purposes

    def generate(self, request: ImageGenerationRequest) -> GeneratedImage:
        for reference in request.reference_images:
            self.store.read_reference(reference)

        existing = self.store.load(request)
        if existing is not None:
            if existing.provider_model != "fake-image-v1":
                raise ValueError("request_id 已属于其他模型，请使用新 ID")
            return existing

        # 只有真正需要生成时才计数，用它证明幂等命中跳过了第二次调用。
        self.generation_calls += 1
        if (
            self.failure != "none"
            and (self.fail_owner_ids is None or request.owner_id in self.fail_owner_ids)
            and (self.fail_purposes is None or request.purpose in self.fail_purposes)
        ):
            messages = {
                "rate_limit": ("rate_limited", "Fake 图像服务限流"),
                "content_rejected": ("content_rejected", "Fake 内容安全拒绝"),
                "service_error": ("provider_unavailable", "Fake 图像服务异常"),
            }
            code, message = messages.get(
                self.failure, ("invalid_fake_mode", f"未知 Fake 模式：{self.failure}")
            )
            raise ImageGenerationError(code, message, request_id=request.request_id)

        return self.store.save(
            request,
            FAKE_PNG,
            provider_model="fake-image-v1",
            prompt_digest=prompt_digest(request),
            provider_request_id=f"fake_{request.request_id}",
        )
