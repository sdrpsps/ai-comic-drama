from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .generated_image import GeneratedImage


class Asset(BaseModel):
    """一项参考图资源：成功保存 GeneratedImage，失败保存结构化错误。

    成功的示例：
    {
        "purpose": "character_reference",
        "owner_id": "char_lin_wan",
        "version": 2,
        "request_id": "img_project_a1b2c3d4e5f6_character_reference_char_lin_wan_v2_ab12cd34ef567890",
        "status": "succeeded",
        "prompt": "角色视觉参考图；统一画风：电影感国风漫画，线条干净，光影柔和；统一色彩：统一低饱和暖色基础，环境局部颜色服从已登记场景。\\n角色：林晚；身份：夜市摊主；性格气质：嘴硬心软。\\n稳定外观：齐肩黑发，左眼下有一颗小痣；固定服装：暗红围裙配米白衬衫。\\n辨识关键词：齐肩黑发、眼下小痣、暗红围裙。\\n单一角色，全身站姿，简洁中性背景，清晰展示脸部、发型与服装；无文字标签。",
        "negative_prompt": "文字标签、水印、额外人物、角色外观与固定服装漂移",
        "size": "2048x2048",
        "image": {
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
        },
        "error_code": null
    }

    失败示例::

    {
        "purpose": "character_reference",
        "owner_id": "char_lin_wan",
        "version": 2,
        "request_id": "img_project_a1b2c3d4e5f6_character_reference_char_lin_wan_v2_ab12cd34ef567890",
        "status": "failed",
        "prompt": "角色视觉参考图；统一画风：电影感国风漫画，线条干净，光影柔和；统一色彩：统一低饱和暖色基础，环境局部颜色服从已登记场景。\\n角色：林晚；身份：夜市摊主；性格气质：嘴硬心软。\\n稳定外观：齐肩黑发，左眼下有一颗小痣；固定服装：暗红围裙配米白衬衫。\\n辨识关键词：齐肩黑发、眼下小痣、暗红围裙。\\n单一角色，全身站姿，简洁中性背景，清晰展示脸部、发型与服装；无文字标签。",
        "negative_prompt": "文字标签、水印、额外人物、角色外观与固定服装漂移",
        "size": "2048x2048",
        "image": null,
        "error_code": "rate_limited"
    }
    """

    model_config = ConfigDict(extra="forbid")
    purpose: Literal["character_reference", "scene_reference"]
    owner_id: str = Field(pattern=r"^(char|scene)_[a-z0-9_]+$")
    version: int = Field(ge=0)
    request_id: str = Field(pattern=r"^img_[a-z0-9_]+$")
    status: Literal["succeeded", "failed"]
    prompt: str
    negative_prompt: str
    size: str
    image: GeneratedImage | None = None
    error_code: str | None = None

    # Asset 创建之后，会自动进行校验
    # Asset(...)、Asset.model_validate(...) 和 Asset.model_validate_json(...) 都会触发它。
    @model_validator(mode="after")
    def check_result(self):
        if self.status == "succeeded":
            if self.image is None or self.error_code is not None:
                raise ValueError("成功素材必须有 image，且不能有 error_code")
            if (
                self.image.request_id,
                self.image.purpose,
                self.image.owner_id,
                self.image.version,
                self.image.prompt,
                self.image.negative_prompt,
                self.image.size,
            ) != (
                self.request_id,
                self.purpose,
                self.owner_id,
                self.version,
                self.prompt,
                self.negative_prompt,
                self.size,
            ):
                raise ValueError("成功图片必须与素材请求完全对应")
        elif self.image is not None or not self.error_code:
            raise ValueError("失败素材必须有 error_code，且不能有成功 image")
        return self
