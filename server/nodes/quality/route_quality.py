from typing import Literal

from server.states import ComicDramaState


def route_quality(
    state: ComicDramaState,
) -> Literal["quality_passed", "quality_failed"]:
    if "quality_report" not in state:
        raise ValueError("缺少质量报告")
    return "quality_passed" if state["quality_report"].is_passed else "quality_failed"
