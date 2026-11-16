from langgraph.graph import END, START, StateGraph

from server.model import TextModel, build_text_model
from server.nodes import (
    hard_rules_failed,
    make_evaluate_storyboard_quality,
    quality_failed,
    quality_passed,
    route_quality,
)
from server.states import ComicDramaState
from server.workflows.story_planning import build_story_planning_graph


def build_graph(text_model: TextModel):
    planning_graph = build_story_planning_graph(text_model)

    def story_planning(state: ComicDramaState) -> dict[str, object]:
        child_result = planning_graph.invoke(state)
        # 子图返回完整事件历史；父图 reducer 只追加本轮新事件。
        return {
            **child_result,
            "events": child_result["events"][len(state["events"]) :],
        }

    builder = StateGraph(ComicDramaState)

    # 添加节点
    builder.add_node("story_planning", story_planning)
    builder.add_node("hard_rules_failed", hard_rules_failed)
    builder.add_node(
        "evaluate_storyboard_quality", make_evaluate_storyboard_quality(text_model)
    )
    builder.add_node("quality_passed", quality_passed)
    builder.add_node("quality_failed", quality_failed)

    # 连边
    builder.add_edge(START, "story_planning")
    builder.add_conditional_edges(
        "story_planning",
        lambda state: (
            "evaluate_storyboard_quality"
            if state["storyboard_validation"].is_valid
            else "hard_rules_failed"
        ),
        path_map=["evaluate_storyboard_quality", "hard_rules_failed"],
    )
    builder.add_conditional_edges("evaluate_storyboard_quality", route_quality)
    builder.add_edge("hard_rules_failed", END)
    builder.add_edge("quality_passed", END)
    builder.add_edge("quality_failed", END)

    return builder.compile()


graph = build_graph(build_text_model())
