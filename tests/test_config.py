"""
配置模块单元测试
"""
import os
import sys
from pathlib import Path
from unittest.mock import patch

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import (
    DATA_DIR, DB_PATH, KEY_PATH, BACKUP_DIR,
    SALT_SIZE, KEY_SIZE, ITERATIONS, NONCE_SIZE,
    DEFAULT_ALGORITHM, DEFAULT_DIGITS, DEFAULT_PERIOD, DEFAULT_CATEGORY,
    init_data_dir, get_data_dir, get_db_path, get_key_path, get_backup_dir
)


class TestConstants:
    """测试常量定义"""

    def test_data_dir_is_path(self):
        """测试DATA_DIR是Path对象"""
        assert isinstance(DATA_DIR, Path)

    def test_db_path(self):
        """测试数据库路径"""
        assert isinstance(DB_PATH, Path)
        assert DB_PATH.name == 'mini2fa.db'

    def test_key_path(self):
        """测试密钥路径"""
        assert isinstance(KEY_PATH, Path)
        assert KEY_PATH.name == 'master.key'

    def test_backup_dir(self):
        """测试备份目录"""
        assert isinstance(BACKUP_DIR, Path)
        assert BACKUP_DIR.name == 'backups'

    def test_salt_size(self):
        """测试盐长度"""
        assert SALT_SIZE == 16
        assert isinstance(SALT_SIZE, int)

    def test_key_size(self):
        """测试密钥长度"""
        assert KEY_SIZE == 32
        assert isinstance(KEY_SIZE, int)

    def test_iterations(self):
        """测试迭代次数"""
        assert ITERATIONS == 600_000
        assert isinstance(ITERATIONS, int)

    def test_nonce_size(self):
        """测试Nonce长度"""
        assert NONCE_SIZE == 12
        assert isinstance(NONCE_SIZE, int)

    def test_default_algorithm(self):
        """测试默认算法"""
        assert DEFAULT_ALGORITHM == 'SHA1'

    def test_default_digits(self):
        """测试默认位数"""
        assert DEFAULT_DIGITS == 6

    def test_default_period(self):
        """测试默认时间步长"""
        assert DEFAULT_PERIOD == 30

    def test_default_category(self):
        """测试默认分类"""
        assert DEFAULT_CATEGORY == 'default'


class TestInitDataDir:
    """测试初始化数据目录"""

    def test_init_creates_directory(self, tmp_path):
        """测试初始化创建目录"""
        with patch('core.config.DATA_DIR', tmp_path / '.mini2fa'):
            with patch('core.config.BACKUP_DIR', tmp_path / '.mini2fa' / 'backups'):
                init_data_dir()

                assert (tmp_path / '.mini2fa').exists()
                assert (tmp_path / '.mini2fa' / 'backups').exists()

    def test_init_existing_directory(self, tmp_path):
        """测试初始化已存在的目录"""
        # 创建目录
        (tmp_path / '.mini2fa').mkdir()
        (tmp_path / '.mini2fa' / 'backups').mkdir()

        with patch('core.config.DATA_DIR', tmp_path / '.mini2fa'):
            with patch('core.config.BACKUP_DIR', tmp_path / '.mini2fa' / 'backups'):
                # 不应该抛出异常
                init_data_dir()

                assert (tmp_path / '.mini2fa').exists()


class TestGetPaths:
    """测试获取路径函数"""

    def test_get_data_dir(self):
        """测试获取数据目录"""
        result = get_data_dir()
        assert isinstance(result, Path)

    def test_get_db_path(self):
        """测试获取数据库路径"""
        result = get_db_path()
        assert isinstance(result, Path)
        assert result.name == 'mini2fa.db'

    def test_get_key_path(self):
        """测试获取密钥路径"""
        result = get_key_path()
        assert isinstance(result, Path)
        assert result.name == 'master.key'

    def test_get_backup_dir(self):
        """测试获取备份目录"""
        result = get_backup_dir()
        assert isinstance(result, Path)
        assert result.name == 'backups'


class TestPathRelationships:
    """测试路径关系"""

    def test_db_in_data_dir(self):
        """测试数据库在数据目录下"""
        assert DB_PATH.parent == DATA_DIR

    def test_key_in_data_dir(self):
        """测试密钥在数据目录下"""
        assert KEY_PATH.parent == DATA_DIR

    def test_backup_in_data_dir(self):
        """测试备份目录在数据目录下"""
        assert BACKUP_DIR.parent == DATA_DIR
