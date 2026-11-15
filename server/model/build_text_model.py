import os

from .fake_text_model import FakeTextModel
from .openai_text_model import OpenAITextModel
from .text_model import TextModel


def build_text_model() -> TextModel:
    provider = os.getenv("TEXT_MODEL_PROVIDER", "fake").strip().lower()

    if provider == "fake":
        planning_fault = os.getenv("FAKE_PLANNING_FAULT", "none").strip().lower()
        storyboard_fault = os.getenv("FAKE_STORYBOARD_FAULT", "none").strip().lower()

        if planning_fault not in {"none", "characters", "scenes"}:
            raise ValueError(f"不支持的 FAKE_PLANNING_FAULT：{planning_fault}")

        if storyboard_fault not in {
            "none",
            "duplicate_id",
            "unknown_character",
            "duration_mismatch",
        }:
            raise ValueError(f"不支持的 FAKE_STORYBOARD_FAULT：{storyboard_fault}")

        return FakeTextModel(
            planning_fault=planning_fault, storyboard_fault=storyboard_fault
        )

    if provider in "openai":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        model = os.getenv("OPENAI_MODEL", "").strip()
        base_url = os.getenv("OPENAI_BASE_URL", "").strip() or None
        if not api_key or not model:
            raise RuntimeError(
                f"使用 {provider} 时必须配置 OPENAI_API_KEY 和 OPENAI_MODEL"
            )
        return OpenAITextModel(api_key=api_key, model=model, base_url=base_url)
    raise ValueError(f"不支持的 TEXT_MODEL_PROVIDER：{provider}")
