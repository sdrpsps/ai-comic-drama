"""从冻结镜头任务构造首尾帧请求，不重新生成故事文本。"""

import hashlib

from server.schema import ImageGenerationRequest, ShotFrameTask
from server.schema.frame_review import FrameType


def frame_request(task: ShotFrameTask, frame_type: FrameType) -> ImageGenerationRequest:
    shot = task.shot
    purpose = "shot_start" if frame_type == "start" else "shot_end"
    frame_prompt = (
        shot.start_frame_prompt if frame_type == "start" else shot.end_frame_prompt
    )
    descriptions = []
    for number, character in enumerate(task.characters, start=1):
        descriptions.append(
            f"参考图{number}对应角色{character.character_id}（{character.name}）；"
            f"稳定外观：{character.appearance}；固定服装：{character.clothing}；"
            f"辨识特征：{'、'.join(character.visual_keywords)}。"
        )
    scene = task.scene
    descriptions.append(
        f"参考图{len(task.characters) + 1}对应场景{scene.scene_id}（{scene.name}）；"
        f"布局：{scene.location}；时间：{scene.time}；光线：{scene.lighting}；"
        f"色彩：{scene.colors}；环境元素：{'、'.join(scene.visual_keywords)}。"
    )
    prompt = (
        f"生成镜头{shot.shot_id}的{'首帧' if frame_type == 'start' else '尾帧'}，只生成一张静态漫画画面。\n"
        f"画风：{task.visual_style}；统一基础色彩：{task.palette}；画幅：{task.aspect_ratio}。\n"
        + "\n".join(descriptions)
        + f"\n镜头动作背景：{shot.action}；主体构图：{shot.composition}；机位/运动背景：{shot.camera_motion}。\n"
        + f"这一帧的瞬间：{frame_prompt}\n"
        + "参考图用于保持人物外观、服装与场景元素；按本帧动作重新构图，不照搬参考图的站姿或空镜。"
        + "首尾帧属于同一镜头，保持人物身份、服装和空间关系；不绘制对白、字幕或水印。"
    )
    # 【重要】同一任务可确定性重建请求。任务摘要包含镜头内容、视觉配置、
    # 参考文件内容摘要；换动作或换图后不能碰巧命中旧首尾帧。
    digest = hashlib.sha256(task.model_dump_json().encode()).hexdigest()[:16]
    size = {"9:16": "1440x2560", "16:9": "2560x1440", "1:1": "2048x2048"}[
        task.aspect_ratio
    ]
    return ImageGenerationRequest(
        request_id=f"img_{task.project_id}_{purpose}_{shot.shot_id}_v{task.version}_{digest}",
        purpose=purpose,
        owner_id=shot.shot_id,
        version=task.version,
        prompt=prompt,
        negative_prompt=task.negative_prompt,
        size=size,
        reference_images=task.reference_images,
    )
