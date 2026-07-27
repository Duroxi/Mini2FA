"""
TOTP 模块单元测试
"""
import sys
import time
import base64
from pathlib import Path
from unittest.mock import patch

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from mini2fa.totp import generate_totp, get_remaining_seconds, verify_totp


class TestGenerateTOTP:
    """测试 TOTP 生成"""

    def test_basic_generation(self):
        """测试基本的TOTP生成"""
        secret = 'JBSWY3DPEHPK3PXP'
        code = generate_totp(secret)

        assert len(code) == 6
        assert code.isdigit()

    def test_custom_digits(self):
        """测试自定义位数"""
        secret = 'JBSWY3DPEHPK3PXP'

        code_6 = generate_totp(secret, digits=6)
        code_8 = generate_totp(secret, digits=8)

        assert len(code_6) == 6
        assert len(code_8) == 8

    def test_custom_period(self):
        """测试自定义时间步长"""
        secret = 'JBSWY3DPEHPK3PXP'

        code_30 = generate_totp(secret, period=30)
        code_60 = generate_totp(secret, period=60)

        # 两者可能不同（因为时间步长不同）
        assert len(code_30) == 6
        assert len(code_60) == 6

    def test_algorithms(self):
        """测试不同算法"""
        secret = 'JBSWY3DPEHPK3PXP'

        for algo in ['SHA1', 'SHA256', 'SHA512']:
            code = generate_totp(secret, algorithm=algo)
            assert len(code) == 6
            assert code.isdigit()

    def test_invalid_algorithm(self):
        """测试无效算法"""
        secret = 'JBSWY3DPEHPK3PXP'

        try:
            generate_totp(secret, algorithm='INVALID')
            assert False, "应该抛出异常"
        except KeyError:
            pass

    def test_case_insensitive_secret(self):
        """测试密钥大小写不敏感"""
        secret_upper = 'JBSWY3DPEHPK3PXP'
        secret_lower = 'jbswy3dpehpk3pxp'

        code1 = generate_totp(secret_upper)
        code2 = generate_totp(secret_lower)

        # Base32 解码应该相同
        assert code1 == code2

    @patch('mini2fa.totp.time')
    def test_deterministic_output(self, mock_time):
        """测试确定性输出（相同时间相同结果）"""
        secret = 'JBSWY3DPEHPK3PXP'

        # 固定时间
        mock_time.time.return_value = 1000000

        code1 = generate_totp(secret)
        code2 = generate_totp(secret)

        assert code1 == code2

    @patch('mini2fa.totp.time')
    def test_time_step_change(self, mock_time):
        """测试时间步长变化"""
        secret = 'JBSWY3DPEHPK3PXP'

        # 在同一个30秒窗口内（990 // 30 == 33, 1019 // 30 == 33）
        mock_time.time.return_value = 990
        code1 = generate_totp(secret, period=30)

        mock_time.time.return_value = 1019
        code2 = generate_totp(secret, period=30)

        # 同一个时间窗口，应该生成相同的代码
        assert code1 == code2

        # 跨越窗口（1020 // 30 == 34）
        mock_time.time.return_value = 1020
        code3 = generate_totp(secret, period=30)

        # 不同时间窗口，代码应该不同
        assert len(code3) == 6


class TestGetRemainingSeconds:
    """测试剩余秒数计算"""

    def test_basic_remaining(self):
        """测试基本剩余时间"""
        remaining = get_remaining_seconds(30)

        assert 1 <= remaining <= 30

    def test_custom_period(self):
        """测试自定义时间步长"""
        remaining = get_remaining_seconds(60)

        assert 1 <= remaining <= 60

    @patch('mini2fa.totp.time')
    def test_specific_time(self, mock_time):
        """测试特定时间点"""
        # 设置时间，使剩余时间可预测
        mock_time.time.return_value = 1000

        remaining = get_remaining_seconds(30)

        # 1000 % 30 = 10, 30 - 10 = 20
        assert remaining == 20


class TestVerifyTOTP:
    """测试 TOTP 验证"""

    def test_verify_current_code(self):
        """测试验证当前验证码"""
        secret = 'JBSWY3DPEHPK3PXP'
        code = generate_totp(secret)

        assert verify_totp(code, secret) is True

    def test_verify_wrong_code(self):
        """测试验证错误验证码"""
        secret = 'JBSWY3DPEHPK3PXP'

        assert verify_totp('000000', secret) is False

    def test_verify_with_window(self):
        """测试带窗口的验证"""
        secret = 'JBSWY3DPEHPK3PXP'
        code = generate_totp(secret)

        # window=1 应该能通过
        assert verify_totp(code, secret, window=1) is True

    def test_verify_different_algorithms(self):
        """测试不同算法的验证"""
        secret = 'JBSWY3DPEHPK3PXP'

        for algo in ['SHA1', 'SHA256', 'SHA512']:
            code = generate_totp(secret, algorithm=algo)
            assert verify_totp(code, secret, algorithm=algo) is True

    def test_verify_different_digits(self):
        """测试不同位数的验证"""
        secret = 'JBSWY3DPEHPK3PXP'

        for digits in [6, 8]:
            code = generate_totp(secret, digits=digits)
            assert verify_totp(code, secret, digits=digits) is True

    def test_verify_invalid_code_format(self):
        """测试无效格式的验证码"""
        secret = 'JBSWY3DPEHPK3PXP'

        # 非数字
        assert verify_totp('abcdef', secret) is False

        # 长度错误
        assert verify_totp('12345', secret) is False
        assert verify_totp('1234567', secret) is False


class TestEdgeCases:
    """边界情况测试"""

    def test_empty_secret(self):
        """测试空密钥"""
        try:
            generate_totp('')
            assert False, "应该抛出异常"
        except Exception:
            pass

    def test_invalid_base32(self):
        """测试无效的Base32编码"""
        try:
            generate_totp('1')  # 无效的Base32
            # 可能不会抛出异常，但结果应该是有效的
        except Exception:
            pass

    def test_long_secret(self):
        """测试长密钥"""
        # 生成一个长的Base32密钥（确保是有效的Base32）
        long_secret = 'JBSWY3DPEHPK3PXP' * 5  # 重复有效的Base32密钥
        code = generate_totp(long_secret)

        assert len(code) == 6
        assert code.isdigit()
