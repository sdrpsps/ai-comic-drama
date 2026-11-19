from typing import Literal

from server.states import ComicDramaState


def route_after_revision(
    state: ComicDramaState,
) -> Literal["validate_revised_storyboard", "revision_stalled"]:
    return (
        "revision_stalled"
        if state.get("stop_reason")
        else "validate_revised_storyboard"
    )
