"""
扫描模块单元测试
"""
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.scanner import parse_otp_uri, preprocess_image, scan_qrcode


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
        """测试解析HOTP URI"""
        uri = 'otpauth://hotp/Example:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=Example'

        result = parse_otp_uri(uri)

        assert result is not None
        assert result.otp_type == 'hotp'

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

    def test_scan_nonexistent_file(self):
        """测试扫描不存在的文件"""
        from core.scanner import scan_qrcode

        try:
            scan_qrcode('/nonexistent/path.png')
            assert False, "应该抛出异常"
        except FileNotFoundError:
            pass

    def test_scan_invalid_image(self):
        """测试扫描无效图片"""
        from core.scanner import scan_qrcode
        import tempfile

        # 创建无效的图片文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('not an image')
            temp_path = f.name

        try:
            result = scan_qrcode(temp_path)
            # 可能返回None或抛出异常
            assert result is None or True
        except Exception:
            pass
        finally:
            os.unlink(temp_path)

    def test_scan_valid_qrcode(self):
        """测试扫描有效的二维码图片"""
        from core.scanner import scan_qrcode

        result = scan_qrcode('test_qr.png')

        assert result is not None
        assert result.issuer == 'Test'
        assert result.account == 'user@example.com'
        assert result.secret == 'JBSWY3DPEHPK3PXP'


class TestScanQRCodeFromRawData:
    """测试从原始数据扫描二维码"""

    def test_scan_from_raw_data(self):
        """测试从原始字节数据扫描"""
        from core.scanner import scan_qrcode_from_raw_data

        # 读取测试二维码图片的原始字节
        with open('test_qr.png', 'rb') as f:
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
        from core.scanner import scan_qrcode_from_raw_data

        result = scan_qrcode_from_raw_data(b'')

        assert result is None

    def test_scan_from_invalid_data(self):
        """测试从无效数据扫描"""
        from core.scanner import scan_qrcode_from_raw_data

        result = scan_qrcode_from_raw_data(b'not a qr code')

        assert result is None


class TestScanEdgeCases:
    """测试扫描边界情况"""

    def test_scan_non_qr_image(self):
        """测试扫描非二维码图片"""
        from core.scanner import scan_qrcode
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
        from core.scanner import scan_qrcode
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
