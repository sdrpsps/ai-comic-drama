from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StoryboardReview(BaseModel):
    """恢复审核时提交的决定，绑定用户实际看到的版本。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    action: Literal["approve", "revise", "cancel"]
    version: int = Field(ge=0, strict=True)
    comment: str = Field(default="", max_length=500)
    shot_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_action_fields(self):
        if self.action == "revise" and (not self.comment or not self.shot_ids):
            raise ValueError("退回修改必须填写意见和 shot_ids")
        if self.action != "revise" and self.shot_ids:
            raise ValueError("只有退回修改可以携带 shot_ids")
        if self.action == "cancel" and not self.comment:
            raise ValueError("取消作品必须填写原因")
        if len(self.shot_ids) != len(set(self.shot_ids)):
            raise ValueError("shot_ids 不能重复")
        return self
