"""
配置管理
"""
import os
from pathlib import Path


# 数据目录（存储在用户主目录下的 .mini2fa）
DATA_DIR = Path.home() / '.mini2fa'
DB_PATH = DATA_DIR / 'mini2fa.db'
KEY_PATH = DATA_DIR / 'master.key'
BACKUP_DIR = DATA_DIR / 'backups'

# 安全参数
SALT_SIZE = 16          # 盐长度
KEY_SIZE = 32           # 密钥长度（256-bit）
ITERATIONS = 600_000    # PBKDF2 迭代次数（OWASP 推荐）
NONCE_SIZE = 12         # GCM Nonce 长度

# 默认 OTP 参数
DEFAULT_ALGORITHM = 'SHA1'
DEFAULT_DIGITS = 6
DEFAULT_PERIOD = 30
DEFAULT_CATEGORY = 'default'


def init_data_dir():
    """初始化数据目录"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(exist_ok=True)


def get_data_dir() -> Path:
    """获取数据目录路径"""
    return DATA_DIR


def get_db_path() -> Path:
    """获取数据库文件路径"""
    return DB_PATH


def get_key_path() -> Path:
    """获取主密钥文件路径"""
    return KEY_PATH


def get_backup_dir() -> Path:
    """获取备份目录路径"""
    return BACKUP_DIR
