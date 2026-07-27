"""
数据模型单元测试
"""
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from mini2fa.models import Account, OTPAccountInfo


class TestAccount:
    """测试 Account 数据模型"""

    def test_create_account(self):
        """测试创建 Account 对象"""
        account = Account(
            id=1,
            issuer='Google',
            account='user@gmail.com',
            secret_encrypted='encrypted_secret',
            algorithm='SHA1',
            digits=6,
            period=30,
            category='default',
            notes='Test',
            created_at='2026-01-01 00:00:00',
            updated_at='2026-01-01 00:00:00'
        )

        assert account.id == 1
        assert account.issuer == 'Google'
        assert account.account == 'user@gmail.com'
        assert account.secret_encrypted == 'encrypted_secret'
        assert account.algorithm == 'SHA1'
        assert account.digits == 6
        assert account.period == 30
        assert account.category == 'default'
        assert account.notes == 'Test'
        assert account.created_at == '2026-01-01 00:00:00'
        assert account.updated_at == '2026-01-01 00:00:00'

    def test_account_attributes(self):
        """测试 Account 属性类型"""
        account = Account(
            id=1,
            issuer='Google',
            account='user@gmail.com',
            secret_encrypted='encrypted',
            algorithm='SHA1',
            digits=6,
            period=30,
            category='default',
            notes='',
            created_at='2026-01-01',
            updated_at='2026-01-01'
        )

        assert isinstance(account.id, int)
        assert isinstance(account.issuer, str)
        assert isinstance(account.account, str)
        assert isinstance(account.secret_encrypted, str)
        assert isinstance(account.algorithm, str)
        assert isinstance(account.digits, int)
        assert isinstance(account.period, int)
        assert isinstance(account.category, str)
        assert isinstance(account.notes, str)
        assert isinstance(account.created_at, str)
        assert isinstance(account.updated_at, str)

    def test_account_defaults(self):
        """测试 Account 默认值"""
        account = Account(
            id=1,
            issuer='Google',
            account='user@gmail.com',
            secret_encrypted='encrypted',
            algorithm='SHA1',
            digits=6,
            period=30,
            category='default',
            notes='',
            created_at='2026-01-01',
            updated_at='2026-01-01'
        )

        # 检查默认值
        assert account.algorithm == 'SHA1'
        assert account.digits == 6
        assert account.period == 30
        assert account.category == 'default'

    def test_account_equality(self):
        """测试 Account 相等性"""
        account1 = Account(
            id=1,
            issuer='Google',
            account='user@gmail.com',
            secret_encrypted='encrypted',
            algorithm='SHA1',
            digits=6,
            period=30,
            category='default',
            notes='',
            created_at='2026-01-01',
            updated_at='2026-01-01'
        )

        account2 = Account(
            id=1,
            issuer='Google',
            account='user@gmail.com',
            secret_encrypted='encrypted',
            algorithm='SHA1',
            digits=6,
            period=30,
            category='default',
            notes='',
            created_at='2026-01-01',
            updated_at='2026-01-01'
        )

        # dataclass 自动生成 __eq__
        assert account1 == account2

    def test_account_inequality(self):
        """测试 Account 不相等"""
        account1 = Account(
            id=1,
            issuer='Google',
            account='user@gmail.com',
            secret_encrypted='encrypted',
            algorithm='SHA1',
            digits=6,
            period=30,
            category='default',
            notes='',
            created_at='2026-01-01',
            updated_at='2026-01-01'
        )

        account2 = Account(
            id=2,  # 不同的ID
            issuer='Google',
            account='user@gmail.com',
            secret_encrypted='encrypted',
            algorithm='SHA1',
            digits=6,
            period=30,
            category='default',
            notes='',
            created_at='2026-01-01',
            updated_at='2026-01-01'
        )

        assert account1 != account2


class TestOTPAccountInfo:
    """测试 OTPAccountInfo 数据模型"""

    def test_create_otp_account_info(self):
        """测试创建 OTPAccountInfo 对象"""
        info = OTPAccountInfo(
            issuer='Google',
            account='user@gmail.com',
            secret='JBSWY3DPEHPK3PXP',
            algorithm='SHA1',
            digits=6,
            period=30,
            otp_type='totp'
        )

        assert info.issuer == 'Google'
        assert info.account == 'user@gmail.com'
        assert info.secret == 'JBSWY3DPEHPK3PXP'
        assert info.algorithm == 'SHA1'
        assert info.digits == 6
        assert info.period == 30
        assert info.otp_type == 'totp'

    def test_otp_account_info_attributes(self):
        """测试 OTPAccountInfo 属性类型"""
        info = OTPAccountInfo(
            issuer='Google',
            account='user@gmail.com',
            secret='JBSWY3DPEHPK3PXP',
            algorithm='SHA1',
            digits=6,
            period=30,
            otp_type='totp'
        )

        assert isinstance(info.issuer, str)
        assert isinstance(info.account, str)
        assert isinstance(info.secret, str)
        assert isinstance(info.algorithm, str)
        assert isinstance(info.digits, int)
        assert isinstance(info.period, int)
        assert isinstance(info.otp_type, str)

    def test_otp_account_info_defaults(self):
        """测试 OTPAccountInfo 默认值"""
        info = OTPAccountInfo(
            issuer='Google',
            account='user@gmail.com',
            secret='JBSWY3DPEHPK3PXP',
            algorithm='SHA1',
            digits=6,
            period=30,
            otp_type='totp'
        )

        assert info.algorithm == 'SHA1'
        assert info.digits == 6
        assert info.period == 30

    def test_otp_account_info_equality(self):
        """测试 OTPAccountInfo 相等性"""
        info1 = OTPAccountInfo(
            issuer='Google',
            account='user@gmail.com',
            secret='JBSWY3DPEHPK3PXP',
            algorithm='SHA1',
            digits=6,
            period=30,
            otp_type='totp'
        )

        info2 = OTPAccountInfo(
            issuer='Google',
            account='user@gmail.com',
            secret='JBSWY3DPEHPK3PXP',
            algorithm='SHA1',
            digits=6,
            period=30,
            otp_type='totp'
        )

        assert info1 == info2

    def test_otp_account_info_inequality(self):
        """测试 OTPAccountInfo 不相等"""
        info1 = OTPAccountInfo(
            issuer='Google',
            account='user@gmail.com',
            secret='JBSWY3DPEHPK3PXP',
            algorithm='SHA1',
            digits=6,
            period=30,
            otp_type='totp'
        )

        info2 = OTPAccountInfo(
            issuer='GitHub',  # 不同的issuer
            account='user@gmail.com',
            secret='JBSWY3DPEHPK3PXP',
            algorithm='SHA1',
            digits=6,
            period=30,
            otp_type='totp'
        )

        assert info1 != info2


class TestModelIntegration:
    """模型集成测试"""

    def test_account_from_otp_info(self):
        """测试从 OTPAccountInfo 创建 Account"""
        info = OTPAccountInfo(
            issuer='Google',
            account='user@gmail.com',
            secret='JBSWY3DPEHPK3PXP',
            algorithm='SHA1',
            digits=6,
            period=30,
            otp_type='totp'
        )

        # 模拟从 OTPAccountInfo 创建 Account 的场景
        account = Account(
            id=1,
            issuer=info.issuer,
            account=info.account,
            secret_encrypted='encrypted_' + info.secret,
            algorithm=info.algorithm,
            digits=info.digits,
            period=info.period,
            category='default',
            notes='',
            created_at='2026-01-01',
            updated_at='2026-01-01'
        )

        assert account.issuer == info.issuer
        assert account.account == info.account
        assert account.algorithm == info.algorithm
        assert account.digits == info.digits
        assert account.period == info.period
