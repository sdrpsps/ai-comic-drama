from server.schema import RevisionRecord
from server.states import ComicDramaState

from .shot_fingerprint import shot_fingerprint


def initialize_revision(state: ComicDramaState) -> dict[str, object]:
    if "storyboard" not in state:
        raise ValueError("缺少分镜，不能初始化修订状态")

    limit = state.get("max_revisions", 2)

    if isinstance(limit, bool) or not isinstance(limit, int) or not 0 <= limit <= 3:
        raise ValueError("max_revisions 必须是 0～3 的整数")

    return {
        "max_revisions": limit,
        "automatic_revision_count": 0,
        "human_revision_count": 0,
        "review_result": None,
        "review_error": None,
        "approved_version": None,
        "previous_quality_report": None,
        "revision_count": 0,
        "revision_history": [
            RevisionRecord(
                version=0,
                fingerprint=shot_fingerprint(state["storyboard"]),
                source_codes=[],
                target_shot_ids=[],
            )
        ],
        "stop_reason": None,
        "events": ["已记录初版分镜与修订上限"],
    }
