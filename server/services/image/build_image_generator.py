from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path

from server.storage import AssetStore

from .fake_image_generator import FakeImageGenerator
from .image_generator import ImageGenerator
from .openai_image_generator import OpenAIImageGenerator


@dataclass(frozen=True)
class ImageRuntimeConfig:
    """这次出图的运行配置。读出来之后字段不能再改。"""

    provider: str
    model: str
    timeout_seconds: float
    project_root: Path

    @classmethod
    def from_env(cls) -> ImageRuntimeConfig:
        return cls(
            provider=os.getenv("IMAGE_MODEL_PROVIDER", "fake").strip().lower(),
            model=os.getenv("ARK_IMAGE_MODEL", "").strip(),
            timeout_seconds=float(os.getenv("IMAGE_TIMEOUT_SECONDS", "120")),
            project_root=Path(__file__).resolve().parents[3],
        )


def build_image_generator_from_env() -> ImageGenerator:
    config = ImageRuntimeConfig.from_env()
    if not math.isfinite(config.timeout_seconds) or config.timeout_seconds <= 0:
        raise ValueError("IMAGE_TIMEOUT_SECONDS 必须是有限正数")
    store = AssetStore(project_root=config.project_root)
    if config.provider == "fake":
        owners = os.getenv("FAKE_IMAGE_FAIL_OWNER_IDS", "").strip()
        purposes = os.getenv("FAKE_IMAGE_FAIL_PURPOSES", "").strip()
        return FakeImageGenerator(
            store,
            failure=os.getenv("FAKE_IMAGE_FAILURE", "none").strip().lower(),
            fail_owner_ids=frozenset(x.strip() for x in owners.split(",") if x.strip())
            if owners
            else None,
            fail_purposes=frozenset(x.strip() for x in purposes.split(",") if x.strip())
            if purposes
            else None,
        )
    if config.provider != "openai":
        raise ValueError("IMAGE_MODEL_PROVIDER 只能是 fake 或 openai")

    ark_api_key = os.getenv("ARK_API_KEY", "").strip()
    if ark_api_key:
        ark_base_url = os.getenv("ARK_BASE_URL", "").strip()
        if not ark_base_url:
            raise ValueError("配置 ARK_API_KEY 时必须同时配置 ARK_BASE_URL")
        return OpenAIImageGenerator(
            store,
            api_key=ark_api_key,
            model=config.model,
            base_url=ark_base_url,
            timeout_seconds=config.timeout_seconds,
        )

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    base_url = os.getenv("OPENAI_BASE_URL", "").strip()
    if not api_key or not base_url:
        raise ValueError(
            "使用 openai 时必须同时配置 ARK_API_KEY 和 ARK_BASE_URL，"
            "或同时配置 OPENAI_API_KEY 和 OPENAI_BASE_URL"
        )
    return OpenAIImageGenerator(
        store,
        api_key=api_key,
        model=config.model,
        base_url=base_url,
        timeout_seconds=config.timeout_seconds,
    )
