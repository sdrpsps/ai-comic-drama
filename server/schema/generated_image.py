from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class GeneratedImage(BaseModel):
    """已规范化的素材结果；State 不需要理解平台原始响应。
    
    示例::

    {
        "asset_id": "asset_img_project_a1b2c3d4e5f6_character_reference_char_lin_wan_v2_ab12cd34ef567890",
        "request_id": "img_project_a1b2c3d4e5f6_character_reference_char_lin_wan_v2_ab12cd34ef567890",
        "purpose": "character_reference",
        "owner_id": "char_lin_wan",
        "version": 2,
        "status": "succeeded",
        "local_path": "outputs/images/character_reference/char_lin_wan/v2/img_project_a1b2c3d4e5f6_character_reference_char_lin_wan_v2_ab12cd34ef567890.png",
        "remote_url": "https://example.invalid/generated/lin-wan.png",
        "provider_request_id": null,
        "provider_model": "doubao-seedream",
        "prompt": "角色视觉参考图；统一画风：电影感国风漫画，线条干净，光影柔和；统一色彩：统一低饱和暖色基础，环境局部颜色服从已登记场景。\\n角色：林晚；身份：夜市摊主；性格气质：嘴硬心软。\\n稳定外观：齐肩黑发，左眼下有一颗小痣；固定服装：暗红围裙配米白衬衫。\\n辨识关键词：齐肩黑发、眼下小痣、暗红围裙。\\n单一角色，全身站姿，简洁中性背景，清晰展示脸部、发型与服装；无文字标签。",
        "negative_prompt": "文字标签、水印、额外人物、角色外观与固定服装漂移",
        "size": "2048x2048",
        "prompt_digest": "ab12cd34ef567890",
        "request_digest": "0123456789abcdef",
        "reused": false
    }
    
    
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    # 资源 id
    asset_id: str = Field(pattern=r"^asset_img_[a-z0-9_]+$")
    # 请求 id
    request_id: str = Field(pattern=r"^img_[a-z0-9_]+$")
    purpose: Literal[
        "character_reference",
        "scene_reference",
        "shot_start",
        "shot_end",
    ]
    owner_id: str = Field(pattern=r"^(project|char|scene|shot)_[a-z0-9_]+$")
    version: int = Field(ge=0)
    status: Literal["succeeded"] = "succeeded"
    # 生成图片存储的路径
    local_path: str = Field(min_length=1)
    remote_url: str | None = None

    # 图像平台自己的请求编号，和项目里的 request_id 不是一回事。
    # 假图生成器写成 fake_ 加项目编号；当前火山方舟适配器不回填，所以是 None。
    provider_request_id: str | None = None

    # 生成图像所用的模型
    provider_model: str
    prompt: str
    negative_prompt: str = ""
    size: str

    # 提示词指纹
    # 针对提示词作了一个哈希计算，取前16位
    prompt_digest: str = Field(pattern=r"^[a-f0-9]{16}$")

    # 请求指纹
    # 针对整份请求作了一个哈希计算，取前16位
    request_digest: str = Field(pattern=r"^[a-f0-9]{16}$")

    # 是否是复用的
    reused: bool = False
