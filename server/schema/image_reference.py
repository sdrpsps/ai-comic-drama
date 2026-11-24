from pydantic import BaseModel, ConfigDict, Field


class ImageReference(BaseModel):
    """冻结参考文件的路径与内容身份，图片字节只在调用时读取。"""

    model_config = ConfigDict(extra="forbid", frozen=True)
    local_path: str = Field(min_length=1)
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
