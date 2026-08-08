"""
存储模块单元测试
"""
import os
import sys
import json
import shutil
import tempfile
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from mini2fa.storage import StorageManager
from mini2fa.crypto import CryptoManager


class _StorageTestBase:
    """测试基类 - 提供统一的存储管理器和清理"""

    def setup_method(self):
        """每个测试前创建临时存储"""
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, 'test.db')
        self.key_path = os.path.join(self.tmpdir, 'master.key')
        self.crypto = CryptoManager(self.key_path)
        self.crypto.initialize('password')
        self.storage = StorageManager(self.db_path, self.crypto)

    def teardown_method(self):
        """每个测试后清理"""
        shutil.rmtree(self.tmpdir, ignore_errors=True)


class TestStorageManagerInit:
    """测试 StorageManager 初始化"""

    def test_create_new_database(self, tmp_dir):
        """测试创建新数据库"""
        db_path = os.path.join(tmp_dir, 'test.db')
        key_path = os.path.join(tmp_dir, 'master.key')

        crypto = CryptoManager(key_path)
        crypto.initialize('password')

        storage = StorageManager(db_path, crypto)

        assert os.path.exists(db_path)

    def test_create_tables(self, tmp_dir):
        """测试创建表"""
        db_path = os.path.join(tmp_dir, 'test.db')
        key_path = os.path.join(tmp_dir, 'master.key')

        crypto = CryptoManager(key_path)
        crypto.initialize('password')

        storage = StorageManager(db_path, crypto)

        # 验证表存在
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        assert 'accounts' in tables


class TestAddAccount(_StorageTestBase):
    """测试添加账号"""

    def test_add_basic_account(self):
        """测试添加基本账号"""
        account_id = self.storage.add_account(
            issuer='Google',
            account='user@gmail.com',
            secret='JBSWY3DPEHPK3PXP'
        )

        assert account_id is not None
        assert account_id > 0

    def test_add_account_with_all_fields(self):
        """测试添加包含所有字段的账号"""
        account_id = self.storage.add_account(
            issuer='GitHub',
            account='user@github.com',
            secret='JBSWY3DPEHPK3PXP',
            algorithm='SHA256',
            digits=8,
            period=60,
            category='work',
            notes='Test account'
        )

        assert account_id is not None

        # 验证存储
        account = self.storage.get_account(account_id)
        assert account.issuer == 'GitHub'
        assert account.account == 'user@github.com'
        assert account.algorithm == 'SHA256'
        assert account.digits == 8
        assert account.period == 60
        assert account.category == 'work'
        assert account.notes == 'Test account'

    def test_add_duplicate_account(self):
        """测试添加重复账号"""
        self.storage.add_account(
            issuer='Google',
            account='user@gmail.com',
            secret='JBSWY3DPEHPK3PXP'
        )

        try:
            self.storage.add_account(
                issuer='Google',
                account='user@gmail.com',
                secret='JBSWY3DPEHPK3PXP'
            )
            assert False, "应该抛出异常"
        except ValueError as e:
            assert '已存在' in str(e)

    def test_add_account_with_defaults(self):
        """测试使用默认值添加账号"""
        account_id = self.storage.add_account(
            issuer='Test',
            account='test@test.com',
            secret='JBSWY3DPEHPK3PXP'
        )

        account = self.storage.get_account(account_id)
        assert account.algorithm == 'SHA1'
        assert account.digits == 6
        assert account.period == 30
        assert account.category == 'default'


class TestGetAccount(_StorageTestBase):
    """测试获取账号"""

    def test_get_existing_account(self):
        """测试获取存在的账号"""
        account_id = self.storage.add_account(
            issuer='Google',
            account='user@gmail.com',
            secret='JBSWY3DPEHPK3PXP'
        )

        account = self.storage.get_account(account_id)

        assert account is not None
        assert account.issuer == 'Google'
        assert account.account == 'user@gmail.com'

    def test_get_nonexistent_account(self):
        """测试获取不存在的账号"""
        account = self.storage.get_account(999)

        assert account is None


class TestGetAllAccounts(_StorageTestBase):
    """测试获取所有账号"""

    def test_get_all_empty(self):
        """测试获取空列表"""
        accounts = self.storage.get_all_accounts()

        assert accounts == []

    def test_get_all_multiple(self):
        """测试获取多个账号"""
        self.storage.add_account(
            issuer='Google',
            account='user1@gmail.com',
            secret='JBSWY3DPEHPK3PXP'
        )

        self.storage.add_account(
            issuer='GitHub',
            account='user2@github.com',
            secret='JBSWY3DPEHPK3PXP'
        )

        accounts = self.storage.get_all_accounts()

        assert len(accounts) == 2

    def test_get_all_with_category(self):
        """测试按分类获取账号"""
        self.storage.add_account(
            issuer='Google',
            account='user1@gmail.com',
            secret='JBSWY3DPEHPK3PXP',
            category='personal'
        )

        self.storage.add_account(
            issuer='GitHub',
            account='user2@github.com',
            secret='JBSWY3DPEHPK3PXP',
            category='work'
        )

        # 获取所有
        all_accounts = self.storage.get_all_accounts()
        assert len(all_accounts) == 2

        # 按分类获取
        personal_accounts = self.storage.get_all_accounts(category='personal')
        assert len(personal_accounts) == 1

        work_accounts = self.storage.get_all_accounts(category='work')
        assert len(work_accounts) == 1


class TestGetSecret(_StorageTestBase):
    """测试获取密钥"""

    def test_get_secret(self):
        """测试获取密钥"""
        secret = 'JBSWY3DPEHPK3PXP'

        account_id = self.storage.add_account(
            issuer='Google',
            account='user@gmail.com',
            secret=secret
        )

        retrieved_secret = self.storage.get_secret(account_id)

        assert retrieved_secret == secret

    def test_get_secret_nonexistent(self):
        """测试获取不存在的密钥"""
        try:
            self.storage.get_secret(999)
            assert False, "应该抛出异常"
        except ValueError as e:
            assert '不存在' in str(e)


class TestUpdateAccount(_StorageTestBase):
    """测试更新账号"""

    def test_update_category(self):
        """测试更新分类"""
        account_id = self.storage.add_account(
            issuer='Google',
            account='user@gmail.com',
            secret='JBSWY3DPEHPK3PXP'
        )

        result = self.storage.update_account(account_id, category='work')
        assert result is True

        account = self.storage.get_account(account_id)
        assert account.category == 'work'

    def test_update_notes(self):
        """测试更新备注"""
        account_id = self.storage.add_account(
            issuer='Google',
            account='user@gmail.com',
            secret='JBSWY3DPEHPK3PXP'
        )

        result = self.storage.update_account(account_id, notes='New notes')
        assert result is True

        account = self.storage.get_account(account_id)
        assert account.notes == 'New notes'

    def test_update_multiple_fields(self):
        """测试更新多个字段"""
        account_id = self.storage.add_account(
            issuer='Google',
            account='user@gmail.com',
            secret='JBSWY3DPEHPK3PXP'
        )

        result = self.storage.update_account(
            account_id,
            category='work',
            notes='important'
        )
        assert result is True

        account = self.storage.get_account(account_id)
        assert account.category == 'work'
        assert account.notes == 'important'

    def test_update_no_fields(self):
        """测试不更新任何字段"""
        account_id = self.storage.add_account(
            issuer='Google',
            account='user@gmail.com',
            secret='JBSWY3DPEHPK3PXP'
        )

        result = self.storage.update_account(account_id)
        assert result is False

    def test_update_nonexistent_account(self):
        """测试更新不存在的账号"""
        result = self.storage.update_account(999, issuer='Test')
        assert result is False

    def test_update_disallowed_field(self):
        """测试更新不允许的字段"""
        account_id = self.storage.add_account(
            issuer='Google',
            account='user@gmail.com',
            secret='JBSWY3DPEHPK3PXP'
        )

        # 尝试更新不允许的字段（如 algorithm）
        result = self.storage.update_account(account_id, algorithm='SHA256')
        assert result is False  # 没有允许的字段被更新


class TestDeleteAccount(_StorageTestBase):
    """测试删除账号"""

    def test_delete_existing_account(self):
        """测试删除存在的账号"""
        account_id = self.storage.add_account(
            issuer='Google',
            account='user@gmail.com',
            secret='JBSWY3DPEHPK3PXP'
        )

        result = self.storage.delete_account(account_id)
        assert result is True

        # 验证已删除
        account = self.storage.get_account(account_id)
        assert account is None

    def test_delete_nonexistent_account(self):
        """测试删除不存在的账号"""
        result = self.storage.delete_account(999)
        assert result is False


class TestExportImport(_StorageTestBase):
    """测试导入导出"""

    def test_export_empty(self):
        """测试导出空数据库"""
        export_path = os.path.join(self.tmpdir, 'export.json')

        count = self.storage.export_json(export_path)

        assert count == 0
        assert os.path.exists(export_path)

        # 验证文件内容
        with open(export_path, 'r') as f:
            data = json.load(f)

        assert data['version'] == 1
        assert 'exported_at' in data
        assert data['accounts'] == []

    def test_export_with_accounts(self):
        """测试导出包含账号的数据库"""
        self.storage.add_account(
            issuer='Google',
            account='user@gmail.com',
            secret='JBSWY3DPEHPK3PXP'
        )

        self.storage.add_account(
            issuer='GitHub',
            account='user@github.com',
            secret='JBSWY3DPEHPK3PXP'
        )

        export_path = os.path.join(self.tmpdir, 'export.json')
        count = self.storage.export_json(export_path)

        assert count == 2

        # 验证文件内容
        with open(export_path, 'r') as f:
            data = json.load(f)

        assert len(data['accounts']) == 2

    def test_import_empty(self):
        """测试导入空文件"""
        export_path = os.path.join(self.tmpdir, 'export.json')

        # 创建空导出文件
        with open(export_path, 'w') as f:
            json.dump({
                'version': 1,
                'exported_at': '2026-01-01T00:00:00',
                'accounts': []
            }, f)

        result = self.storage.import_json(export_path)
        assert result == {'imported': 0, 'updated': 0, 'conflict_skipped': 0, 'damaged_skipped': 0}

    def test_export_import_cycle(self):
        """测试导出再导入的完整流程"""
        # 添加账号
        self.storage.add_account(
            issuer='Google',
            account='user@gmail.com',
            secret='JBSWY3DPEHPK3PXP',
            category='personal'
        )

        # 导出
        export_path = os.path.join(self.tmpdir, 'export.json')
        self.storage.export_json(export_path)

        # 创建新的存储（使用相同的密钥）
        new_db_path = os.path.join(self.tmpdir, 'new.db')
        new_storage = StorageManager(new_db_path, self.crypto)

        # 导入
        result = new_storage.import_json(export_path)
        assert result == {'imported': 1, 'updated': 0, 'conflict_skipped': 0, 'damaged_skipped': 0}

        # 验证导入的数据
        accounts = new_storage.get_all_accounts()
        assert len(accounts) == 1
        assert accounts[0].issuer == 'Google'
        assert accounts[0].account == 'user@gmail.com'
        assert accounts[0].category == 'personal'

    def test_import_duplicate_accounts(self):
        """测试导入重复账号"""
        # 添加账号
        self.storage.add_account(
            issuer='Google',
            account='user@gmail.com',
            secret='JBSWY3DPEHPK3PXP'
        )

        # 导出
        export_path = os.path.join(self.tmpdir, 'export.json')
        self.storage.export_json(export_path)

        # 尝试导入（无决策，默认跳过重复）
        result = self.storage.import_json(export_path)
        assert result == {'imported': 0, 'updated': 0, 'conflict_skipped': 1, 'damaged_skipped': 0}

        # 验证只有一个账号
        accounts = self.storage.get_all_accounts()
        assert len(accounts) == 1

    def test_export_contains_master_key(self):
        """测试导出文件包含 master_key 字段"""
        self.storage.add_account(
            issuer='Google',
            account='user@gmail.com',
            secret='JBSWY3DPEHPK3PXP'
        )

        export_path = os.path.join(self.tmpdir, 'export.json')
        self.storage.export_json(export_path)

        with open(export_path, 'r') as f:
            data = json.load(f)

        assert 'master_key' in data
        assert data['master_key'] is not None
        assert 'salt' in data['master_key']
        assert 'encrypted_key' in data['master_key']


class TestPreviewImport(_StorageTestBase):
    """测试导入预览（含损坏条目检测）"""

    def test_preview_classifies_damaged(self):
        """测试损坏条目归入 damaged"""
        backup = {
            'version': 1,
            'exported_at': 'x',
            'accounts': [
                # 损坏条目（密文过短）
                {'issuer': 'Bad', 'account': 'b@x.com', 'secret_encrypted': 'dGVzdA==',
                 'algorithm': 'SHA1', 'digits': 6, 'period': 30, 'category': 'default', 'notes': ''},
                # 正常条目
                {'issuer': 'Good', 'account': 'g@x.com',
                 'secret_encrypted': self.crypto.encrypt('JBSWY3DPEHPK3PXP'),
                 'algorithm': 'SHA1', 'digits': 6, 'period': 30, 'category': 'default', 'notes': ''},
            ]
        }
        path = os.path.join(self.tmpdir, 'backup.json')
        with open(path, 'w') as f:
            json.dump(backup, f)

        preview = self.storage.preview_import(path)

        assert preview['total'] == 2
        assert len(preview['to_import']) == 1
        assert preview['to_import'][0]['issuer'] == 'Good'
        assert len(preview['damaged']) == 1
        assert preview['damaged'][0]['issuer'] == 'Bad'
        assert len(preview['to_skip']) == 0

    def test_preview_classifies_existing_as_skip(self):
        """测试已存在账号归入 to_skip"""
        self.storage.add_account(
            issuer='Google', account='user@gmail.com', secret='JBSWY3DPEHPK3PXP'
        )
        backup = {
            'version': 1,
            'exported_at': 'x',
            'accounts': [
                {'issuer': 'Google', 'account': 'user@gmail.com',
                 'secret_encrypted': self.crypto.encrypt('JBSWY3DPEHPK3PXP'),
                 'algorithm': 'SHA1', 'digits': 6, 'period': 30, 'category': 'default', 'notes': ''},
            ]
        }
        path = os.path.join(self.tmpdir, 'backup.json')
        with open(path, 'w') as f:
            json.dump(backup, f)

        preview = self.storage.preview_import(path)

        assert preview['total'] == 1
        assert len(preview['to_skip']) == 1
        assert len(preview['to_import']) == 0
        assert len(preview['damaged']) == 0


class TestImportWithExternalKey(_StorageTestBase):
    """测试跨机导入（用外部密钥重加密）"""

    def test_import_with_external_key(self):
        """测试用外部密钥导入，数据可用本机密钥解密"""
        # 本机存储
        self.storage.add_account(
            issuer='Google',
            account='user@gmail.com',
            secret='JBSWY3DPEHPK3PXP'
        )
        self.storage.add_account(
            issuer='GitHub',
            account='user@github.com',
            secret='JBSWY3DPEHPK3PXP'
        )

        # 导出（含 master_key）
        export_path = os.path.join(self.tmpdir, 'export.json')
        self.storage.export_json(export_path)

        # 读取备份中的 master_key，用备份密码解出外部密钥
        with open(export_path, 'r') as f:
            data = json.load(f)
        backup_key_data = data['master_key']

        # 创建本机（新机器）的密钥
        new_key_path = os.path.join(self.tmpdir, 'new_master.key')
        new_crypto = CryptoManager(new_key_path)
        new_crypto.initialize('local_pwd')

        # 用备份密码解出备份主密钥
        external_key = new_crypto.load_external_key(backup_key_data, 'password')

        # 新存储用本机密钥，导入时传 external_key 重加密
        new_db_path = os.path.join(self.tmpdir, 'new.db')
        new_storage = StorageManager(new_db_path, new_crypto)
        result = new_storage.import_json(export_path, external_key=external_key)
        assert result == {'imported': 2, 'updated': 0, 'conflict_skipped': 0, 'damaged_skipped': 0}

        # 新存储中的账号应能用本机密钥解密
        accounts = new_storage.get_all_accounts()
        assert len(accounts) == 2
        secret = new_storage.get_secret(accounts[0].id)
        assert secret == 'JBSWY3DPEHPK3PXP'

    def test_import_with_external_key_wrong_secret(self):
        """测试外部密钥错误时跳过损坏数据"""
        # 本机存储
        self.storage.add_account(
            issuer='Google',
            account='user@gmail.com',
            secret='JBSWY3DPEHPK3PXP'
        )
        export_path = os.path.join(self.tmpdir, 'export.json')
        self.storage.export_json(export_path)

        # 构造一份损坏的备份（secret_encrypted 无效）
        with open(export_path, 'r') as f:
            data = json.load(f)
        data['accounts'][0]['secret_encrypted'] = 'invalid_base64!'
        corrupt_path = os.path.join(self.tmpdir, 'corrupt.json')
        with open(corrupt_path, 'w') as f:
            json.dump(data, f)

        new_key_path = os.path.join(self.tmpdir, 'new_master.key')
        new_crypto = CryptoManager(new_key_path)
        new_crypto.initialize('local_pwd')
        external_key = new_crypto.load_external_key(data['master_key'], 'password')

        new_db_path = os.path.join(self.tmpdir, 'new.db')
        new_storage = StorageManager(new_db_path, new_crypto)
        # 损坏条目解密失败 → 被跳过
        result = new_storage.import_json(corrupt_path, external_key=external_key)
        assert result == {'imported': 0, 'updated': 0, 'conflict_skipped': 0, 'damaged_skipped': 1}


class TestImportConflictDecisions(_StorageTestBase):
    """测试导入冲突决策（当前/备份）"""

    def _make_backup(self, google_secret='JBSWY3DPEHPK3PXP'):
        """构造一份备份：含 Google（本机已存在）+ GitHub（本机没有）"""
        backup = {
            'version': 1,
            'exported_at': '2026-01-01T00:00:00',
            'master_key': self.crypto.get_key_data(),
            'accounts': [
                {
                    'issuer': 'Google',
                    'account': 'user@gmail.com',
                    'secret_encrypted': self.crypto.encrypt(google_secret),
                    'algorithm': 'SHA1', 'digits': 6, 'period': 30,
                    'category': 'default', 'notes': ''
                },
                {
                    'issuer': 'GitHub',
                    'account': 'user@github.com',
                    'secret_encrypted': self.crypto.encrypt('MFRGGZDFMZTWQ2LK'),
                    'algorithm': 'SHA1', 'digits': 6, 'period': 30,
                    'category': 'default', 'notes': ''
                }
            ]
        }
        path = os.path.join(self.tmpdir, 'backup.json')
        with open(path, 'w') as f:
            json.dump(backup, f)
        return path

    def test_conflict_current_keeps_local(self):
        """决策 current：保留当前账号，不覆盖"""
        # 本机已有 Google（K1）
        self.storage.add_account(
            issuer='Google', account='user@gmail.com', secret='JBSWY3DPEHPK3PXP'
        )
        export_path = self._make_backup()

        decisions = {('Google', 'user@gmail.com'): 'current'}
        result = self.storage.import_json(export_path, decisions=decisions)

        # Google 保留当前（跳过），GitHub 新增
        assert result == {'imported': 1, 'updated': 0, 'conflict_skipped': 1, 'damaged_skipped': 0}

        google = self.storage.find_by_identity('Google', 'user@gmail.com')
        assert self.storage.get_secret(google.id) == 'JBSWY3DPEHPK3PXP'
        github = self.storage.find_by_identity('GitHub', 'user@github.com')
        assert github is not None
        assert len(self.storage.get_all_accounts()) == 2

    def test_conflict_backup_overwrites(self):
        """决策 backup：用备份整体覆盖当前"""
        self.storage.add_account(
            issuer='Google', account='user@gmail.com', secret='JBSWY3DPEHPK3PXP'
        )
        export_path = self._make_backup()

        decisions = {('Google', 'user@gmail.com'): 'backup'}
        result = self.storage.import_json(export_path, decisions=decisions)

        # Google 被覆盖，GitHub 新增
        assert result == {'imported': 1, 'updated': 1, 'conflict_skipped': 0, 'damaged_skipped': 0}

        google = self.storage.find_by_identity('Google', 'user@gmail.com')
        assert self.storage.get_secret(google.id) == 'JBSWY3DPEHPK3PXP'
        assert len(self.storage.get_all_accounts()) == 2

    def test_conflict_backup_overwrites_with_new_secret(self):
        """决策 backup：备份里密钥与当前不同时，用备份密钥覆盖"""
        self.storage.add_account(
            issuer='Google', account='user@gmail.com', secret='OLD_SECRET_K1'
        )
        # 备份里 Google 用的是新密钥 K2
        export_path = self._make_backup(google_secret='NEW_SECRET_K2')

        decisions = {('Google', 'user@gmail.com'): 'backup'}
        result = self.storage.import_json(export_path, decisions=decisions)

        assert result == {'imported': 1, 'updated': 1, 'conflict_skipped': 0, 'damaged_skipped': 0}

        google = self.storage.find_by_identity('Google', 'user@gmail.com')
        # Google 密钥已被覆盖为 K2
        assert self.storage.get_secret(google.id) == 'NEW_SECRET_K2'
        # GitHub 从备份新增
        github = self.storage.find_by_identity('GitHub', 'user@github.com')
        assert self.storage.get_secret(github.id) == 'MFRGGZDFMZTWQ2LK'
