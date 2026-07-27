"""
Pytest 配置文件
"""
import os
import sys
import tempfile
from pathlib import Path

# 添加项目 src 路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import pytest

from mini2fa.crypto import CryptoManager
from mini2fa.storage import StorageManager


@pytest.fixture
def tmp_dir():
    """创建临时目录"""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def crypto_manager(tmp_dir):
    """创建加密管理器实例"""
    key_path = os.path.join(tmp_dir, 'master.key')
    crypto = CryptoManager(key_path)
    crypto.initialize('test_password', 'test_hint')
    return crypto


@pytest.fixture
def storage_manager(tmp_dir, crypto_manager):
    """创建存储管理器实例"""
    db_path = os.path.join(tmp_dir, 'test.db')
    return StorageManager(db_path, crypto_manager)


@pytest.fixture
def sample_account_info():
    """示例账号信息"""
    from mini2fa.models import OTPAccountInfo
    return OTPAccountInfo(
        issuer='Google',
        account='user@gmail.com',
        secret='JBSWY3DPEHPK3PXP',
        algorithm='SHA1',
        digits=6,
        period=30,
        otp_type='totp'
    )
