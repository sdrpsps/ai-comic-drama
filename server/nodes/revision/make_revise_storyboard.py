from server.model import TextModel
from server.schema import RevisionRecord, StoryBoard
from server.states import ComicDramaState

from .shot_fingerprint import shot_fingerprint


def make_revise_storyboard(text_model: TextModel):
    def revise_storyboard(state: ComicDramaState) -> dict[str, object]:
        report = state.get("quality_report")

        if report is None or report.is_passed or not report.issues:
            raise ValueError("没有可执行的质量问题，不能修订")

        if (
            "revision_count" not in state
            or "max_revisions" not in state
            or "storyboard" not in state
            or "requirement" not in state
            or "story_outline" not in state
            or "characters" not in state
            or "scenes" not in state
            or "revision_history" not in state
        ):
            raise ValueError("缺少修订所需的分镜、设定或修订状态，不能自动修订")

        if (
            state.get("automatic_revision_count", state["revision_count"])
            >= state["max_revisions"]
        ):
            raise ValueError("修订次数已达上限")

        old_shots = state["storyboard"]
        requirement = state["requirement"]
        candidate = [
            StoryBoard.model_validate(shot)
            for shot in text_model.revise_storyboard(
                requirement,
                state["story_outline"],
                state["characters"],
                state["scenes"],
                old_shots,
                report,
                revision_count=state["revision_count"],
            )
        ]

        old_by_order = {shot.order: shot for shot in old_shots}
        new_by_order = {shot.order: shot for shot in candidate}
        old_ids = [shot.shot_id for shot in old_shots]
        targets = set(report.affected_shot_ids)

        if len(candidate) != requirement.shot_count:
            raise ValueError("修订不得改变镜头数量")

        if (
            sum(shot.duration_seconds for shot in candidate)
            != requirement.duration_seconds
        ):
            raise ValueError("修订不得改变目标总时长")

        if new_by_order.keys() != old_by_order.keys():
            raise ValueError("修订不得改变镜头顺序号")

        if (
            len(set(old_ids)) == len(old_ids)
            and [s.shot_id for s in candidate] != old_ids
        ):
            raise ValueError("已有唯一 shot_id 必须保持稳定")

        if targets and any(
            old_by_order[order] != shot and old_by_order[order].shot_id not in targets
            for order, shot in new_by_order.items()
        ):
            raise ValueError("修订改动了报告未指出的镜头")

        signature = shot_fingerprint(candidate)
        history = state["revision_history"]
        if signature in {record.fingerprint for record in history}:
            reason = (
                "no_change"
                if signature == shot_fingerprint(old_shots)
                else "repeated_version"
            )
            return {
                "stop_reason": reason,
                "current_stage": "revision_stalled",
                "events": ["修订没有产生新版本，工作流停止"],
            }

        next_version = state["revision_count"] + 1
        return {
            "storyboard": candidate,
            "quality_report": None,
            "previous_quality_report": report.model_dump(mode="json"),
            "storyboard_validation": None,
            "revision_count": next_version,
            "automatic_revision_count": state.get(
                "automatic_revision_count", state["revision_count"]
            )
            + 1,
            "approved_version": None,
            "revision_history": [
                *history,
                RevisionRecord(
                    version=next_version,
                    fingerprint=signature,
                    source_codes=sorted({issue.code for issue in report.issues}),
                    target_shot_ids=sorted(targets),
                ),
            ],
            "stop_reason": None,
            "current_stage": "storyboard_revised",
            "events": [f"已生成第 {next_version} 版修订分镜，等待重新校验"],
        }

    return revise_storyboard
