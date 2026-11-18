from typing import Literal

from server.states import ComicDramaState


def route_after_failure(
    state: ComicDramaState,
) -> Literal["revise_storyboard", "revision_exhausted"]:
    return (
        "revise_storyboard"
        if state["revision_count"] < state["max_revisions"]
        else "revision_exhausted"
    )
