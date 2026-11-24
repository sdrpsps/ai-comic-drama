from typing import Literal

from pydantic import BaseModel, ConfigDict

from .character_profile import CharacterProfile
from .image_reference import ImageReference
from .scene_profile import SceneProfile
from .storyboard import StoryBoard


class ShotFrameTask(BaseModel):
    """一张镜头任务单；不包含全部故事、所有镜头或客户端对象。"""

    """
    {
      "project_id": "project_a1b2c3d4e5f6",
      "version": 2,
      "visual_digest": "ab12cd34ef567890",
      "generation_profile": "ark:doubao-seedream",
      "visual_style": "电影感国风漫画，线条干净，光影柔和",
      "palette": "统一低饱和暖色基础，环境局部颜色服从已登记场景",
      "aspect_ratio": "9:16",
      "negative_prompt": "文字标签、水印、额外人物、角色外观与固定服装漂移",
      "shot": {
          "shot_id": "shot_01",
          "order": 1,
          "duration_seconds": 4,
          "scene_id": "scene_night_market",
          "character_ids": ["char_lin_wan"],
          "action": "林晚把一碗热汤推到摊位边缘",
          "composition": "竖屏中景，人物位于画面左侧，摊位灯笼占右侧",
          "dialogue": "",
          "camera_motion": "固定机位",
          "start_frame_prompt": "林晚低头看向碗沿，双手还扶着碗",
          "end_frame_prompt": "碗已经推到摊位边缘，林晚抬眼看向巷口",
          "video_prompt": "4 秒镜头：林晚把热汤从身前推到摊位边缘；镜头保持固定。"
      },
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
      "scene": {
          "scene_id": "scene_night_market",
          "name": "老街夜市",
          "time": "夏夜九点",
          "location": "窄巷两侧是灯火摊位，地面湿滑反光",
          "lighting": "暖黄灯笼光，远处霓虹偏冷",
          "colors": "琥珀、暗红、深夜蓝",
          "visual_keywords": ["灯笼", "湿地面", "窄巷"]
      },
      "reference_images": [
          {
              "local_path": "outputs/images/character_reference/char_lin_wan/v2/...",
              "content_sha256": "ab12cd34ef567890ab12cd34ef5..."
          },
          {
              "local_path": "outputs/images/scene_reference/scene_night_market/v2/....",
              "content_sha256": "0123456789abcdef0123456789ab..."
          }
      ]
    }
    """

    model_config = ConfigDict(extra="forbid")
    project_id: str
    version: int
    visual_digest: str
    generation_profile: str
    visual_style: str
    palette: str
    aspect_ratio: Literal["9:16", "16:9", "1:1"]
    negative_prompt: str
    shot: StoryBoard
    characters: list[CharacterProfile]
    scene: SceneProfile
    reference_images: list[ImageReference]
