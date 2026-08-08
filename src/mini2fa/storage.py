"""
数据存储模块

使用 SQLite 存储账号数据，支持 JSON 导入导出
"""
import sqlite3
import json
from datetime import datetime
from typing import List, Optional

from .models import Account
from .crypto import CryptoManager


class StorageCorruptedError(Exception):
    """数据库文件损坏或无法读取时抛出"""


def _connect(db_path: str):
    """
    连接数据库，损坏/锁定异常统一转 StorageCorruptedError
    """
    try:
        return sqlite3.connect(db_path)
    except sqlite3.Error as e:
        raise StorageCorruptedError(f"数据库无法打开: {e}")


def _guard_errors(func):
    """装饰器：把 sqlite3.Error（损坏/锁定/表异常）统一转 StorageCorruptedError"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except sqlite3.Error as e:
            raise StorageCorruptedError(f"数据库损坏或操作失败: {e}")
    return wrapper


# 数据库表结构
CREATE_TABLE_SQL = '''
CREATE TABLE IF NOT EXISTS accounts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    issuer          TEXT NOT NULL,
    account         TEXT NOT NULL,
    secret_encrypted TEXT NOT NULL,
    algorithm       TEXT DEFAULT 'SHA1',
    digits          INTEGER DEFAULT 6,
    period          INTEGER DEFAULT 30,
    category        TEXT DEFAULT 'default',
    notes           TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(issuer, account)
);
'''

CREATE_INDEX1_SQL = '''
CREATE INDEX IF NOT EXISTS idx_accounts_issuer ON accounts(issuer);
'''

CREATE_INDEX2_SQL = '''
CREATE INDEX IF NOT EXISTS idx_accounts_category ON accounts(category);
'''

CREATE_TRIGGER_SQL = '''
CREATE TRIGGER IF NOT EXISTS update_accounts_timestamp
AFTER UPDATE ON accounts
BEGIN
    UPDATE accounts SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
'''


class StorageManager:
    """存储管理器"""

    def __init__(self, db_path: str, crypto_manager: CryptoManager):
        """
        Args:
            db_path: 数据库文件路径
            crypto_manager: 加密管理器实例
        """
        self.db_path = db_path
        self.crypto = crypto_manager
        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        try:
            with _connect(self.db_path) as conn:
                conn.execute(CREATE_TABLE_SQL)
                conn.execute(CREATE_INDEX1_SQL)
                conn.execute(CREATE_INDEX2_SQL)
                conn.execute(CREATE_TRIGGER_SQL)
                conn.commit()
        except StorageCorruptedError:
            raise
        except sqlite3.Error as e:
            raise StorageCorruptedError(f"数据库损坏或无法初始化: {e}")

    @_guard_errors
    def add_account(
        self,
        issuer: str,
        account: str,
        secret: str,
        algorithm: str = 'SHA1',
        digits: int = 6,
        period: int = 30,
        category: str = 'default',
        notes: str = ''
    ) -> int:
        """
        添加新账号

        Args:
            issuer: 服务提供商
            account: 账号名
            secret: OTP 密钥（明文，将自动加密）
            algorithm: 哈希算法
            digits: 验证码位数
            period: 时间步长
            category: 分类
            notes: 备注

        Returns:
            新账号 ID

        Raises:
            ValueError: 账号已存在
        """
        # 加密密钥
        encrypted_secret = self.crypto.encrypt(secret)

        with _connect(self.db_path) as conn:
            try:
                cursor = conn.execute('''
                    INSERT INTO accounts
                    (issuer, account, secret_encrypted, algorithm, digits, period, category, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (issuer, account, encrypted_secret, algorithm, digits, period, category, notes))
                conn.commit()
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                raise ValueError(f"账号已存在: {issuer}:{account}")

    @_guard_errors
    def get_account(self, account_id: int) -> Optional[Account]:
        """获取单个账号"""
        with _connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute('SELECT * FROM accounts WHERE id = ?', (account_id,)).fetchone()
            if row:
                return Account(**dict(row))
            return None

    @_guard_errors
    def get_all_accounts(self, category: str = None) -> List[Account]:
        """获取所有账号"""
        with _connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if category:
                rows = conn.execute(
                    'SELECT * FROM accounts WHERE category = ? ORDER BY issuer, account',
                    (category,)
                ).fetchall()
            else:
                rows = conn.execute(
                    'SELECT * FROM accounts ORDER BY issuer, account'
                ).fetchall()
            return [Account(**dict(row)) for row in rows]

    def get_secret(self, account_id: int) -> str:
        """解密并获取密钥"""
        account = self.get_account(account_id)
        if not account:
            raise ValueError(f"账号不存在: {account_id}")
        return self.crypto.decrypt(account.secret_encrypted)

    @_guard_errors
    def find_by_identity(self, issuer: str, account: str) -> Optional[Account]:
        """按 (issuer, account) 精确查找账号"""
        with _connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                'SELECT * FROM accounts WHERE issuer = ? AND account = ?',
                (issuer, account)
            ).fetchone()
            if row:
                return Account(**dict(row))
            return None

    @_guard_errors
    def overwrite_account(self, account_id: int, secret_encrypted: str,
                          algorithm: str, digits: int, period: int,
                          category: str, notes: str) -> bool:
        """用备份数据整体覆盖账号（含密钥），供导入冲突时使用"""
        with _connect(self.db_path) as conn:
            cursor = conn.execute('''
                UPDATE accounts SET
                    secret_encrypted = ?,
                    algorithm = ?,
                    digits = ?,
                    period = ?,
                    category = ?,
                    notes = ?
                WHERE id = ?
            ''', (secret_encrypted, algorithm, digits, period, category, notes, account_id))
            conn.commit()
            return cursor.rowcount > 0

    @_guard_errors
    def update_account(self, account_id: int, **kwargs) -> bool:
        """更新账号信息"""
        # 检查账号是否存在
        if not self.get_account(account_id):
            return False

        allowed_fields = {'category', 'notes'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return False

        set_clause = ', '.join(f'{k} = ?' for k in updates.keys())
        values = list(updates.values()) + [account_id]

        with _connect(self.db_path) as conn:
            conn.execute(f'UPDATE accounts SET {set_clause} WHERE id = ?', values)
            conn.commit()
            return True

    @_guard_errors
    def delete_account(self, account_id: int) -> bool:
        """删除账号"""
        with _connect(self.db_path) as conn:
            cursor = conn.execute('DELETE FROM accounts WHERE id = ?', (account_id,))
            conn.commit()
            return cursor.rowcount > 0

    def export_json(self, output_path: str) -> int:
        """
        导出为 JSON 文件（密钥仍加密，内嵌主密钥文件以支持跨机器迁移）

        Args:
            output_path: 输出文件路径

        Returns:
            导出的账号数量
        """
        accounts = self.get_all_accounts()

        export_data = {
            'version': 1,
            'exported_at': datetime.now().isoformat(),
            'master_key': self.crypto.get_key_data(),  # 内嵌主密钥文件，支持跨机恢复
            'accounts': [
                {
                    'issuer': a.issuer,
                    'account': a.account,
                    'secret_encrypted': a.secret_encrypted,
                    'algorithm': a.algorithm,
                    'digits': a.digits,
                    'period': a.period,
                    'category': a.category,
                    'notes': a.notes
                }
                for a in accounts
            ]
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        return len(accounts)

    def import_json(self, input_path: str, external_key: bytes = None,
                    decisions: dict = None) -> dict:
        """
        从 JSON 文件导入（密钥仍加密）

        Args:
            input_path: 输入文件路径
            external_key: 备份对应的主密钥（跨机导入时用外部 key 解密再重加密）；
                          None 时用当前 self.key（同机导入）
            decisions: 冲突决策映射 {(issuer, account): 'current' | 'backup'}；
                      'backup' 用备份整体覆盖，'current' 或缺失时保留当前（跳过）

        Returns:
            {'imported': 新增数, 'updated': 覆盖数,
             'conflict_skipped': 冲突保留当前数, 'damaged_skipped': 数据损坏跳过数}
        """
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        imported = 0
        updated = 0
        conflict_skipped = 0
        damaged_skipped = 0
        decisions = decisions or {}

        for acc in data.get('accounts', []):
            issuer = acc['issuer']
            account = acc['account']

            # 解密备份中的明文密钥
            try:
                if external_key is not None:
                    decrypted_secret = self.crypto.decrypt_with_key(external_key, acc['secret_encrypted'])
                else:
                    decrypted_secret = self.crypto.decrypt(acc['secret_encrypted'])
            except ValueError:
                damaged_skipped += 1  # 密钥无法解密（损坏），跳过
                continue

            existing = self.find_by_identity(issuer, account)

            if existing is None:
                # 新增账号
                self.add_account(
                    issuer=issuer,
                    account=account,
                    secret=decrypted_secret,
                    algorithm=acc.get('algorithm', 'SHA1'),
                    digits=acc.get('digits', 6),
                    period=acc.get('period', 30),
                    category=acc.get('category', 'default'),
                    notes=acc.get('notes', '')
                )
                imported += 1
            elif decisions.get((issuer, account)) == 'backup':
                # 用户选择用备份覆盖（整体覆盖，含密钥和全部字段）
                new_secret = self.crypto.encrypt(decrypted_secret)
                self.overwrite_account(
                    existing.id,
                    new_secret,
                    acc.get('algorithm', 'SHA1'),
                    acc.get('digits', 6),
                    acc.get('period', 30),
                    acc.get('category', 'default'),
                    acc.get('notes', '')
                )
                updated += 1
            else:
                # 用户选择保留当前（或无决策，默认跳过）
                conflict_skipped += 1

        return {
            'imported': imported,
            'updated': updated,
            'conflict_skipped': conflict_skipped,
            'damaged_skipped': damaged_skipped
        }

    def preview_import(self, input_path: str, external_key: bytes = None) -> dict:
        """
        预览导入内容，不实际导入

        Args:
            input_path: 输入文件路径
            external_key: 备份对应的主密钥（跨机导入时用于解密校验）；
                          None 时用当前 self.key（同机导入）

        Returns:
            {
                'total': 3,
                'to_import': [{'issuer': 'Google', ...}, ...],
                'to_skip': [{'issuer': 'GitHub', ...}, ...],   # 已存在账号
                'damaged': [{'issuer': 'X', ...}, ...]          # 无法解密的损坏条目
            }
        """
        # 获取现有账号集合
        existing = self.get_all_accounts()
        existing_keys = {(acc.issuer, acc.account) for acc in existing}

        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 校验版本号
        version = data.get('version', 0)
        if version < 1:
            raise ValueError("不支持的备份文件格式")

        to_import = []
        to_skip = []
        damaged = []

        for acc in data.get('accounts', []):
            # 校验必要字段
            if 'issuer' not in acc or 'account' not in acc or 'secret_encrypted' not in acc:
                raise ValueError("备份文件中存在字段不完整的账号数据")

            # 校验该条目能否解密（无法解密的归入 damaged，不会真正导入）
            try:
                if external_key is not None:
                    self.crypto.decrypt_with_key(external_key, acc['secret_encrypted'])
                else:
                    self.crypto.decrypt(acc['secret_encrypted'])
            except ValueError:
                damaged.append(acc)
                continue

            key = (acc['issuer'], acc['account'])
            if key in existing_keys:
                to_skip.append(acc)
            else:
                to_import.append(acc)

        return {
            'total': len(data.get('accounts', [])),
            'to_import': to_import,
            'to_skip': to_skip,
            'damaged': damaged
        }
