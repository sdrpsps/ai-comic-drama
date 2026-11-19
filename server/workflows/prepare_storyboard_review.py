# 一张子图，负责把当前分镜送到可以人工审核的状态

from typing import Literal

from langgraph.graph import END, START, StateGraph

from server.model import TextModel
from server.nodes import (
    hard_rules_failed,
    make_evaluate_storyboard_quality,
    make_revise_storyboard,
    quality_failed,
    quality_passed,
    revision_exhausted,
    revision_stalled,
    route_after_failure,
    route_after_revision,
    route_quality,
    validate_storyboard,
)
from server.states import ComicDramaState


def route_prepare_entry(
    state: ComicDramaState,
) -> Literal[
    "validate_revised_storyboard",
    "evaluate_storyboard_quality",
    "hard_rules_failed",
]:
    validation = state.get("storyboard_validation")
    if validation is None:
        return "validate_revised_storyboard"
    if validation.is_valid:
        return "evaluate_storyboard_quality"
    return "hard_rules_failed"


def route_validated_storyboard(
    state: ComicDramaState,
) -> Literal["evaluate_storyboard_quality", "hard_rules_failed"]:
    validation = state.get("storyboard_validation")
    if validation is None:
        raise ValueError("缺少分镜验证结果，不能路由")
    return "evaluate_storyboard_quality" if validation.is_valid else "hard_rules_failed"


def build_prepare_storyboard_review_graph(text_model: TextModel):
    builder = StateGraph(ComicDramaState)

    builder.add_node("hard_rules_failed", hard_rules_failed)
    builder.add_node(
        "evaluate_storyboard_quality", make_evaluate_storyboard_quality(text_model)
    )
    builder.add_node("quality_passed", quality_passed)
    builder.add_node("quality_failed", quality_failed)
    builder.add_node("revise_storyboard", make_revise_storyboard(text_model))
    builder.add_node("validate_revised_storyboard", validate_storyboard)
    builder.add_node("revision_exhausted", revision_exhausted)
    builder.add_node("revision_stalled", revision_stalled)

    builder.add_conditional_edges(START, route_prepare_entry)
    builder.add_conditional_edges("hard_rules_failed", route_after_failure)
    builder.add_conditional_edges("evaluate_storyboard_quality", route_quality)
    builder.add_edge("quality_passed", END)
    builder.add_conditional_edges("quality_failed", route_after_failure)
    builder.add_conditional_edges("revise_storyboard", route_after_revision)
    builder.add_conditional_edges(
        "validate_revised_storyboard", route_validated_storyboard
    )
    builder.add_edge("revision_exhausted", END)
    builder.add_edge("revision_stalled", END)

    return builder.compile()
