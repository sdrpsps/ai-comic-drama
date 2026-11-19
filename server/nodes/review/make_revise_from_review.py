from server.model import TextModel
from server.nodes.revision import shot_fingerprint
from server.schema import (
    QualityIssue,
    RevisionRecord,
    StoryBoard,
    StoryboardQualityReport,
)
from server.states import ComicDramaState


def make_revise_from_review(text_model: TextModel):
    def revise_from_review(state: ComicDramaState) -> dict[str, object]:
        review = state.get("review_result")
        if review is None or review.action != "revise":
            raise ValueError("没有可执行的人工修订意见")
        if (
            "storyboard" not in state
            or "requirement" not in state
            or "story_outline" not in state
            or "characters" not in state
            or "scenes" not in state
            or "human_revision_count" not in state
            or "revision_history" not in state
            or "revision_count" not in state
        ):
            raise ValueError("缺少修订所需的分镜、设定或修订状态，不能执行人工修订")
        report = StoryboardQualityReport(
            is_passed=False,
            summary="用户退回分镜",
            issues=[
                QualityIssue(
                    code="visual_unclear",
                    severity="error",
                    shot_id=shot_id,
                    description=review.comment,
                    suggestion=review.comment,
                )
                for shot_id in review.shot_ids
            ],
            affected_shot_ids=review.shot_ids,
        )
        old = state["storyboard"]
        candidate = [
            StoryBoard.model_validate(item)
            for item in text_model.revise_storyboard(
                state["requirement"],
                state["story_outline"],
                state["characters"],
                state["scenes"],
                old,
                report,
                revision_count=state["human_revision_count"],
            )
        ]
        if len(candidate) != state["requirement"].shot_count:
            raise ValueError("人工修订不得改变镜头数量")
        if [s.shot_id for s in candidate] != [s.shot_id for s in old]:
            raise ValueError("人工修订必须保留全部稳定 shot_id 和排列")
        if [s.order for s in candidate] != [s.order for s in old]:
            raise ValueError("人工修订不得改变镜头顺序号")
        if (
            sum(s.duration_seconds for s in candidate)
            != state["requirement"].duration_seconds
        ):
            raise ValueError("人工修订不得改变目标总时长")
        if any(
            before != after and before.shot_id not in review.shot_ids
            for before, after in zip(old, candidate)
        ):
            raise ValueError("人工修订改动了未指定镜头")
        signature = shot_fingerprint(candidate)
        if signature in {record.fingerprint for record in state["revision_history"]}:
            return {
                "review_result": None,
                "approved_version": None,
                "current_stage": "revision_stalled",
                "stop_reason": "human_revision_no_new_version",
                "events": ["人工修订未产生新版本，返回人工审核"],
            }
        version = state["revision_count"] + 1
        previous = state.get("quality_report") or report
        return {
            "storyboard": candidate,
            "revision_count": version,
            "human_revision_count": state["human_revision_count"] + 1,
            "revision_history": [
                *state["revision_history"],
                RevisionRecord(
                    version=version,
                    fingerprint=signature,
                    source_codes=["human_review"],
                    target_shot_ids=review.shot_ids,
                ),
            ],
            "previous_quality_report": previous.model_dump(mode="json"),
            "quality_report": None,
            "storyboard_validation": None,
            "review_result": None,
            "approved_version": None,
            "stop_reason": None,
            "current_stage": "storyboard_revised_by_user",
            "events": [f"已按人工意见生成 v{version} 分镜，等待重新校验"],
        }

    return revise_from_review
