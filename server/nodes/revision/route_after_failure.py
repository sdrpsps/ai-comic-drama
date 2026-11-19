from typing import Literal

from server.states import ComicDramaState


def route_after_failure(
    state: ComicDramaState,
) -> Literal["revise_storyboard", "revision_exhausted"]:
    if "revision_count" not in state or "max_revisions" not in state:
        raise ValueError("缺少修订次数或上限配置，不能路由")
    return (
        "revise_storyboard"
        if state.get("automatic_revision_count", state["revision_count"])
        < state["max_revisions"]
        else "revision_exhausted"
    )
