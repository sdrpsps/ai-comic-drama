from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class QualityIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    code: Literal[
        "hard_rule",  # 分镜没通过 Python 硬规则。镜头数量、shot_id、顺序、时长、角色或场景引用这类问题走这里。它由 hard_rules_failed 写入，模型评价不会产出这个码。
        "plot_gap",  # 故事因果或镜头衔接断了。例如核心动作没交代、前后镜头对不上、动作在该镜头的秒数里讲不清。
        "character_inconsistent",  # 角色、场景或关键道具前后不一致。例如同一角色外观或服装变了，道具的来源、数量、持有者互相矛盾。
        "visual_unclear",  # 画面描述不够，首帧或尾帧无法据此生成。核心人物、道具或空间关系缺失，导致画面表达不明确。
        "motion_conflict",  # 镜头里的动作和摄影机运动互相矛盾。例如同一镜头既要求固定机位，又要求摄影机跟拍。
    ]
    severity: Literal["error", "warning"]
    shot_id: str | None = Field(default=None, pattern=r"^shot_[a-z0-9_]+$")
    description: str = Field(min_length=1)
    suggestion: str = Field(min_length=1)


class StoryboardQualityReport(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    is_passed: bool
    summary: str = Field(min_length=1)
    issues: list[QualityIssue]
    affected_shot_ids: list[str]

    @model_validator(mode="after")
    def check_consistency(self):
        blocking = any(issue.severity == "error" for issue in self.issues)
        if self.is_passed == blocking:
            raise ValueError("is_passed 必须与 error 级问题一致")
        expected = {issue.shot_id for issue in self.issues if issue.shot_id}
        if set(self.affected_shot_ids) != expected or len(
            self.affected_shot_ids
        ) != len(expected):
            raise ValueError("affected_shot_ids 必须与问题中的 shot_id 一致且不重复")
        return self


class ModelQualityReport(BaseModel):
    """模型只生成问题事实，正式通过判断由 Python 推导。"""

    """在让 AI 生成内容的时候，只让 AI 生成无法通过规则确定的内容，凡是能够通过规则确定的内容，都应该通过编码来得到。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    summary: str = Field(min_length=1)
    issues: list[QualityIssue]

    def to_report(self) -> StoryboardQualityReport:
        return StoryboardQualityReport(
            is_passed=not any(i.severity == "error" for i in self.issues),
            summary=self.summary,
            issues=self.issues,
            affected_shot_ids=sorted({i.shot_id for i in self.issues if i.shot_id}),
        )
