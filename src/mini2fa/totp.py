"""
TOTP (Time-based One-Time Password) 算法实现

基于 RFC 6238 标准
"""
import hmac
import hashlib
import struct
import time
import base64


def generate_totp(
    secret: str,
    algorithm: str = 'SHA1',
    digits: int = 6,
    period: int = 30
) -> str:
    """
    生成 TOTP 验证码

    Args:
        secret: Base32 编码的密钥
        algorithm: 哈希算法 (SHA1/SHA256/SHA512)
        digits: 验证码位数
        period: 时间步长（秒）

    Returns:
        验证码字符串（如 '123456'）
    """
    # Base32 解码
    key = base64.b32decode(secret, casefold=True)

    # 计算时间步数
    counter = int(time.time()) // period

    # 打包为 8 字节大端序
    msg = struct.pack('>Q', counter)

    # 选择哈希算法
    hash_func = {
        'SHA1': hashlib.sha1,
        'SHA256': hashlib.sha256,
        'SHA512': hashlib.sha512
    }[algorithm]

    # HMAC 计算
    hmac_result = hmac.new(key, msg, hash_func).digest()

    # 动态截断
    offset = hmac_result[-1] & 0x0F
    truncated = struct.unpack('>I', hmac_result[offset:offset+4])[0]
    truncated &= 0x7FFFFFFF

    # 取模得到验证码
    code = truncated % (10 ** digits)

    # 左侧补零
    return str(code).zfill(digits)


def get_remaining_seconds(period: int = 30) -> int:
    """
    获取当前周期剩余秒数

    Args:
        period: 时间步长（秒）

    Returns:
        剩余秒数（1-30）
    """
    return period - int(time.time()) % period


def verify_totp(
    code: str,
    secret: str,
    algorithm: str = 'SHA1',
    digits: int = 6,
    period: int = 30,
    window: int = 1
) -> bool:
    """
    验证 TOTP 验证码

    Args:
        code: 用户输入的验证码
        secret: Base32 编码的密钥
        algorithm: 哈希算法
        digits: 验证码位数
        period: 时间步长
        window: 验证窗口（允许前/后 N 个周期）

    Returns:
        验证是否成功
    """
    current_counter = int(time.time()) // period
    key = base64.b32decode(secret, casefold=True)
    hash_func = {
        'SHA1': hashlib.sha1,
        'SHA256': hashlib.sha256,
        'SHA512': hashlib.sha512
    }[algorithm]

    for offset in range(-window, window + 1):
        counter = current_counter + offset
        msg = struct.pack('>Q', counter)

        hmac_result = hmac.new(key, msg, hash_func).digest()

        offset_byte = hmac_result[-1] & 0x0F
        truncated = struct.unpack('>I', hmac_result[offset_byte:offset_byte+4])[0]
        truncated &= 0x7FFFFFFF
        expected = str(truncated % (10 ** digits)).zfill(digits)

        if code == expected:
            return True

    return False
