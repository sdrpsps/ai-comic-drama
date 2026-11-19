from server.states import ComicDramaState


def revision_exhausted(state: ComicDramaState) -> dict[str, object]:
    if "max_revisions" not in state:
        raise ValueError("缺少最大修订次数配置，不能标记修订上限已达")
    return {
        "current_stage": "revision_exhausted",
        "stop_reason": "max_revisions_reached",
        "events": [f"已达到 {state['max_revisions']} 次修订上限"],
    }
