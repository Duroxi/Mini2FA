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


class UnsupportedOTPTypeError(Exception):
    """OTP URI 类型不是 TOTP 时抛出（如 HOTP、STEAM 等）"""

    def __init__(self, otp_type: str):
        self.otp_type = otp_type
        super().__init__(f"不支持的 OTP 类型: {otp_type}")


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

    Raises:
        UnsupportedOTPTypeError: URI 类型不是 totp（如 hotp、steam 等）

    URI 格式示例:
        otpauth://totp/Example:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=Example&algorithm=SHA1&digits=6&period=30
    """
    # 验证 URI 格式
    if not uri.startswith('otpauth://'):
        return None

    try:
        parsed = urlparse(uri)
        params = parse_qs(parsed.query)

        # 校验必要参数
        if 'secret' not in params:
            return None

        # 校验 OTP 类型（仅支持 totp）
        otp_type = parsed.netloc
        if otp_type != 'totp':
            raise UnsupportedOTPTypeError(otp_type)

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
            otp_type=otp_type  # 仅 'totp'
        )
    except UnsupportedOTPTypeError:
        raise  # 类型错误穿透，由调用方给出明确提示
    except Exception:
        return None


def _extract_otp_info(decoded_objects) -> Optional[OTPAccountInfo]:
    """从 pyzbar 解码结果中提取第一个可解析的 OTP URI 信息

    若图片含多个二维码：优先返回 totp 类型；存在非 totp 类型时
    记下第一个遇到的类型，全部非 totp 才抛出。
    """
    first_unsupported = None
    for obj in decoded_objects:
        data = obj.data.decode('utf-8')
        if not data.startswith('otpauth://'):
            continue
        try:
            return parse_otp_uri(data)
        except UnsupportedOTPTypeError as e:
            if first_unsupported is None:
                first_unsupported = e.otp_type
    if first_unsupported is not None:
        raise UnsupportedOTPTypeError(first_unsupported)
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
        UnsupportedOTPTypeError: 二维码是 HOTP 等非 TOTP 类型
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

        return _extract_otp_info(decoded_objects)

    except UnsupportedOTPTypeError:
        raise
    except Exception as e:
        raise ValueError(f"扫描失败: {e}")


def scan_qrcode_from_raw_data(data: bytes) -> Optional[OTPAccountInfo]:
    """
    从原始数据中解析二维码

    Args:
        data: 原始字节数据

    Returns:
        OTPAccountInfo 对象，或 None

    Raises:
        UnsupportedOTPTypeError: 数据是 HOTP 等非 TOTP 类型
    """
    try:
        decoded_objects = decode(data)
        return _extract_otp_info(decoded_objects)
    except UnsupportedOTPTypeError:
        raise
    except Exception:
        return None
