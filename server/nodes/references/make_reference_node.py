from server.prompts import character_reference_request, scene_reference_request
from server.schema import Asset
from server.services.image import ImageGenerationError, ImageGenerator
from server.states import ComicDramaState

from .visual_bible import _checked_bible

# 之后在编排图的时候，加入该节点时，会传入两个东西：
# 1. generator：使用哪个图片生成器（ark / fake）
# 2. purpose：生成什么图片（角色、场景...）
# builder.add_node(
#     "generate_character_references",
#     make_reference_node(image_generator, purpose="character_reference"),
# )
# builder.add_node(
#     "generate_scene_references",
#     make_reference_node(image_generator, purpose="scene_reference"),
# )


def make_reference_node(generator: ImageGenerator, *, purpose: str):
    def generate_references(state: ComicDramaState) -> dict:
        # bible 是一个 VisualBible 类型数据
        bible = _checked_bible(state)

        if purpose == "character_reference":
            # requests: [ImageGenerationRequest, ImageGenerationRequest, ImageGenerationRequest...]
            requests = [character_reference_request(bible, x) for x in bible.characters]
        else:
            requests = [scene_reference_request(bible, x) for x in bible.scenes]

        updates = {}  # 目前是空的，回头会放入生成的图像资源（Asset）

        for request in requests:
            # 遍历每一个请求
            # 生成图像
            # 无论生成图像成功还是失败，都会有的字段
            common = {
                "purpose": request.purpose,
                "owner_id": request.owner_id,
                "version": request.version,
                "request_id": request.request_id,
                "prompt": request.prompt,
                "negative_prompt": request.negative_prompt,
                "size": request.size,
            }
            try:
                # 使用图片生成器来生成图片
                image = generator.generate(request)
            except ImageGenerationError as exc:
                # 平台失败。例如限流时 error_code 是 rate_limited，图片不会落盘。
                asset = Asset(**common, status="failed", error_code=exc.code)
            except (OSError, ValueError):
                # 路径越界、文件损坏或旧图对不上，都不自动再出一张。
                asset = Asset(
                    **common, status="failed", error_code="asset_storage_invalid"
                )
            else:
                # 生成成功，asset 也会有值
                asset = Asset(**common, status="succeeded", image=image)

            updates[request.request_id] = asset.model_dump(mode="json")
        # 更新图的状态
        return {
            "assets": updates,
            "events": [f"{purpose} 分支完成，共 {len(updates)} 项"],
        }

    return generate_references
