from openai import OpenAI

from server.prompts import SYSTEM_PROMPT
from server.schema import CreativeRequirement


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

    def analyze_requirement(self, raw_requirement: str) -> CreativeRequirement:
        completion = self._client.chat.completions.parse(
            model=self._model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": raw_requirement},
            ],
            response_format=CreativeRequirement,
        )
        requirement = completion.choices[0].message.parsed
        if requirement is None:
            raise ValueError("文本模型没有返回可解析的结构化需求")
        return requirement
