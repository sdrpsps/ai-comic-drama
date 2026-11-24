"""共用工具：帧标识、审核快照、新版本请求与图片检查。"""

import hashlib
import json
from io import BytesIO

from PIL import Image

from server.prompts.frame_prompts import frame_request
from server.schema import (
    Asset,
    FrameRedoItem,
    ImageGenerationRequest,
    ImageReference,
    ShotFrameTask,
)
from server.schema.frame_review import FrameType
from server.states import ComicDramaState
from server.storage import AssetStore

FRAME_TYPES: tuple[FrameType, FrameType] = ("start", "end")


def frame_key(shot_id: str, frame_type: FrameType) -> str:
    """拼出一帧的逻辑键，用来在索引里选中当前这一帧。

    入参：shot_id 是镜头 ID，如 shot_03；frame_type 是 start（首帧）或 end（尾帧）。
    返回：形如 shot_03:end 的字符串。它只用来定位当前帧，和保存每次生成档案的 request_id 不是同一个标识。
    """
    return f"{shot_id}:{frame_type}"


def snapshot_token(
    project_id: str, version: int, round_number: int, frames: list
) -> str:
    """为当前这一轮画面计算审核令牌，提交审核时必须带上同一个值。

    入参：project_id 是作品 ID；version 是已批准的分镜版本；round_number 是审核轮次；
    frames 是这一轮各帧的检查记录，其中包含文件内容摘要。
    返回：64 位十六进制字符串。重做后即使分镜文字没变，轮次或文件摘要变了也会得到新令牌。
    """
    payload = [project_id, version, round_number, frames]
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def redo_request(
    previous: ImageGenerationRequest, item: FrameRedoItem
) -> ImageGenerationRequest:
    """根据当前候选请求和返工意见，造出下一版生图请求。

    入参：previous 是这一帧当前的 ImageGenerationRequest；item 是一条 FrameRedoItem。
    返回：新的 ImageGenerationRequest。version 加 1；item.comment 非空时追加到提示词末尾；
    request_id 按新内容重新计算。item.reason 只记录原因，不进入提示词。
    """
    data = previous.model_dump(mode="json")
    data["version"] += 1
    if item.comment:
        data["prompt"] += f"\n本次画面修改要求：{item.comment}"
    # 【重要】稳定新 ID 绑定旧请求、素材版本与意见。重放同一计划时可以命中缓存；
    # 换意见生成新 ID，旧图片和旧元数据不会被原子写入静默覆盖。
    digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:16]
    data["request_id"] = (
        f"img_redo_{previous.owner_id}_{previous.purpose}_v{data['version']}_{digest}"
    )
    return ImageGenerationRequest.model_validate(data)


MAX_FRAME_REDOS = 2


def load_reference(
    store: AssetStore, assets: dict[str, dict], request: ImageGenerationRequest
) -> ImageReference:
    """核对参考图请求、State 记录和磁盘文件，返回冻结了实际内容的参考图。

    入参：store 是素材库；assets 是状态里的素材表，键为 request_id；
    request 是角色或场景参考图的生图请求。
    返回：ImageReference，含相对路径和文件内容摘要。记录缺失、失败、与请求不一致，
    或磁盘档案对不上时抛出 ValueError。
    """
    payload = assets.get(request.request_id)
    asset = Asset.model_validate(payload) if payload else None
    # 【重要】先核对 State 与当前请求，再重新验证磁盘文件。
    # reference_report.is_complete 不能证明文件现在仍然存在。
    expected = request.model_dump(mode="json")
    if (
        asset is None
        or asset.status != "succeeded"
        or asset.image is None
        or any(
            asset.model_dump(mode="json")[name] != value
            for name, value in expected.items()
        )
    ):
        raise ValueError("参考素材缺失、失败或与当前请求不一致")
    image = store.load(request)
    if image is None or asset.image.local_path != image.local_path:
        raise ValueError("参考素材没有匹配的落盘档案")
    return store.reference_from_image(image)


def frame_project_id(state: ComicDramaState) -> str:
    """取出并核对当前作品 ID。

    入参：state 是图状态，必须包含 visual_bible.project_id；state.project_id 可以不填。
    返回：冻结视觉设定里的作品 ID。状态里另外写了 project_id 且两边不一致时抛出 ValueError。
    """
    visual_bible = state.get("visual_bible")
    project_id = visual_bible.get("project_id") if visual_bible is not None else None
    if project_id is None:
        raise ValueError("缺少冻结视觉设定或作品 ID，不能审核首尾帧")
    if not isinstance(project_id, str):
        raise TypeError("冻结视觉设定中的作品 ID 必须是字符串")
    if state.get("project_id", project_id) != project_id:
        raise ValueError("作品 ID 与冻结视觉设定不一致")
    return project_id


def initial_frame_index(state: ComicDramaState) -> dict[str, dict]:
    """按冻结的镜头任务，重建每一帧第一次生成时的生图请求。

    入参：state 是图状态，使用 approved_version、revision_count、frame_tasks 和 visual_bible。
    返回：字典。键是 frame_key，值是 ImageGenerationRequest 的字典。这里只有首版请求，不含重做后的候选。
    """
    approved_version = state.get("approved_version")
    if approved_version is None or approved_version != state.get("revision_count"):
        raise ValueError("分镜版本发生变化，不能审核旧帧")
    frozen_tasks = state.get("frame_tasks")
    if frozen_tasks is None:
        raise ValueError("缺少冻结镜头任务，不能审核首尾帧")
    project_id = frame_project_id(state)
    index = {}
    tasks = [ShotFrameTask.model_validate(x) for x in frozen_tasks]
    if not 4 <= len(tasks) <= 6 or len({x.shot.shot_id for x in tasks}) != len(tasks):
        raise ValueError("冻结镜头任务数量或 ID 不合法")
    for task in sorted(tasks, key=lambda x: x.shot.order):
        if task.project_id != project_id or task.version != approved_version:
            raise ValueError("帧任务不属于当前批准作品版本")
        for kind in FRAME_TYPES:
            index[frame_key(task.shot.shot_id, kind)] = frame_request(
                task, kind
            ).model_dump(mode="json")
    return index


def inspect_frames(
    state: ComicDramaState, store: AssetStore
) -> tuple[dict[str, dict], list[dict[str, object]], list[dict[str, object]]]:
    """重新打开每一帧的实际文件做检查，不沿用 frame_report 里的成功标记。

    入参：state 是图状态；store 是素材库，用来读取参考图和已经落盘的帧。
    返回：(index, frames, failed)。
    index 是当前候选帧索引，键为 frame_key，值为 ImageGenerationRequest 字典。
    frames 是每一帧的检查记录：成功的含路径、宽高和内容摘要，失败的 local_path 为 None。
    failed 是失败帧列表，每一项是 FrameRedoItem 的字典。
    """
    baseline = initial_frame_index(state)
    index = state.get("frame_index", baseline)
    if set(index) != set(baseline):
        raise ValueError("当前帧索引必须完整对应冻结镜头")
    frames: list[dict[str, object]] = []
    failed: list[dict[str, object]] = []
    assets = state.get("assets", {})
    for key in baseline:  # 冻结顺序仅用于展示；查找始终使用逻辑键。
        request = ImageGenerationRequest.model_validate(index[key])
        shot_id, kind = key.split(":")
        if kind != "start" and kind != "end":
            raise ValueError("帧索引包含未知的帧类型")
        if request.owner_id != shot_id or request.purpose != f"shot_{kind}":
            raise ValueError("帧索引与请求归属不一致")
        original = ImageGenerationRequest.model_validate(baseline[key])
        if (
            any(
                getattr(request, name) != getattr(original, name)
                for name in ("reference_images", "size", "negative_prompt")
            )
            or request.version < original.version
        ):
            raise ValueError("候选帧不能改变冻结参考、尺寸或回退版本")
        entry: dict[str, object] = {
            "key": key,
            "shot_id": shot_id,
            "frame_type": kind,
            "version": request.version,
            "request_id": request.request_id,
        }
        # 最近一次重做的旧版本供人工对照；只展示档案，不把旧图认作当前合格候选。
        for task in state.get("frame_redo_tasks", []):
            if (
                task["key"] == key
                and task["request"]["request_id"] == request.request_id
            ):
                old = assets.get(task["previous_request_id"], {})
                entry["previous"] = {
                    "request_id": task["previous_request_id"],
                    "version": old.get("version"),
                    "local_path": (old.get("image") or {}).get("local_path"),
                }
        error = "missing_asset"
        try:
            raw = assets.get(request.request_id)
            asset = Asset.model_validate(raw) if raw else None
            if asset:
                expected = request.model_dump(mode="json")
                if any(
                    asset.model_dump(mode="json")[k] != v for k, v in expected.items()
                ):
                    raise ValueError("素材请求不一致")
                error = asset.error_code or "asset_storage_invalid"
                if asset.status == "succeeded":
                    for source in request.reference_images:
                        store.read_reference(source)
                    loaded = store.load(request)
                    if (
                        loaded is None
                        or asset.image is None
                        or loaded.local_path != asset.image.local_path
                    ):
                        raise ValueError("素材没有有效档案")
                    reference = store.reference_from_image(loaded)
                    content = store.read_reference(reference)
                    # open() 只识别文件，load() 才执行解码；限制像素后再分配解码内存。
                    with Image.open(
                        BytesIO(content), formats=["PNG", "JPEG", "WEBP"]
                    ) as image:
                        width, height = image.size
                        if width * height > 16_000_000:
                            raise ValueError("素材超过 1600 万像素上限")
                        image.load()
                        # Fake 明确只验编排用的 1×1；真实图严格匹配本次请求的数字尺寸。
                        if loaded.provider_model == "fake-image-v1":
                            if (width, height) != (1, 1):
                                raise ValueError("Fake 图片尺寸不符合约定")
                        elif "x" not in request.size or (width, height) != tuple(
                            map(int, request.size.split("x"))
                        ):
                            raise ValueError(
                                "实际尺寸不符合请求；不能用 size 元数据冒充解码结果"
                            )
                    frames.append(
                        {
                            **entry,
                            "local_path": loaded.local_path,
                            "content_sha256": reference.content_sha256,
                            "width": width,
                            "height": height,
                            "error_code": None,
                        }
                    )
                    continue
        except (OSError, ValueError, Image.DecompressionBombError):
            error = "asset_storage_invalid"
        failed.append(
            FrameRedoItem(shot_id=shot_id, frame_type=kind, reason=error).model_dump(
                mode="json"
            )
        )
        frames.append({**entry, "local_path": None, "error_code": error})
    return index, frames, failed
