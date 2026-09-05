"""领星 API 签名所需的 AES/MD5 加密工具"""
import hashlib
import base64
from Crypto.Cipher import AES

BLOCK_SIZE = 16


def _pad(text: str) -> str:
    """PKCS5Padding 补位"""
    padding_len = BLOCK_SIZE - len(text) % BLOCK_SIZE
    return text + chr(padding_len) * padding_len


def aes_encrypt(key: str, data: str) -> str:
    """AES/ECB/PKCS5Padding 加密，返回 base64 编码的密文"""
    key_bytes = _normalize_key(key)
    data = _pad(data)
    cipher = AES.new(key_bytes, AES.MODE_ECB)
    encrypted = cipher.encrypt(data.encode())
    return base64.b64encode(encrypted).decode("utf-8")


def _normalize_key(key: str) -> bytes:
    """规范化 AES 密钥到 32 字节（不足补 \\x00，超出截断）"""
    key_bytes = key.encode("utf-8")
    if len(key_bytes) == 16 or len(key_bytes) == 24 or len(key_bytes) == 32:
        return key_bytes
    if len(key_bytes) < 32:
        return key_bytes.ljust(32, b"\x00")
    return key_bytes[:32]


def md5_encrypt(text: str) -> str:
    """MD5 加密，返回 32 位小写十六进制字符串"""
    return hashlib.md5(text.encode("utf-8")).hexdigest()
