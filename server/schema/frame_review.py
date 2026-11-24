"""画面审核决定和精确到单帧的返工意见。"""

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

FrameType = Literal["start", "end"]
FrameReviewAction = Literal["approve", "regenerate", "cancel"]


class FrameRedoItem(BaseModel):
    """精确到单帧的返工意见。reason 只记录原因，comment 才会追加到图片提示词"""

    """
    {
      "shot_id": "shot_03",
      "frame_type": "end",
      "reason": "服装与角色参考图不一致",
      "comment": "保持原有服装与辨识特征，保留既定动作和构图"
    }
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    shot_id: str = Field(pattern=r"^shot_[a-z0-9_]+$")
    frame_type: FrameType
    reason: str = Field(min_length=1, max_length=300)
    comment: str = Field(default="", max_length=500)


class FrameReview(BaseModel):
    """一轮画面审核决定。version 和 review_token 必须对应当前审核快照"""

    """
    {
      "command_id": "redo_shot_03_end_01",
      "action": "regenerate",
      "version": 0,
      "review_token": "e3b0c44298fc1c149afbf4c8996fb924....",
      "items": [
          {
              "shot_id": "shot_03",
              "frame_type": "end",
              "reason": "服装与角色参考图不一致",
              "comment": "保持原有服装与辨识特征，保留既定动作和构图"
          }
      ]
    }
    """

    """
    {
      "command_id": "approve_frames_01",
      "action": "approve",
      "version": 0,
      "review_token": "e3b0c44298fc1c149afbf4c8996fb92427ae4....",
      "items": []
    }
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    command_id: str | None = Field(default=None, pattern=r"^[a-z0-9_]{1,80}$")
    action: FrameReviewAction
    version: int = Field(ge=0)
    # 当前这一轮待审核画面的指纹，用来确认用户提交的决定
    review_token: str = Field(pattern=r"^[a-f0-9]{64}$")
    items: list[FrameRedoItem] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def check_items(self):
        if self.action == "regenerate" and not self.items:
            raise ValueError("重做必须指定至少一帧")
        if self.action != "regenerate" and self.items:
            raise ValueError("通过和取消不能携带重做项")
        if self.command_id is None:
            items = sorted(
                {
                    (item.shot_id, item.frame_type, item.reason, item.comment)
                    for item in self.items
                }
            )
            payload = {
                "review_token": self.review_token,
                "version": self.version,
                "action": self.action,
                "items": items,
            }
            encoded = json.dumps(
                payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")
            self.command_id = "review_" + hashlib.sha256(encoded).hexdigest()
        return self
