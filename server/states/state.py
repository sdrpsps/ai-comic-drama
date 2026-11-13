import operator
from typing import Annotated, TypedDict


class ComicDramaState(TypedDict):
    """整张图状态"""

    # 用户最初的创意
    # 用户最初输入的创意。后续需求整理节点会以它为起点。
    raw_requirement: str

    # 当前所处的阶段
    # 例：首次输入 "submitted"；分镜待审 "quality_passed"；成片待审 "final_video_ready"；验收通过 "final_video_approved"
    current_stage: str

    # 各节点只返回本节点新增的字符串。operator.add 追加到历史，避免后写覆盖先写。
    # 例：["已接收用户创意", "已生成结构化创意需求", "已生成故事大纲", "已收到人工审核命令：revise", "已按人工意见生成 v1 分镜"]
    events: Annotated[list[str], operator.add]
