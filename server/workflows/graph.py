# 主图（父图）

from typing import Literal

from langgraph.graph import END, START, StateGraph

from server.model import TextModel, build_text_model
from server.nodes import (
    initialize_revision,
    make_revise_from_review,
    review_storyboard,
    storyboard_approved,
    storyboard_cancelled,
)
from server.states import ComicDramaState
from server.workflows.prepare_storyboard_review import (
    build_prepare_storyboard_review_graph,
)
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
    prepare_graph = build_prepare_storyboard_review_graph(text_model)

    # 第一个子图
    def story_planning(state: ComicDramaState) -> dict[str, object]:
        # 调用子图
        child_result = planning_graph.invoke(state)

        return {
            **child_result,
            "events": child_result["events"][len(state["events"]) :],
        }

    # 第二个子图
    def prepare_storyboard_review(state: ComicDramaState) -> dict[str, object]:
        # 调用子图
        child_result = prepare_graph.invoke(state)

        return {
            **child_result,
            "events": child_result["events"][len(state["events"]) :],
        }

    builder = StateGraph(ComicDramaState)

    # 加点
    builder.add_node("story_planning", story_planning)
    builder.add_node("initialize_revision", initialize_revision)
    builder.add_node("prepare_storyboard_review", prepare_storyboard_review)
    builder.add_node("review_storyboard", review_storyboard)
    builder.add_node("revise_from_review", make_revise_from_review(text_model))
    builder.add_node("storyboard_approved", storyboard_approved)
    builder.add_node("storyboard_cancelled", storyboard_cancelled)

    # 连边
    builder.add_edge(START, "story_planning")
    builder.add_edge("story_planning", "initialize_revision")
    builder.add_edge("initialize_revision", "prepare_storyboard_review")
    builder.add_edge("prepare_storyboard_review", "review_storyboard")

    # review_storyboard 由 Command 选择唯一业务路径，不再添加静态出口。
    builder.add_conditional_edges(
        "revise_from_review",
        lambda state: (
            "review_storyboard"
            if state["current_stage"] == "revision_stalled"
            else "prepare_storyboard_review"
        ),
        path_map=["review_storyboard", "prepare_storyboard_review"],
    )
    builder.add_edge("storyboard_approved", END)
    builder.add_edge("storyboard_cancelled", END)

    return builder.compile(checkpointer=checkpointer)


graph = build_graph(build_text_model())
