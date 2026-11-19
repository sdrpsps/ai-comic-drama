from server.states import ComicDramaState


def storyboard_cancelled(state: ComicDramaState) -> dict[str, object]:
    return {
        "current_stage": "storyboard_cancelled",
        "stop_reason": "cancelled_by_user",
        "approved_version": None,
        "events": ["用户已取消作品"],
    }
