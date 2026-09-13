"""领星 API 签名生成

签名规则（7步）：
1. 将所有参数（业务参数 + access_token + app_key + timestamp）按 ASCII 排序
2. 拼接为 key1=value1&key2=value2 格式（value 为空不参与，value 为 null 会参与）
3. 对拼接字符串进行 MD5(32位)加密并转大写
4. 使用 AES/ECB/PKCS5Padding 加密 MD5 值，密钥为 AppId
5. 最终签名由 query string encoder 做 URL 编码后使用
6. 签名有效期 2 分钟，建议使用实时时间戳，不要缓存
"""
import json

from .aes_util import aes_encrypt, md5_encrypt


def generate_sign(app_id: str, params: dict) -> str:
    """
    生成领星 API 请求签名（base64 格式，调用方负责 URL 编码）

    Args:
        app_id: 领星 AppId，同时作为 AES 加密密钥
        params: 所有请求参数（业务参数 + access_token + app_key + timestamp）

    Returns:
        base64 编码的签名字符串（未 URL 编码）
    """
    canonical_str = _format_params(params)
    md5_upper = md5_encrypt(canonical_str).upper()
    return aes_encrypt(app_id, md5_upper)


def _format_params(params: dict) -> str:
    """按 ASCII 排序后拼接参数为 key1=value1&key2=value2 格式"""
    if not params or not isinstance(params, dict):
        return ""

    parts = []
    for k in sorted(params.keys()):
        v = params[k]
        if v == "":
            continue  # 空字符串不参与签名
        elif isinstance(v, (dict, list)):
            # 嵌套结构序列化为 JSON，确保无空格
            parts.append(f"{k}={json.dumps(v, separators=(',', ':'), ensure_ascii=False)}")
        elif v is None:
            parts.append(f"{k}=null")
        else:
            parts.append(f"{k}={v}")
    return "&".join(parts)
