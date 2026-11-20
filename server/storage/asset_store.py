"""图片落盘边界：受控路径、原子写入和持久化元数据。"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from server.schema import GeneratedImage, ImageGenerationRequest


class AssetStore:
    def __init__(self, project_root: Path, output_dir: str = "outputs") -> None:
        """初始化项目根目录和素材输出目录，并检查输出目录是否越界。
        project_root : 项目的路径
        output_dir : 素材（图片、视频）的输出目录
        """

        # 这两行先把路径算死
        # resolve() 会把 .、.. 和符号链接展开成绝对路径
        self.project_root = project_root.resolve()
        self.output_root = (self.project_root / output_dir).resolve()

        # 防御性的代码
        # output_dir 必须要在 project_root 下面
        if not self.output_root.is_relative_to(self.project_root):
            raise ValueError("output_dir 不能越过项目根目录")

    def _stem(self, request: ImageGenerationRequest) -> Path:
        """根据用途、对象 ID、版本和请求 ID，构造不带后缀的素材路径。
        就是构造素材（图片、json）的路径
        一定要注意，这里不会涉及到具体的后缀
        """
        stem = (
            self.output_root
            / "images"
            / request.purpose
            / request.owner_id
            / f"v{request.version}"
            / request.request_id
        ).resolve()

        if not stem.is_relative_to(self.output_root):
            raise ValueError("素材路径越过 outputs 目录")

        # 对外返回构造的这个路径（不含后缀）
        return stem

    def load(self, request: ImageGenerationRequest) -> GeneratedImage | None:
        """读取并检查已有图片和元数据；检查通过则返回可复用的图片信息。"""

        # 获取元数据信息
        metadata_path = self._stem(request).with_suffix(".json")

        # 防御性代码
        if not metadata_path.is_file():
            if any(
                self._stem(request).with_suffix(suffix).exists()
                for suffix in (".png", ".jpg", ".webp")
            ):
                raise ValueError("已有图片但缺少元数据，请先人工检查，不自动重复生成")
            return None

        try:
            # 读出同名 JSON，并按 GeneratedImage 校验字段；格式不对会在下面被收成复用失败。
            image = GeneratedImage.model_validate_json(metadata_path.read_text())

            # 中间做了很多防御性措施
            local_path = (self.project_root / image.local_path).resolve()

            if not local_path.is_relative_to(self.output_root):
                raise ValueError("元数据中的图片路径越界")

            if not local_path.is_file() or not self._looks_like_image(
                local_path.read_bytes()
            ):
                raise ValueError("已有素材文件缺失或损坏")

            if (
                image.request_id != request.request_id
                or image.owner_id != request.owner_id
                or image.version != request.version
                or image.purpose != request.purpose
                or image.request_digest != self._request_digest(request)
            ):
                raise ValueError("同一 request_id 不能用于不同的图像请求")

            return image.model_copy(update={"reused": True})
        except (OSError, ValueError) as exc:
            # 【重要】已有文件不可信时停下，不自动再付费生成。
            raise ValueError(f"无法安全复用已有素材：{exc}") from exc

    def save(
        self,
        request: ImageGenerationRequest,
        content: bytes,
        *,
        provider_model: str,
        prompt_digest: str,
        remote_url: str | None = None,
        provider_request_id: str | None = None,
    ) -> GeneratedImage:
        """保存图片及其 JSON 元数据，并返回图片信息。"""

        # 根据 content 内容来决定后缀
        suffix = self._detect_suffix(content)  # ".png"、".jpg"、".webp""

        # 拿路径
        stem = self._stem(request)

        # 创建目录
        stem.parent.mkdir(parents=True, exist_ok=True)

        # 图片的路径（包含了后缀）
        image_path = stem.with_suffix(suffix)

        # 元数据信息路径
        metadata_path = stem.with_suffix(".json")

        # 上面是落盘之前的准备工作，接下来开始写入（原子写入）

        # 这里是写入图片
        self._atomic_write(image_path, content)

        result = GeneratedImage(
            asset_id=f"asset_{request.request_id}",
            request_id=request.request_id,
            purpose=request.purpose,
            owner_id=request.owner_id,
            version=request.version,
            local_path=image_path.relative_to(self.project_root).as_posix(),
            remote_url=remote_url,
            provider_request_id=provider_request_id,
            provider_model=provider_model,
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            size=request.size,
            prompt_digest=prompt_digest,
            request_digest=self._request_digest(request),
        )

        # 写入json
        self._atomic_write(
            metadata_path,
            result.model_dump_json(indent=2).encode("utf-8"),
        )

        return result

    @staticmethod
    def _looks_like_image(content: bytes) -> bool:
        """检查内容是否具有 PNG、JPEG 或 WebP 的文件格式标记。"""
        return (
            # PNG、JPEG 任一文件头匹配即可；startswith 支持传入前缀元组。
            content.startswith((b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff"))
            # WebP 还必须同时满足 RIFF 文件头与第 8～11 字节的 WEBP 标记。
            or (content.startswith(b"RIFF") and content[8:12] == b"WEBP")
        )

    @staticmethod
    def _request_digest(request: ImageGenerationRequest) -> str:
        """根据完整的图片生成请求计算摘要，用于检查请求是否一致。"""
        return hashlib.sha256(request.model_dump_json().encode("utf-8")).hexdigest()[
            :16
        ]

    @staticmethod
    def _detect_suffix(content: bytes) -> str:
        """根据图片内容判断格式，返回对应的文件后缀。"""
        if content.startswith(b"\x89PNG\r\n\x1a\n"):
            return ".png"

        if content.startswith(b"\xff\xd8\xff"):
            return ".jpg"

        if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
            return ".webp"

        raise ValueError("下载结果不是受支持的 PNG、JPEG 或 WebP 图片")

    @staticmethod
    def _atomic_write(target: Path, content: bytes) -> None:
        temporary: str | None = None
        try:
            with NamedTemporaryFile(dir=target.parent, delete=False) as file:
                temporary = file.name
                file.write(content)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary, target)  # 一次性替换
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)
