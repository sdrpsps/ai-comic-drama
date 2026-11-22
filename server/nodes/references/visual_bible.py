import hashlib

from server.prompts import visual_digest
from server.schema import (
    CharacterProfile,
    CreativeRequirement,
    SceneProfile,
    StoryBoard,
    VisualBible,
)
from server.states import ComicDramaState


# 接收两个参数：
# 1. 图的状态
# 2. generation_profile：这个仅仅是一个标识，由[模型厂商:模型]组成的一个字符串标识
# generation_profile = f"{config.provider}:{config.model if config.provider == 'ark' else 'fake-image-v1'}"
# "doubao:doubao-seedream-5-0-260128"
# 返回一个 VisualBible（视觉快照） 类型的数据
def _bible(state: ComicDramaState, generation_profile: str) -> VisualBible:

    # 先从图的状态里面获取人工审核的版本
    version = state.get("approved_version")

    if version is None or version != state.get("revision_count"):
        raise ValueError("批准版本与当前分镜版本不一致")

    if (
        "requirement" not in state
        or "characters" not in state
        or "scenes" not in state
        or "storyboard" not in state
    ):
        raise ValueError("缺少需求、角色、场景或分镜，不能生成视觉快照")

    # 从图的状态里面获取一些必要的信息
    requirement = CreativeRequirement.model_validate(state["requirement"])
    characters = tuple(CharacterProfile.model_validate(x) for x in state["characters"])
    scenes = tuple(SceneProfile.model_validate(x) for x in state["scenes"])
    char_ids = {x.character_id for x in characters}
    scene_ids = {x.scene_id for x in scenes}

    if (
        not characters
        or not scenes
        or len(char_ids) != len(characters)
        or len(scene_ids) != len(scenes)
    ):
        raise ValueError("角色和场景不能为空，ID 也不能重复")

    shots = [StoryBoard.model_validate(x) for x in state["storyboard"]]
    if not shots or any(
        x.scene_id not in scene_ids or not set(x.character_ids) <= char_ids
        for x in shots
    ):
        raise ValueError("分镜缺失或引用了未登记的角色/场景")

    # 生成 projectid
    default_id = (
        "project_" + hashlib.sha256(requirement.core_idea.encode()).hexdigest()[:12]
    )

    # 最终要返回一个 VisualBible 类型的数据
    return VisualBible(
        project_id=state.get("project_id", default_id),
        version=version,
        visual_style=requirement.visual_style,
        palette="统一低饱和暖色基础，环境局部颜色服从已登记场景",
        aspect_ratio=requirement.aspect_ratio,
        negative_prompt="文字标签、水印、额外人物、角色外观与固定服装漂移",
        characters=characters,
        scenes=scenes,
        generation_profile=generation_profile,
    )


# 这个方法所做的事情，就是将图状态里面所存的 visual_bible 还原成 VisualBible
def _checked_bible(state: ComicDramaState) -> VisualBible:
    if state["current_stage"] != "reference_assets_generating":
        raise ValueError("参考素材节点只能读取已准备好的生成阶段")

    if "visual_bible" not in state or "visual_digest" not in state:
        raise ValueError("缺少视觉快照或视觉指纹，不能读取参考素材配置")

    # 核心其实就是这一步：从图的状态里面拿到 visual_bible 字典值
    # 还原成 VisualBible 类型
    bible = VisualBible.model_validate(state["visual_bible"])

    if (
        bible != _bible(state, bible.generation_profile)
        or visual_digest(bible) != state["visual_digest"]
    ):
        raise ValueError("审核设定与视觉快照不一致")

    return bible
