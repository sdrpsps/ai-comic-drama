# 生成角色或者场景的提示词
# 这里不会像之前那样直接写死
# 因为角色也好、场景也好，都是用户来定的，你这里没办法写死

"""
角色视觉参考图；统一画风：电影感国风漫画……角色：林晚；身份：夜市摊主……稳定外观：齐肩黑发，左眼下有一颗小痣；固定服装：暗红围裙配米白衬衫。
"""

import hashlib

from server.schema import (
    CharacterProfile,
    ImageGenerationRequest,
    SceneProfile,
    VisualBible,
)


# 工具方法：做指纹的
def visual_digest(bible: VisualBible) -> str:
    return hashlib.sha256(bible.model_dump_json().encode()).hexdigest()[:16]


def _request(bible: VisualBible, owner_id: str, purpose, prompt: str):
    # 返回的就是一个 ImageGenerationRequest 结构的数据
    """
    类似于:
    {
        "request_id": "img_project_a1b2c3d4e5f6_character_reference_char_lin_wan_v2_ab12cd34ef567890",
        "purpose": "character_reference",
        "owner_id": "char_lin_wan",
        "version": 2,
        "prompt": "角色视觉参考图；统一画风：电影感国风漫画，线条干净，光影柔和；统一色彩：统一低饱和暖色基础，环境局部颜色服从已登记场景。\\n角色：林晚；身份：夜市摊主；性格气质：嘴硬心软。\\n稳定外观：齐肩黑发，左眼下有一颗小痣；固定服装：暗红围裙配米白衬衫。\\n辨识关键词：齐肩黑发、眼下小痣、暗红围裙。\\n单一角色，全身站姿，简洁中性背景，清晰展示脸部、发型与服装；无文字标签。",
        "negative_prompt": "文字标签、水印、额外人物、角色外观与固定服装漂移",
        "size": "2048x2048"
    }
    """
    return ImageGenerationRequest(
        request_id=f"img_{bible.project_id}_{purpose}_{owner_id}_v{bible.version}_{visual_digest(bible)}",
        purpose=purpose,
        owner_id=owner_id,
        version=bible.version,
        prompt=prompt,
        negative_prompt=bible.negative_prompt,
        size=bible.reference_size,
    )


# 角色
def character_reference_request(bible: VisualBible, character: CharacterProfile):
    return _request(
        bible,
        character.character_id,
        "character_reference",
        f"角色视觉参考图；统一画风：{bible.visual_style}；统一色彩：{bible.palette}。\n"
        f"角色：{character.name}；身份：{character.identity}；性格气质：{character.personality}。\n"
        f"稳定外观：{character.appearance}；固定服装：{character.clothing}。\n"
        f"辨识关键词：{'、'.join(character.visual_keywords)}。\n"
        "单一角色，全身站姿，简洁中性背景，清晰展示脸部、发型与服装；无文字标签。",
    )


# 场景
def scene_reference_request(bible: VisualBible, scene: SceneProfile):
    return _request(
        bible,
        scene.scene_id,
        "scene_reference",
        f"场景视觉参考图；统一画风：{bible.visual_style}；统一色彩：{bible.palette}。\n"
        f"场景：{scene.name}；时间：{scene.time}；空间布局：{scene.location}。\n"
        f"光线：{scene.lighting}；场景主色：{scene.colors}。\n"
        f"环境关键词：{'、'.join(scene.visual_keywords)}。\n"
        "空镜头，无人物，不加入分镜动作，展示环境布局与固定元素；无文字标签。",
    )
