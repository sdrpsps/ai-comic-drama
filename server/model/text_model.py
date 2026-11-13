from typing import Protocol

from server.schema.creative_requirement import CreativeRequirement


class TextModel(Protocol):
    def analyze_requirement(self, raw_requirement: str) -> CreativeRequirement:
        """把自然语言创意转换为经过校验的结构化需求。"""
        ...
