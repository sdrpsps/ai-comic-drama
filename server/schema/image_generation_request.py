from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ImageGenerationRequest(BaseModel):
    """项目自己的图像生成请求，不暴露火山方舟 SDK 类型。

    示例::

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

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    # 图片生成的请求的 id
    request_id: str = Field(pattern=r"^img_[a-z0-9_]+$")
    # 图像用来干嘛的
    purpose: Literal[
        "character_reference", # 角色图
        "scene_reference", # 场景图
        "shot_start", # 首帧
        "shot_end",   # 尾帧
    ]
    # 和图像关联的
    owner_id: str = Field(pattern=r"^(project|char|scene|shot)_[a-z0-9_]+$")
    version: int = Field(ge=0)
    prompt: str = Field(min_length=1, max_length=4000)
    negative_prompt: str = Field(default="", max_length=2000)
    size: str = Field(default="2048x2048", pattern=r"^(\d{3,4}x\d{3,4}|[124]K)$")
