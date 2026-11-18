import hashlib
import json

from server.schema import StoryBoard


def shot_fingerprint(shots: list[StoryBoard]) -> str:
    """对完整分镜取稳定指纹，用于识别未变化或回到旧版本。"""
    payload = [shot.model_dump(mode="json") for shot in shots]
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]
