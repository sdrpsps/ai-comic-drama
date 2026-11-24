"""首次首尾帧制作：准备镜头任务、动态派发、生成与汇总。"""

from typing import Literal, TypedDict

from langgraph.types import Send

from server.nodes.frames.helpers import FRAME_TYPES, load_reference
from server.nodes.references.visual_bible import _bible
from server.prompts.frame_prompts import frame_request
from server.prompts.reference_prompts import (
    character_reference_request,
    scene_reference_request,
    visual_digest,
)
from server.schema import (
    Asset,
    CreativeRequirement,
    ShotFrameTask,
    StoryBoard,
    VisualBible,
)
from server.services.image import ImageGenerationError, ImageGenerator
from server.states import ComicDramaState
from server.storage import AssetStore


class ShotFrameInput(TypedDict):
    # Send 的子任务输入只有 task，不是整个 ComicDramaState。
    task: dict


def route_after_references(
    state: ComicDramaState,
) -> Literal["prepare_shot_frames", "__end__"]:
    return (
        "prepare_shot_frames"
        if state["current_stage"] == "reference_assets_ready"
        else "__end__"
    )


def make_prepare_shot_frames(store: AssetStore, generation_profile: str):
    def prepare_shot_frames(state: ComicDramaState) -> dict:
        if state["current_stage"] != "reference_assets_ready":
            raise ValueError("参考素材尚未就绪，不能派发首尾帧")
        visual_bible = state.get("visual_bible")
        digest = state.get("visual_digest")
        storyboard = state.get("storyboard")
        requirement = state.get("requirement")
        if (
            visual_bible is None
            or digest is None
            or storyboard is None
            or requirement is None
        ):
            raise ValueError("缺少视觉快照、视觉指纹、需求或分镜，不能准备首尾帧")
        bible = VisualBible.model_validate(visual_bible)
        # 复用已有视觉快照校验，连同当前配置再次核对。
        if (
            bible != _bible(state, generation_profile)
            or visual_digest(bible) != digest
        ):
            raise ValueError("审核设定、视觉快照或生成配置已变化")
        shots = [StoryBoard.model_validate(x) for x in storyboard]
        ids = [x.shot_id for x in shots]
        orders = [x.order for x in shots]
        if (
            not 4 <= len(shots) <= 6
            or len(set(ids)) != len(ids)
            or sorted(orders) != list(range(1, len(shots) + 1))
        ):
            raise ValueError("镜头数量必须为 4～6，ID 唯一，order 连续")
        if len(shots) != CreativeRequirement.model_validate(requirement).shot_count:
            raise ValueError("镜头数量与审核需求不一致")
        characters = {x.character_id: x for x in bible.characters}
        scenes = {x.scene_id: x for x in bible.scenes}
        assets = state.get("assets", {})

        tasks = []
        for shot in sorted(shots, key=lambda x: x.order):
            if (
                shot.scene_id not in scenes
                or len(set(shot.character_ids)) != len(shot.character_ids)
                or not set(shot.character_ids) <= characters.keys()
            ):
                raise ValueError("分镜引用了未知或重复角色/未知场景")
            related = [characters[key] for key in shot.character_ids]
            scene = scenes[shot.scene_id]
            inputs = [
                load_reference(store, assets, character_reference_request(bible, x))
                for x in related
            ]
            inputs.append(
                load_reference(store, assets, scene_reference_request(bible, scene))
            )
            if len(inputs) > 8:
                raise ValueError("单镜头参考图超过上限 8 张")
            task = ShotFrameTask(
                project_id=bible.project_id,
                version=bible.version,
                visual_digest=digest,
                generation_profile=generation_profile,
                visual_style=bible.visual_style,
                palette=bible.palette,
                aspect_ratio=bible.aspect_ratio,
                negative_prompt=bible.negative_prompt,
                shot=shot,
                characters=related,
                scene=scene,
                reference_images=inputs,
            )
            # 在派发前构造两请求，确保提示词长度、ID 等 Schema 错误不会触发部分付费调用。
            frame_request(task, "start")
            frame_request(task, "end")
            tasks.append(task.model_dump(mode="json"))
        frozen_tasks = state.get("frame_tasks")
        if frozen_tasks is not None and frozen_tasks != tasks:
            raise ValueError("冻结镜头任务已变化，不能沿用旧任务更换镜头或参考图")
        return {
            "frame_tasks": tasks,
            "frame_report": {},
            "current_stage": "shot_frames_generating",
            "events": [f"已准备 {len(tasks)} 个首尾帧镜头任务"],
        }

    return prepare_shot_frames


def dispatch_shot_frames(state: ComicDramaState) -> list[Send]:
    tasks = state.get("frame_tasks", [])
    if state["current_stage"] != "shot_frames_generating" or not tasks:
        raise ValueError("必须先准备非空镜头任务")
    # 这里只有一个注册节点名，运行时为每个镜头生成一个任务实例。
    # task 是 JSON 基础类型，客户端通过 make_generate_shot_frames 的闭包注入。
    return [Send("generate_shot_frames", {"task": task}) for task in tasks]


def make_generate_shot_frames(generator: ImageGenerator):
    def generate_shot_frames(state: ShotFrameInput) -> dict:
        task = ShotFrameTask.model_validate(state["task"])
        updates = {}
        for frame_type in FRAME_TYPES:
            request = frame_request(task, frame_type)
            common = request.model_dump(mode="json")
            try:
                # generator 先核验参考图和已落盘帧；命中时返回 reused=True。
                # 两帧在同一镜头任务里依次执行，不另开线程，因此一个任务最多一笔生成在途。
                image = generator.generate(request)
                asset = Asset(**common, status="succeeded", image=image)
            except ImageGenerationError as exc:
                # 首帧成功、尾帧失败时，两项都返回；其他镜头不会被这项业务错误撤销。
                asset = Asset(**common, status="failed", error_code=exc.code)
            except (OSError, ValueError):
                # 文件损坏、参考图变化或适配结果不一致，记录稳定错误，不自动重复付费。
                asset = Asset(
                    **common, status="failed", error_code="asset_storage_invalid"
                )
            updates[request.request_id] = asset.model_dump(mode="json")

        return {"assets": updates, "events": [f"{task.shot.shot_id} 首尾帧任务完成"]}

    return generate_shot_frames


def make_collect_shot_frames(store: AssetStore):
    def collect_shot_frames(state: ComicDramaState) -> dict:
        frozen_tasks = state.get("frame_tasks")
        if frozen_tasks is None:
            raise ValueError("缺少冻结镜头任务，不能汇总首尾帧")
        assets = state.get("assets", {})
        succeeded, failed, ordered = [], [], []
        tasks = [ShotFrameTask.model_validate(x) for x in frozen_tasks]
        for task in sorted(tasks, key=lambda x: x.shot.order):
            for frame_type in FRAME_TYPES:
                request = frame_request(task, frame_type)
                payload = assets.get(request.request_id)
                error, image = "missing_asset", None
                try:
                    asset = Asset.model_validate(payload) if payload else None
                    if asset is not None:
                        expected = request.model_dump(mode="json")
                        if any(
                            asset.model_dump(mode="json")[key] != value
                            for key, value in expected.items()
                        ):
                            error = "asset_request_mismatch"
                        elif asset.status == "failed":
                            error = asset.error_code or "asset_storage_invalid"
                        else:
                            # 再确认实际档案；reused 字段仍保留本次生成节点返回的值。
                            loaded = store.load(request)
                            if (
                                loaded is None
                                or asset.image is None
                                or loaded.local_path != asset.image.local_path
                            ):
                                error = "asset_storage_invalid"
                            else:
                                image = asset.image
                except (OSError, ValueError):
                    error = "asset_storage_invalid"
                entry = {
                    "shot_id": task.shot.shot_id,
                    "frame_type": frame_type,
                    "version": task.version,
                    "request_id": request.request_id,
                }
                if image is None:
                    failed.append({**entry, "error_code": error})
                else:
                    succeeded.append(request.request_id)
                    ordered.append(
                        {
                            **entry,
                            "local_path": image.local_path,
                            "reused": image.reused,
                        }
                    )
        stage = (
            "shot_frames_ready"
            if not failed
            else ("shot_frames_partial_failed" if succeeded else "shot_frames_failed")
        )
        return {
            "frame_report": {
                "expected_count": len(tasks) * 2,
                "succeeded_ids": succeeded,
                "failed": failed,
                "ordered_frames": ordered,
                "is_complete": not failed,
            },
            "current_stage": stage,
            "events": [f"首尾帧汇总：成功 {len(succeeded)}，失败 {len(failed)}"],
        }

    return collect_shot_frames
