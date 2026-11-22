from server.prompts import visual_digest
from server.states import ComicDramaState

from .visual_bible import _bible


def make_prepare_visual_bible(generation_profile: str):

    def prepare_visual_bible(state: ComicDramaState) -> dict:

        # 先对工作流当前的阶段做一个判断
        if state["current_stage"] != "storyboard_approved":
            raise ValueError("只有分镜审核通过后才能准备参考素材")

        # bibel 会得到一个 VisualBibal 类型的数据（视觉快照）
        bible = _bible(state, generation_profile)
        # 针对该视觉快照做一个指纹
        digest = visual_digest(bible)

        # 防御性代码
        # 第一次是不会进来的
        existing_visual_bible = state.get("visual_bible")
        if existing_visual_bible is not None and (
            existing_visual_bible != bible.model_dump(mode="json")
            or state.get("visual_digest") != digest
        ):
            raise ValueError("冻结视觉设定已变化，请检查上游，不能静默重用旧素材")

        # 如果代码来到这里，就正常将当前得到的视觉快照以及视觉快照的指纹存储图的状态里面
        return {
            "visual_bible": bible.model_dump(
                mode="json"
            ),  # 存储视觉快照（注意，不是直接存的 VisualBibal 类型，而是转成了 json 类型）
            "visual_digest": digest,
            "current_stage": "reference_assets_generating",
            "events": ["已冻结审核版视觉设定"],
        }

    return prepare_visual_bible
