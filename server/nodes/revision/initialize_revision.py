from server.schema import RevisionRecord
from server.states import ComicDramaState

from .shot_fingerprint import shot_fingerprint


def initialize_revision(state: ComicDramaState) -> dict[str, object]:

    limit = state.get("max_revisions", 2)

    if isinstance(limit, bool) or not isinstance(limit, int) or not 0 <= limit <= 3:
        raise ValueError("max_revisions 必须是 0～3 的整数")

    return {
        "max_revisions": limit,
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
