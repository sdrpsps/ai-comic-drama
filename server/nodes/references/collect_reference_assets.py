# 收集结果

from server.prompts import character_reference_request, scene_reference_request
from server.schema import Asset
from server.states import ComicDramaState

from .visual_bible import _checked_bible


def collect_reference_assets(state: ComicDramaState) -> dict:
    # bible 就是一个 VisualBible 类型的数据
    bible = _checked_bible(state)
    if "visual_digest" not in state:
        raise ValueError("缺少视觉指纹，不能汇总参考素材")
    # requests: [ImageGenerationRequest, ImageGenerationRequest, ImageGenerationRequest...]
    # 即包含了角色图像生成的请求，也包含了场景图像生成的请求
    requests = [character_reference_request(bible, x) for x in bible.characters]
    requests += [scene_reference_request(bible, x) for x in bible.scenes]

    # 统计成功了多少条，失败了多少条
    succeeded, failed = [], []

    for request in requests:
        # 按 request_id 取出一条素材字典。账本里没有这条请求时是 None。
        # 例如林晚出图成功：
        # {
        #     "purpose": "character_reference",
        #     "owner_id": "char_lin_wan",
        #     "version": 2,
        #     "request_id": "img_project_a1b2c3d4e5f6_character_reference_char_lin_wan_v2_ab12cd34ef567890",
        #     "status": "succeeded",
        #     "prompt": "角色视觉参考图；统一画风：电影感国风漫画……角色：林晚……",
        #     "negative_prompt": "文字标签、水印、额外人物、角色外观与固定服装漂移",
        #     "size": "2048x2048",
        #     "image": {
        #         "asset_id": "asset_img_project_a1b2c3d4e5f6_character_reference_char_lin_wan_v2_ab12cd34ef567890",
        #         "request_id": "img_project_a1b2c3d4e5f6_character_reference_char_lin_wan_v2_ab12cd34ef567890",
        #         "purpose": "character_reference",
        #         "owner_id": "char_lin_wan",
        #         "version": 2,
        #         "status": "succeeded",
        #         "local_path": "outputs/images/character_reference/char_lin_wan/v2/img_project_a1b2c3d4e5f6_character_reference_char_lin_wan_v2_ab12cd34ef567890.png",
        #         "remote_url": "https://example.invalid/generated/lin-wan.png",
        #         "provider_request_id": None,
        #         "provider_model": "doubao-seedream",
        #         "prompt": "角色视觉参考图；统一画风：电影感国风漫画……角色：林晚……",
        #         "negative_prompt": "文字标签、水印、额外人物、角色外观与固定服装漂移",
        #         "size": "2048x2048",
        #         "prompt_digest": "ab12cd34ef567890",
        #         "request_digest": "0123456789abcdef",
        #         "reused": False,
        #     },
        #     "error_code": None,
        # }
        # 夜市被限流时 status 是 "failed"，image 是 None，error_code 是 "rate_limited"。
        payload = state.get("assets", {}).get(
            request.request_id
        )  # 目前是一个 json 数据
        asset = (
            Asset.model_validate(payload) if payload else None
        )  # 重新转成 Asset 类型

        # matches 最终得到一个 Boolean 类型的值
        # 有 asset 的前提下，和原本的 request 里面的信息能够对上号
        matches = asset is not None and (
            asset.request_id,
            asset.purpose,
            asset.owner_id,
            asset.version,
            asset.prompt,
            asset.negative_prompt,
            asset.size,
        ) == (
            request.request_id,
            request.purpose,
            request.owner_id,
            request.version,
            request.prompt,
            request.negative_prompt,
            request.size,
        )

        if asset is not None and matches and asset.status == "succeeded":
            # 成功的情况，往 succeeded 列表里面追加
            succeeded.append(request.request_id)
        else:
            # 失败的情况，往 failed 列表里面追加
            failed.append(
                {
                    "request_id": request.request_id,
                    "owner_id": request.owner_id,
                    "purpose": request.purpose,
                    "error_code": (
                        asset.error_code if matches else "asset_request_mismatch"
                    )
                    if asset
                    else "missing_asset",
                }
            )

    # 统计完成之后，更新图的状态
    return {
        "reference_report": {
            "version": bible.version,
            "visual_digest": state["visual_digest"],
            "expected_count": len(requests),
            "succeeded_ids": succeeded,
            "failed": failed,
            "is_complete": not failed,
        },
        "current_stage": "reference_assets_failed"
        if failed
        else "reference_assets_ready",
        "events": [f"参考素材汇总：成功 {len(succeeded)}，失败 {len(failed)}"],
    }
