"""
二维码扫描模块

从图片文件中识别二维码并解析 OTP URI
"""
import os
from typing import Optional
from urllib.parse import urlparse, parse_qs

from pyzbar.pyzbar import decode
from PIL import Image, ImageEnhance

from .models import OTPAccountInfo
from .config import DEFAULT_ALGORITHM, DEFAULT_DIGITS, DEFAULT_PERIOD


def preprocess_image(image: Image.Image) -> Image.Image:
    """
    图片预处理，提高识别率

    1. 转换为灰度图
    2. 调整对比度
    3. 缩放到合理尺寸（如果太大）

    Args:
        image: 原始图片

    Returns:
        预处理后的图片
    """
    # 转灰度
    gray = image.convert('L')

    # 增强对比度
    enhancer = ImageEnhance.Contrast(gray)
    enhanced = enhancer.enhance(2.0)

    # 缩放（如果宽度超过1024）
    if enhanced.width > 1024:
        ratio = 1024 / enhanced.width
        new_size = (1024, int(enhanced.height * ratio))
        enhanced = enhanced.resize(new_size, Image.Resampling.LANCZOS)

    return enhanced


def parse_otp_uri(uri: str) -> Optional[OTPAccountInfo]:
    """
    解析 otpauth:// URI

    Args:
        uri: OTP URI 字符串

    Returns:
        OTPAccountInfo 对象，或 None（格式无效）

    URI 格式示例:
        otpauth://totp/Example:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=Example&algorithm=SHA1&digits=6&period=30
    """
    # 验证 URI 格式
    if not uri.startswith('otpauth://'):
        return None

    try:
        parsed = urlparse(uri)
        params = parse_qs(parsed.query)

        # 验证必要参数
        if 'secret' not in params:
            return None

        # 提取标签（issuer:account 格式）
        label = parsed.path.lstrip('/')
        if ':' in label:
            default_issuer, account = label.split(':', 1)
        else:
            default_issuer = ''
            account = label

        issuer = params.get('issuer', [default_issuer])[0] or default_issuer

        return OTPAccountInfo(
            issuer=issuer,
            account=account,
            secret=params['secret'][0],
            algorithm=params.get('algorithm', [DEFAULT_ALGORITHM])[0],
            digits=int(params.get('digits', [DEFAULT_DIGITS])[0]),
            period=int(params.get('period', [DEFAULT_PERIOD])[0]),
            otp_type=parsed.netloc  # 'totp' 或 'hotp'
        )
    except Exception:
        return None


def scan_qrcode(image_path: str) -> Optional[OTPAccountInfo]:
    """
    从图片文件中扫描二维码并解析 OTP URI

    Args:
        image_path: 图片文件路径

    Returns:
        OTPAccountInfo 对象，或 None（识别失败）

    Raises:
        FileNotFoundError: 文件不存在
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"图片文件不存在: {image_path}")

    try:
        image = Image.open(image_path)

        # 尝试直接识别
        decoded_objects = decode(image)

        # 如果直接识别失败，尝试预处理后识别
        if not decoded_objects:
            processed = preprocess_image(image)
            decoded_objects = decode(processed)

        # 查找有效的 OTP URI
        for obj in decoded_objects:
            data = obj.data.decode('utf-8')
            if data.startswith('otpauth://'):
                return parse_otp_uri(data)

        return None  # 未找到有效二维码

    except Exception as e:
        raise ValueError(f"扫描失败: {e}")


def scan_qrcode_from_raw_data(data: bytes) -> Optional[OTPAccountInfo]:
    """
    从原始数据中解析二维码

    Args:
        data: 原始字节数据

    Returns:
        OTPAccountInfo 对象，或 None
    """
    try:
        decoded_objects = decode(data)
        for obj in decoded_objects:
            uri = obj.data.decode('utf-8')
            if uri.startswith('otpauth://'):
                return parse_otp_uri(uri)
        return None
    except Exception:
        return None
