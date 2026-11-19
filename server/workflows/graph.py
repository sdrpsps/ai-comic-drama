# 主图（父图）

from typing import Literal

from langgraph.graph import END, START, StateGraph

from server.model import TextModel, build_text_model
from server.nodes import (
    hard_rules_failed,
    initialize_revision,
    make_evaluate_storyboard_quality,
    make_revise_from_review,
    make_revise_storyboard,
    quality_failed,
    quality_passed,
    review_storyboard,
    revision_exhausted,
    revision_stalled,
    route_after_failure,
    route_after_revision,
    route_quality,
    storyboard_approved,
    storyboard_cancelled,
    validate_storyboard,
)
from server.states import ComicDramaState
from server.workflows.story_planning import build_story_planning_graph


def route_validation(
    state: ComicDramaState,
) -> Literal["evaluate_storyboard_quality", "hard_rules_failed"]:
    validation = state.get("storyboard_validation")
    if validation is None:
        raise ValueError("缺少分镜验证结果，不能路由")
    return "evaluate_storyboard_quality" if validation.is_valid else "hard_rules_failed"


def build_graph(text_model: TextModel, *, checkpointer=None):
    # 创建子图
    planning_graph = build_story_planning_graph(text_model)

    # 新增一个节点
    def story_planning(state: ComicDramaState) -> dict[str, object]:
        # 调用子图
        child_result = planning_graph.invoke(state)

        return {
            **child_result,
            "events": child_result["events"][len(state["events"]) :],
        }

    builder = StateGraph(ComicDramaState)

    # 加点
    builder.add_node("story_planning", story_planning)
    builder.add_node("hard_rules_failed", hard_rules_failed)
    builder.add_node("quality_passed", quality_passed)
    builder.add_node("quality_failed", quality_failed)
    builder.add_node(
        "evaluate_storyboard_quality", make_evaluate_storyboard_quality(text_model)
    )
    builder.add_node("revise_storyboard", make_revise_storyboard(text_model))
    builder.add_node("validate_revised_storyboard", validate_storyboard)
    builder.add_node("revision_exhausted", revision_exhausted)
    builder.add_node("revision_stalled", revision_stalled)
    builder.add_node("initialize_revision", initialize_revision)
    builder.add_node("review_storyboard", review_storyboard)
    builder.add_node("revise_from_review", make_revise_from_review(text_model))
    builder.add_node("storyboard_approved", storyboard_approved)
    builder.add_node("storyboard_cancelled", storyboard_cancelled)

    # 连边
    builder.add_edge(START, "story_planning")
    builder.add_edge("story_planning", "initialize_revision")
    builder.add_conditional_edges(
        "initialize_revision",
        route_validation,
        path_map=["evaluate_storyboard_quality", "hard_rules_failed"],
    )
    builder.add_conditional_edges(
        "hard_rules_failed", route_after_failure
    )  # 根据修订最大次数有没有超过来决定走哪一边
    builder.add_conditional_edges(
        "evaluate_storyboard_quality", route_quality
    )  # 看模型评审分镜有没有通过
    builder.add_edge("quality_passed", "review_storyboard")
    builder.add_conditional_edges(
        "quality_failed", route_after_failure
    )  # 根据修订最大次数有没有超过来决定走哪一边
    builder.add_conditional_edges("revise_storyboard", route_after_revision)
    builder.add_conditional_edges(
        "validate_revised_storyboard",
        route_validation,
        path_map=["evaluate_storyboard_quality", "hard_rules_failed"],
    )
    builder.add_edge("revision_exhausted", "review_storyboard")
    builder.add_edge("revision_stalled", "review_storyboard")
    # review_storyboard 由 Command 选择唯一业务路径，不再添加静态出口。
    builder.add_conditional_edges(
        "revise_from_review",
        lambda state: (
            "review_storyboard"
            if state["current_stage"] == "revision_stalled"
            else "validate_revised_storyboard"
        ),
        path_map=["review_storyboard", "validate_revised_storyboard"],
    )
    builder.add_edge("storyboard_approved", END)
    builder.add_edge("storyboard_cancelled", END)

    return builder.compile(checkpointer=checkpointer)


graph = build_graph(build_text_model())
