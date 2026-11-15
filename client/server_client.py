from langgraph_sdk import get_sync_client

SERVER_URL = "http://127.0.0.1:2024"
GRAPH_ID = "comic_drama"
IDEA = (
    "制作一部45秒的都市奇幻漫剧：程序员小林在深夜办公室，"
    "遇见从漫画中走出来的阿沐。全剧5个镜头，采用暖色二维漫画风格。"
)


def main() -> None:
    client = get_sync_client(url=SERVER_URL)
    assistants = client.assistants.search(graph_id=GRAPH_ID)

    if not assistants:
        raise RuntimeError(f"Agent Server 中没有找到 Graph：{GRAPH_ID}")
    assistant = assistants[0]

    thread = client.threads.create(metadata={"title": "零点之后"})
    run = client.runs.create(
        thread["thread_id"],
        assistant["assistant_id"],
        input={
            "raw_requirement": IDEA,
            "current_stage": "submitted",
            "events": [],
        },
    )

    result = client.runs.join(thread["thread_id"], run["run_id"])
    state = client.threads.get_state(thread["thread_id"])
    values = state["values"]
    if not isinstance(values, dict):
        raise TypeError("Thread 状态不是预期的对象")

    print(f"Graph ID：{assistant['graph_id']}")
    print(f"Assistant ID：{assistant['assistant_id']}")
    print(f"Thread ID：{thread['thread_id']}")
    print(f"Run ID：{run['run_id']}")
    print(f"Run 返回阶段：{result['current_stage']}")
    print(f"Thread 保存阶段：{values['current_stage']}")
    print("事件：")
    for event in values["events"]:
        print(f"  - {event}")

    requirement = values["requirement"]
    print(
        f"需求：{requirement['title']} / "
        f"{requirement['duration_seconds']} 秒 / "
        f"{requirement['shot_count']} 镜"
    )
    print(f"故事主题：{values['story_outline']['theme']}")
    print(f"角色数：{len(values['characters'])}")
    print(f"场景数：{len(values['scenes'])}")
    print(f"分镜数：{len(values['storyboard'])}")
    print(f"分镜校验通过：{values['storyboard_validation']['is_valid']}")


# 用 python client/server_client.py 直接运行时，才会进入 main()。
# 被其他模块 import 时不会自动发请求。
if __name__ == "__main__":
    main()
