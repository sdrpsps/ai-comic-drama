# 视觉圣经
# 整部作品的视觉效果设定

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .character_profile import CharacterProfile
from .scene_profile import SceneProfile


class VisualBible(BaseModel):
    """审核后的视觉快照；保存基础类型，方便服务检查点序列化。
    
    示例::

        {
            "project_id": "project_a1b2c3d4e5f6",
            "version": 2,
            "visual_style": "电影感国风漫画，线条干净，光影柔和",
            "palette": "统一低饱和暖色基础，环境局部颜色服从已登记场景",
            "aspect_ratio": "9:16",
            "reference_size": "2048x2048",
            "negative_prompt": "文字标签、水印、额外人物、角色外观与固定服装漂移",
            "characters": [
                {
                    "character_id": "char_lin_wan",
                    "name": "林晚",
                    "identity": "夜市摊主",
                    "personality": "嘴硬心软",
                    "appearance": "齐肩黑发，左眼下有一颗小痣",
                    "clothing": "暗红围裙配米白衬衫",
                    "visual_keywords": ["齐肩黑发", "眼下小痣", "暗红围裙"]
                }
            ],
            "scenes": [
                {
                    "scene_id": "scene_night_market",
                    "name": "老街夜市",
                    "time": "夏夜九点",
                    "location": "窄巷两侧是灯火摊位，地面湿滑反光",
                    "lighting": "暖黄灯笼光，远处霓虹偏冷",
                    "colors": "琥珀、暗红、深夜蓝",
                    "visual_keywords": ["灯笼", "湿地面", "窄巷"]
                }
            ],
            "generation_profile": "ark:doubao-seedream"
        }
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    # 作品稳定标识。客户端可显式传入；未传时由创意摘要确定性生成。
    # 会写入参考图请求 ID，避免不同作品因角色/场景 ID 相同而共用一张图。
    project_id: str = Field(pattern=r"^project_[a-z0-9_]+$")
    version: int = Field(ge=0)

    # 全片统一画风，来自已审核的创意需求（默认「暖色二维漫画」）。
    # 角色参考图和场景参考图的提示词都会带上它。
    visual_style: str

    # 全片统一色彩约束，组装快照时写死，不从创意需求读取。
    # 场景自身的主色仍记在 SceneProfile.colors，这里只规定全片底色。
    palette: str
    aspect_ratio: Literal["9:16", "16:9", "1:1"]
    reference_size: str = "2048x2048"

    # 反向提示词 [避免xxxx、不要xxxx]
    negative_prompt: str
    characters: tuple[CharacterProfile, ...]
    scenes: tuple[SceneProfile, ...]

    # 本次图像生成配置，形如「供应商:模型」（如 ark:doubao-seedream）。
    # 不参与画风或提示词，但会计入快照摘要；换模型重跑时与已冻结设定不一致，从而拒绝复用旧图。
    generation_profile: str
