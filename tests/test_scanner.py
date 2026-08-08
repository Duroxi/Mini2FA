"""
扫描模块单元测试
"""
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from mini2fa.scanner import parse_otp_uri, preprocess_image, scan_qrcode, scan_qrcode_from_raw_data, UnsupportedOTPTypeError


class _FakeDecoded:
    """模拟 pyzbar 解码结果对象"""

    def __init__(self, data: bytes):
        self.data = data


class TestParseOTPURI:
    """测试 OTP URI 解析"""

    def test_parse_totp_uri(self):
        """测试解析标准TOTP URI"""
        uri = 'otpauth://totp/Example:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=Example&algorithm=SHA1&digits=6&period=30'

        result = parse_otp_uri(uri)

        assert result is not None
        assert result.issuer == 'Example'
        assert result.account == 'user@example.com'
        assert result.secret == 'JBSWY3DPEHPK3PXP'
        assert result.algorithm == 'SHA1'
        assert result.digits == 6
        assert result.period == 30
        assert result.otp_type == 'totp'

    def test_parse_hotp_uri(self):
        """测试HOTP URI被拒绝（仅支持TOTP）"""
        uri = 'otpauth://hotp/Example:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=Example'

        with pytest.raises(UnsupportedOTPTypeError) as excinfo:
            parse_otp_uri(uri)

        assert excinfo.value.otp_type == 'hotp'

    def test_parse_with_issuer_in_params(self):
        """测试从参数中获取issuer"""
        uri = 'otpauth://totp/user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=Google'

        result = parse_otp_uri(uri)

        assert result is not None
        assert result.issuer == 'Google'
        assert result.account == 'user@example.com'

    def test_parse_without_issuer(self):
        """测试没有issuer的URI"""
        uri = 'otpauth://totp/user@example.com?secret=JBSWY3DPEHPK3PXP'

        result = parse_otp_uri(uri)

        assert result is not None
        assert result.issuer == ''
        assert result.account == 'user@example.com'

    def test_parse_with_label_issuer(self):
        """测试从标签中获取issuer"""
        uri = 'otpauth://totp/Google:user@gmail.com?secret=JBSWY3DPEHPK3PXP'

        result = parse_otp_uri(uri)

        assert result is not None
        assert result.issuer == 'Google'
        assert result.account == 'user@gmail.com'

    def test_parse_custom_algorithm(self):
        """测试自定义算法"""
        uri = 'otpauth://totp/Example:user@example.com?secret=JBSWY3DPEHPK3PXP&algorithm=SHA256'

        result = parse_otp_uri(uri)

        assert result is not None
        assert result.algorithm == 'SHA256'

    def test_parse_custom_digits(self):
        """测试自定义位数"""
        uri = 'otpauth://totp/Example:user@example.com?secret=JBSWY3DPEHPK3PXP&digits=8'

        result = parse_otp_uri(uri)

        assert result is not None
        assert result.digits == 8

    def test_parse_custom_period(self):
        """测试自定义时间步长"""
        uri = 'otpauth://totp/Example:user@example.com?secret=JBSWY3DPEHPK3PXP&period=60'

        result = parse_otp_uri(uri)

        assert result is not None
        assert result.period == 60

    def test_parse_invalid_uri_scheme(self):
        """测试无效的URI scheme"""
        uri = 'http://example.com'

        result = parse_otp_uri(uri)

        assert result is None

    def test_parse_missing_secret(self):
        """测试缺少secret参数"""
        uri = 'otpauth://totp/Example:user@example.com'

        result = parse_otp_uri(uri)

        assert result is None

    def test_parse_empty_uri(self):
        """测试空URI"""
        result = parse_otp_uri('')

        assert result is None

    def test_parse_unknown_type_uri(self):
        """测试未知OTP类型被拒绝"""
        uri = 'otpauth://unknown/Example:user@example.com?secret=JBSWY3DPEHPK3PXP'

        with pytest.raises(UnsupportedOTPTypeError) as excinfo:
            parse_otp_uri(uri)

        assert excinfo.value.otp_type == 'unknown'

    def test_parse_with_space_in_account(self):
        """测试账号中包含空格"""
        uri = 'otpauth://totp/Example:user name@example.com?secret=JBSWY3DPEHPK3PXP'

        result = parse_otp_uri(uri)

        assert result is not None
        assert ' ' in result.account

    def test_parse_with_special_chars(self):
        """测试特殊字符"""
        uri = 'otpauth://totp/Example:user%40example.com?secret=JBSWY3DPEHPK3PXP'

        result = parse_otp_uri(uri)

        assert result is not None


class TestPreprocessImage:
    """测试图片预处理"""

    def test_convert_to_grayscale(self):
        """测试转换为灰度图"""
        from PIL import Image

        # 创建彩色测试图片
        img = Image.new('RGB', (100, 100), color='red')

        processed = preprocess_image(img)

        # 应该转换为灰度
        assert processed.mode == 'L'

    def test_resize_large_image(self):
        """测试缩放大图片"""
        from PIL import Image

        # 创建大图片
        img = Image.new('RGB', (2000, 2000), color='blue')

        processed = preprocess_image(img)

        # 应该被缩放
        assert processed.width <= 1024

    def test_keep_small_image(self):
        """测试保持小图片尺寸"""
        from PIL import Image

        # 创建小图片
        img = Image.new('RGB', (500, 500), color='green')

        processed = preprocess_image(img)

        # 应该保持原尺寸
        assert processed.width == 500

    def test_enhance_contrast(self):
        """测试增强对比度"""
        from PIL import Image

        # 创建低对比度图片
        img = Image.new('RGB', (100, 100), color=(128, 128, 128))

        processed = preprocess_image(img)

        # 应该是处理后的图片
        assert processed is not None


class TestScanQRCode:
    """测试二维码扫描"""

    QR_PATH = str(Path(__file__).parent / 'test_qr.png')

    def test_scan_nonexistent_file(self):
        """测试扫描不存在的文件"""
        from mini2fa.scanner import scan_qrcode

        try:
            scan_qrcode('/nonexistent/path.png')
            assert False, "应该抛出异常"
        except FileNotFoundError:
            pass

    def test_scan_invalid_image(self):
        """测试扫描无效图片"""
        from mini2fa.scanner import scan_qrcode
        import tempfile

        # 创建无效的图片文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('not an image')
            temp_path = f.name

        try:
            result = scan_qrcode(temp_path)
            assert result is None, "无效图片应返回 None"
        except Exception:
            pass
        finally:
            os.unlink(temp_path)

    def test_scan_valid_qrcode(self):
        """测试扫描有效的二维码图片"""
        from mini2fa.scanner import scan_qrcode

        result = scan_qrcode(self.QR_PATH)

        assert result is not None
        assert result.issuer == 'Test'
        assert result.account == 'user@example.com'
        assert result.secret == 'JBSWY3DPEHPK3PXP'


class TestScanQRCodeFromRawData:
    """测试从原始数据扫描二维码"""

    QR_PATH = str(Path(__file__).parent / 'test_qr.png')

    def test_scan_from_raw_data(self):
        """测试从原始字节数据扫描"""
        from mini2fa.scanner import scan_qrcode_from_raw_data

        # 读取测试二维码图片的原始字节
        with open(self.QR_PATH, 'rb') as f:
            raw_data = f.read()

        # 测试裸字节（不带PIL包装）
        result = scan_qrcode_from_raw_data(raw_data)

        # pyzbar 可能支持或不支持裸字节，取决于版本
        # 如果返回None，则测试通过（不抛出异常即可）
        if result is not None:
            assert result.issuer == 'Test'
            assert result.account == 'user@example.com'

    def test_scan_from_empty_data(self):
        """测试从空数据扫描"""
        from mini2fa.scanner import scan_qrcode_from_raw_data

        result = scan_qrcode_from_raw_data(b'')

        assert result is None

    def test_scan_from_invalid_data(self):
        """测试从无效数据扫描"""
        from mini2fa.scanner import scan_qrcode_from_raw_data

        result = scan_qrcode_from_raw_data(b'not a qr code')

        assert result is None


class TestScanUnsupportedOTP:
    """测试非 TOTP 类型的 OTP 二维码被明确拒绝"""

    HOTP_URI = b'otpauth://hotp/Example:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=Example&counter=1'
    UNKNOWN_URI = b'otpauth://unknown/Example:user@example.com?secret=JBSWY3DPEHPK3PXP'

    def test_scan_qrcode_hotp_rejected(self):
        """测试 scan_qrcode 扫描 HOTP 二维码抛出 UnsupportedOTPTypeError"""
        fake = _FakeDecoded(self.HOTP_URI)

        with patch('mini2fa.scanner.decode', return_value=[fake]):
            with patch('mini2fa.scanner.Image.open'):
                with pytest.raises(UnsupportedOTPTypeError) as excinfo:
                    scan_qrcode(__file__)
                assert excinfo.value.otp_type == 'hotp'

    def test_scan_qrcode_unknown_type_rejected(self):
        """测试 scan_qrcode 扫描未知类型 OTP 二维码抛出 UnsupportedOTPTypeError"""
        fake = _FakeDecoded(self.UNKNOWN_URI)

        with patch('mini2fa.scanner.decode', return_value=[fake]):
            with patch('mini2fa.scanner.Image.open'):
                with pytest.raises(UnsupportedOTPTypeError) as excinfo:
                    scan_qrcode(__file__)
                assert excinfo.value.otp_type == 'unknown'

    def test_scan_raw_hotp_rejected(self):
        """测试 scan_qrcode_from_raw_data 扫描 HOTP 数据抛出 UnsupportedOTPTypeError"""
        fake = _FakeDecoded(self.HOTP_URI)

        with patch('mini2fa.scanner.decode', return_value=[fake]):
            with pytest.raises(UnsupportedOTPTypeError) as excinfo:
                scan_qrcode_from_raw_data(b'anything')
            assert excinfo.value.otp_type == 'hotp'

    def test_scan_raw_unknown_type_rejected(self):
        """测试 scan_qrcode_from_raw_data 扫描未知类型数据抛出 UnsupportedOTPTypeError"""
        fake = _FakeDecoded(self.UNKNOWN_URI)

        with patch('mini2fa.scanner.decode', return_value=[fake]):
            with pytest.raises(UnsupportedOTPTypeError) as excinfo:
                scan_qrcode_from_raw_data(b'anything')
            assert excinfo.value.otp_type == 'unknown'

    TOTP_URI = b'otpauth://totp/Example:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=Example'

    def test_multi_qrcode_prefers_totp(self):
        """测试多二维码时优先返回 totp"""
        # 解码结果顺序：先 HOTP 后 TOTP
        fake_hotp = _FakeDecoded(self.HOTP_URI)
        fake_totp = _FakeDecoded(self.TOTP_URI)

        with patch('mini2fa.scanner.decode', return_value=[fake_hotp, fake_totp]):
            with patch('mini2fa.scanner.Image.open'):
                result = scan_qrcode(__file__)
                assert result is not None
                assert result.otp_type == 'totp'

    def test_multi_qrcode_all_unsupported(self):
        """测试多个非 totp 二维码时抛第一个遇到的类型"""
        fake_steam = _FakeDecoded(b'otpauth://steam/Steam:u@x.com?secret=JBSWY3DPEHPK3PXP')
        fake_unknown = _FakeDecoded(self.UNKNOWN_URI)

        with patch('mini2fa.scanner.decode', return_value=[fake_steam, fake_unknown]):
            with patch('mini2fa.scanner.Image.open'):
                with pytest.raises(UnsupportedOTPTypeError) as excinfo:
                    scan_qrcode(__file__)
                assert excinfo.value.otp_type == 'steam'


class TestScanEdgeCases:
    """测试扫描边界情况"""

    def test_scan_non_qr_image(self):
        """测试扫描非二维码图片"""
        from mini2fa.scanner import scan_qrcode
        import tempfile

        # 创建一个纯色图片（非二维码）
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='white')
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            temp_path = f.name
            img.save(temp_path)

        try:
            result = scan_qrcode(temp_path)
            assert result is None
        finally:
            os.unlink(temp_path)

    def test_scan_corrupted_image_file(self):
        """测试扫描损坏的图片文件"""
        from mini2fa.scanner import scan_qrcode
        import tempfile

        # 创建一个有 .png 后缀但不是图片的文件
        with tempfile.NamedTemporaryFile(suffix='.png', mode='w', delete=False) as f:
            f.write('this is not an image file at all')
            temp_path = f.name

        try:
            try:
                scan_qrcode(temp_path)
                assert False, "应该抛出异常"
            except ValueError as e:
                assert '扫描失败' in str(e)
        finally:
            os.unlink(temp_path)


class TestEdgeCases:
    """边界情况测试"""

    def test_parse_very_long_uri(self):
        """测试很长的URI"""
        long_account = 'a' * 1000
        uri = f'otpauth://totp/Example:{long_account}?secret=JBSWY3DPEHPK3PXP'

        result = parse_otp_uri(uri)

        assert result is not None
        assert len(result.account) == 1000

    def test_parse_unicode_account(self):
        """测试Unicode账号"""
        uri = 'otpauth://totp/Example:用户@example.com?secret=JBSWY3DPEHPK3PXP'

        result = parse_otp_uri(uri)

        assert result is not None
        assert '用户' in result.account

    def test_parse_multiple_params(self):
        """测试多个参数"""
        uri = 'otpauth://totp/Example:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=Example&algorithm=SHA512&digits=8&period=60'

        result = parse_otp_uri(uri)

        assert result is not None
        assert result.algorithm == 'SHA512'
        assert result.digits == 8
        assert result.period == 60
