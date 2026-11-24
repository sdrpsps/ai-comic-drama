import operator
from typing import Annotated, NotRequired, TypedDict

from server.schema import (
    CharacterProfile,
    CreativeRequirement,
    RevisionRecord,
    SceneProfile,
    StoryBoard,
    StoryboardQualityReport,
    StoryboardReview,
    StoryboardValidation,
    StoryOutline,
)

from .asset_reducer import merge_assets


class ComicDramaState(TypedDict):
    """整张图"""

    # 用户最初的创意
    # 例如：深夜的办公室里，程序员小林正在修改一款漫画应用。零点到来时，他设计的漫画角色阿沐突然从屏幕中走了出来。
    raw_requirement: str

    # 结构化数据
    requirement: NotRequired[CreativeRequirement]

    # 故事大纲
    story_outline: NotRequired[StoryOutline]
    # 角色设定（对应的是一个list列表）
    characters: NotRequired[list[CharacterProfile]]
    # 场景设定（对应的是一个list列表）
    scenes: NotRequired[list[SceneProfile]]

    # 分镜（对应的是一个list列表）
    storyboard: NotRequired[list[StoryBoard]]
    # 硬规则对分镜评审后的结果
    storyboard_validation: NotRequired[StoryboardValidation]

    # 存储模型评审分镜后的结果
    quality_report: NotRequired[StoryboardQualityReport]
    # 存储的是上一次模型对分镜的评价
    previous_quality_report: NotRequired[dict | None]

    # 修订的次数
    revision_count: NotRequired[int]
    # 最大能够修订的次数
    max_revisions: NotRequired[int]
    # 修订的历史记录
    revision_history: NotRequired[list[RevisionRecord]]
    # 停止下一次修订的原因（修订过关了、超过最大修订次数了、修订回之前的版本了）
    stop_reason: NotRequired[str | None]

    # 重点需要理解 revision_count、automatic_revision_count、human_revision_count之间的区别
    automatic_revision_count: NotRequired[int]
    human_revision_count: NotRequired[int]
    # 存储人工审核的决定
    review_result: NotRequired[StoryboardReview | None]
    # 存储人工审核时抛出的错误信息
    review_error: NotRequired[str | None]
    # 通过的时候的版本号
    approved_version: NotRequired[int | None]

    # 项目id号，项目的唯一标识
    # 可以由用户传入，用户如果没有传入，我们来生成
    project_id: NotRequired[str]
    # 视觉快照，就是一个 VisualBible 转成的字典类型
    visual_bible: NotRequired[dict]
    # 视觉快照的指纹：做了一个hash计算取前面16位
    visual_digest: NotRequired[str]
    # 存储的是一个 Asset 转成的字典类型
    # 这里我们自己指定了一个 reducer：merge_assets
    assets: Annotated[dict[str, dict], merge_assets]
    # 最终生图的一个报告：成功了几张、失败了几张
    reference_report: NotRequired[dict]

    # 就是 ShotFrameTask 的字典形式
    frame_tasks: NotRequired[list[dict]]
    # 首次生成了首位帧之后，要做一个汇总报告，看有几张成功的，有几张失败的，用于决定是否要重做
    frame_report: NotRequired[dict]

    # 当前候选帧。键是 shot_id:start 或 shot_id:end，值是这一帧当前要审核的生图请求。
    # 存放的是 ImageGenerationRequest 的字典形式；历史版本仍留在 assets。
    # 用于记录是哪个分镜的哪一帧要进行生图，值对应的是一个 ImageGenerationRequest 的字典形式
    frame_index: NotRequired[dict[str, dict]]

    # 自动检查结果：各帧检查记录、失败项、是否完整、已耗尽重做次数的帧键。
    # failed 里每一项是 FrameRedoItem 的字典形式。
    frame_check: NotRequired[dict]

    # 画面审核轮次。每做一次画面检查加 1，并写进审核令牌。
    frame_review_round: NotRequired[int]

    # 存储 review_token 的
    frame_review_token: NotRequired[str]

    # 存储审核结果的
    frame_review_result: NotRequired[dict]

    # 存储上一次审核提交没有通过校验的原因
    frame_review_error: NotRequired[str | None]

    # 存储 command_id 的
    frame_command_ids: NotRequired[list[str]]

    # 还没变成生图计划的返工意见，来自自动检查失败或人工指定重做。
    # 每一项是 FrameRedoItem 的字典形式
    pending_frame_redos: NotRequired[list[dict]]

    # 已准备好、即将派发的单帧重做任务。每项含帧键、上一版 request_id。
    # request 存放的是 ImageGenerationRequest 的字典形式
    frame_redo_tasks: NotRequired[list[dict]]

    # 记录重做的次数
    frame_redo_counts: NotRequired[dict[str, int]]

    # 最终用户审核通过了的帧
    # 后续视频生成阶段，主要消费这里的数据
    approved_frames: NotRequired[dict[str, dict]]

    # 记录当前所处的阶段
    # 例：首次输入 "submitted"；分镜待审 "quality_passed"；成片待审 "final_video_ready"；验收通过 "final_video_approved"
    current_stage: str

    # 记录当前经过了哪些阶段
    # ["已接收用户创意", "已生成结构化创意需求", "已生成故事大纲",]
    events: Annotated[list[str], operator.add]
