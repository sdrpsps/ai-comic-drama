import json
from typing import Any

from openai import OpenAI

from server.prompts import CHARACTER_PROMPT, SCENE_PROMPT, STORY_PROMPT, SYSTEM_PROMPT
from server.schema import (
    CharacterList,
    CharacterProfile,
    CreativeRequirement,
    SceneList,
    SceneProfile,
    StoryOutline,
)


class OpenAITextModel:
    """OpenAI 兼容接口结构化输出适配器。"""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str | None = None,
    ) -> None:
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def _parse(self, *, system: str, payload: dict[str, Any], schema: type[Any]) -> Any:
        """调用模型输出结构化回复。"""
        completion = self._client.beta.chat.completions.parse(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            response_format=schema,
        )
        parsed = completion.choices[0].message.parsed
        if parsed is None:
            raise ValueError("文本模型没有返回可解析的策划结果")
        return parsed

    def analyze_requirement(self, raw_requirement: str) -> CreativeRequirement:
        return self._parse(
            system=SYSTEM_PROMPT,
            payload={"raw_requirement": raw_requirement},
            schema=CreativeRequirement,
        )

    def generate_story_outline(self, requirement: CreativeRequirement) -> StoryOutline:
        return self._parse(
            system=STORY_PROMPT,
            payload={"requirement": requirement.model_dump(mode="json")},
            schema=StoryOutline,
        )

    def generate_characters(
        self, requirement: CreativeRequirement, outline: StoryOutline
    ) -> list[CharacterProfile]:
        result = self._parse(
            system=CHARACTER_PROMPT,
            payload={
                "requirement": requirement.model_dump(mode="json"),
                "story_outline": outline.model_dump(mode="json"),
            },
            schema=CharacterList,
        )
        return result.characters

    def generate_scenes(
        self, requirement: CreativeRequirement, outline: StoryOutline
    ) -> list[SceneProfile]:
        result = self._parse(
            system=SCENE_PROMPT,
            payload={
                "requirement": requirement.model_dump(mode="json"),
                "story_outline": outline.model_dump(mode="json"),
            },
            schema=SceneList,
        )
        return result.scenes
