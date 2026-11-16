from server.model import TextModel
from server.schema import StoryboardQualityReport
from server.states import ComicDramaState


def make_evaluate_storyboard_quality(text_model: TextModel):
    def evaluate_storyboard_quality(state: ComicDramaState) -> dict[str, object]:
        validation = state.get("storyboard_validation")
        if validation is None:
            raise ValueError("缺少分镜验证结果，不能调用语义评价")
        if not validation.is_valid:
            raise ValueError("硬规则未通过，不能调用语义评价")
        if (
            "requirement" not in state
            or "story_outline" not in state
            or "characters" not in state
            or "scenes" not in state
            or "storyboard" not in state
        ):
            raise ValueError("缺少需求、大纲、角色、场景或分镜，不能调用语义评价")

        previous_report = state.get("previous_quality_report")
        report = text_model.evaluate_storyboard_quality(
            state["requirement"],
            state["story_outline"],
            state["characters"],
            state["scenes"],
            state["storyboard"],
            previous_report=(
                StoryboardQualityReport.model_validate(previous_report)
                if previous_report is not None
                else None
            ),
        )
        # 协议实现也可能绕过 Pydantic；在 State 写入前再次校验。
        report = StoryboardQualityReport.model_validate(report)
        known_ids = {shot.shot_id for shot in state["storyboard"]}
        referenced = set(report.affected_shot_ids) | {
            issue.shot_id for issue in report.issues if issue.shot_id
        }
        unknown = referenced - known_ids
        if unknown:
            raise ValueError(f"质量报告引用了未知分镜：{sorted(unknown)}")
        return {"quality_report": report, "events": ["已完成分镜语义质量评价"]}

    return evaluate_storyboard_quality
