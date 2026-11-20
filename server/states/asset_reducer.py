from server.schema import Asset


# 这里有两个参数：current、update
# 这两个都是字典类型
# 这个reducer要做的事情，就是把 update 合并到 current 里面
def merge_assets(current: dict, update: dict) -> dict:
    # 以 current 打底
    merged = dict(current)

    # 中间就是要做将 update 合并到 merged
    for key, payload in update.items():
        asset = Asset.model_validate(payload)
        if key != asset.request_id:
            raise ValueError("素材索引键必须等于 request_id")
        if key in merged:
            previous = Asset.model_validate(merged[key])
            # 同键只能代表同一请求，不能静默覆盖提示词或归属。
            identity = (
                "purpose",
                "owner_id",
                "version",
                "prompt",
                "negative_prompt",
                "size",
            )
            if any(
                getattr(previous, name) != getattr(asset, name) for name in identity
            ):
                raise ValueError("同一素材键出现不同请求")
        # 当前尝试覆盖旧尝试：失败后成功可恢复；文件损坏后失败也不保留伪成功。
        # 两个并行分支的用途与 owner 不同，因此不会同时写同一个键。
        merged[key] = asset.model_dump(mode="json")

    return merged
