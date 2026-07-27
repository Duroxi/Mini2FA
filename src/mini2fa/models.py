"""
数据模型定义
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Account:
    """账号数据模型"""
    id: int
    issuer: str           # 服务提供商（如 Google、GitHub）
    account: str          # 账号名（如 user@example.com）
    secret_encrypted: str # 加密后的密钥
    algorithm: str        # 算法：SHA1/SHA256/SHA512
    digits: int           # 验证码位数
    period: int           # 时间步长（秒）
    category: str         # 分类
    notes: str            # 备注
    created_at: str       # 创建时间
    updated_at: str       # 更新时间


@dataclass
class OTPAccountInfo:
    """从二维码解析出的 OTP 账号信息"""
    issuer: str           # 服务提供商
    account: str          # 账号名
    secret: str           # 明文密钥（Base32）
    algorithm: str        # 哈希算法
    digits: int           # 验证码位数
    period: int           # 时间步长
    otp_type: str         # OTP 类型：totp 或 hotp
