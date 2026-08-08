"""
加密模块单元测试
"""
import os
import sys
import json
import tempfile
import shutil
from pathlib import Path

import pytest

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from mini2fa.crypto import CryptoManager


class TestCryptoManagerInit:
    """测试 CryptoManager 初始化"""

    def test_create_new_key(self):
        """测试创建新密钥"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            os.unlink(temp_path)  # 删除文件以便创建新的
            crypto = CryptoManager(temp_path)
            result = crypto.initialize('test_password')

            assert result is True
            assert crypto.key is not None
            assert os.path.exists(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_create_key_with_hint(self):
        """测试创建带密保提示的密钥"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            os.unlink(temp_path)
            crypto = CryptoManager(temp_path)
            result = crypto.initialize('test_password', 'my hint')

            assert result is True

            # 验证密保提示
            hint = crypto.get_hint()
            assert hint == 'my hint'
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_load_existing_key(self):
        """测试加载现有密钥"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            os.unlink(temp_path)

            # 创建密钥
            crypto1 = CryptoManager(temp_path)
            crypto1.initialize('test_password')

            # 加载密钥
            crypto2 = CryptoManager(temp_path)
            result = crypto2.initialize('test_password')

            assert result is True
            assert crypto2.key == crypto1.key
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_wrong_password(self):
        """测试错误密码"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            os.unlink(temp_path)

            # 创建密钥
            crypto1 = CryptoManager(temp_path)
            crypto1.initialize('correct_password')

            # 尝试用错误密码加载
            crypto2 = CryptoManager(temp_path)
            result = crypto2.initialize('wrong_password')

            assert result is False
            assert crypto2.key is None
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_load_corrupted_key_file(self):
        """测试加载损坏的密钥文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            # 写入无效内容
            with open(temp_path, 'w') as f:
                f.write('not valid json')

            crypto = CryptoManager(temp_path)
            result = crypto.initialize('any_password')
            assert result is False
            assert crypto.key is None

            # 写入有效JSON但缺少字段
            with open(temp_path, 'w') as f:
                json.dump({'version': 1}, f)

            crypto2 = CryptoManager(temp_path)
            result2 = crypto2.initialize('any_password')
            assert result2 is False
            assert crypto2.key is None

            # 写入有效JSON但Base64内容无效
            with open(temp_path, 'w') as f:
                json.dump({
                    'salt': '!!!invalid base64!!!',
                    'nonce': 'dGVzdA==',
                    'encrypted_key': 'dGVzdA==',
                    'version': 1
                }, f)

            crypto3 = CryptoManager(temp_path)
            result3 = crypto3.initialize('any_password')
            assert result3 is False
            assert crypto3.key is None
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestGetHint:
    """测试获取密保提示"""

    def test_get_hint_when_exists(self):
        """测试获取存在的密保提示"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            os.unlink(temp_path)

            crypto = CryptoManager(temp_path)
            crypto.initialize('password', 'test hint')

            hint = crypto.get_hint()
            assert hint == 'test hint'
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_get_hint_empty(self):
        """测试获取空密保提示"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            os.unlink(temp_path)

            crypto = CryptoManager(temp_path)
            crypto.initialize('password', '')

            hint = crypto.get_hint()
            assert hint == ''
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_get_hint_no_hint_field(self):
        """测试获取没有hint字段的文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            # 创建一个没有hint字段的假密钥文件
            data = {
                'salt': 'dGVzdA==',
                'nonce': 'dGVzdA==',
                'encrypted_key': 'dGVzdA==',
                'version': 1
            }
            with open(temp_path, 'w') as f:
                json.dump(data, f)

            crypto = CryptoManager(temp_path)
            hint = crypto.get_hint()

            assert hint == ''
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_get_hint_file_not_exists(self):
        """测试文件不存在时获取密保提示"""
        crypto = CryptoManager('/nonexistent/path.json')
        hint = crypto.get_hint()

        assert hint == ''

    def test_get_hint_corrupted_file(self):
        """测试获取损坏文件的密保提示"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('not valid json')
            temp_path = f.name

        try:
            crypto = CryptoManager(temp_path)
            hint = crypto.get_hint()

            assert hint == ''
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestEncryptDecrypt:
    """测试加密解密"""

    def test_basic_encrypt_decrypt(self):
        """测试基本加密解密"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            os.unlink(temp_path)

            crypto = CryptoManager(temp_path)
            crypto.initialize('test_password')

            # 加密
            plaintext = 'Hello, World!'
            encrypted = crypto.encrypt(plaintext)

            assert encrypted != plaintext
            assert len(encrypted) > 0

            # 解密
            decrypted = crypto.decrypt(encrypted)
            assert decrypted == plaintext
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_encrypt_unicode(self):
        """测试加密Unicode字符串"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            os.unlink(temp_path)

            crypto = CryptoManager(temp_path)
            crypto.initialize('test_password')

            plaintext = '你好，世界！🔐'
            encrypted = crypto.encrypt(plaintext)
            decrypted = crypto.decrypt(encrypted)

            assert decrypted == plaintext
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_encrypt_empty_string(self):
        """测试加密空字符串"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            os.unlink(temp_path)

            crypto = CryptoManager(temp_path)
            crypto.initialize('test_password')

            plaintext = ''
            encrypted = crypto.encrypt(plaintext)
            decrypted = crypto.decrypt(encrypted)

            assert decrypted == plaintext
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_encrypt_long_string(self):
        """测试加密长字符串"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            os.unlink(temp_path)

            crypto = CryptoManager(temp_path)
            crypto.initialize('test_password')

            plaintext = 'A' * 10000
            encrypted = crypto.encrypt(plaintext)
            decrypted = crypto.decrypt(encrypted)

            assert decrypted == plaintext
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_different_encryptions_differ(self):
        """测试相同明文的加密结果不同（因为随机nonce）"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            os.unlink(temp_path)

            crypto = CryptoManager(temp_path)
            crypto.initialize('test_password')

            plaintext = 'test'
            encrypted1 = crypto.encrypt(plaintext)
            encrypted2 = crypto.encrypt(plaintext)

            # 由于使用随机nonce，密文应该不同
            assert encrypted1 != encrypted2

            # 但解密结果应该相同
            assert crypto.decrypt(encrypted1) == plaintext
            assert crypto.decrypt(encrypted2) == plaintext
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_encrypt_without_initialization(self):
        """测试未初始化时加密"""
        crypto = CryptoManager('/tmp/test.json')

        try:
            crypto.encrypt('test')
            assert False, "应该抛出异常"
        except RuntimeError as e:
            assert '未初始化密钥' in str(e)

    def test_decrypt_without_initialization(self):
        """测试未初始化时解密"""
        crypto = CryptoManager('/tmp/test.json')

        try:
            crypto.decrypt('dGVzdA==')
            assert False, "应该抛出异常"
        except RuntimeError as e:
            assert '未初始化密钥' in str(e)

    def test_decrypt_corrupted_data(self):
        """测试解密损坏的数据"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            os.unlink(temp_path)

            crypto = CryptoManager(temp_path)
            crypto.initialize('test_password')

            # 尝试解密无效数据
            try:
                crypto.decrypt('invalid_base64!!!')
                assert False, "应该抛出异常"
            except Exception:
                pass
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_decrypt_wrong_key(self):
        """测试用错误的密钥解密"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            os.unlink(temp_path)

            # 用密钥1加密
            crypto1 = CryptoManager(temp_path)
            crypto1.initialize('password1')
            encrypted = crypto1.encrypt('test')

            # 创建新的密钥文件用密钥2
            os.unlink(temp_path)
            crypto2 = CryptoManager(temp_path)
            crypto2.initialize('password2')

            # 尝试用密钥2解密
            try:
                crypto2.decrypt(encrypted)
                assert False, "应该抛出异常"
            except Exception:
                pass
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestKeyFileFormat:
    """测试密钥文件格式"""

    def test_key_file_structure(self):
        """测试密钥文件结构"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            os.unlink(temp_path)

            crypto = CryptoManager(temp_path)
            crypto.initialize('password', 'hint')

            with open(temp_path, 'r') as f:
                data = json.load(f)

            # 验证必要字段
            assert 'salt' in data
            assert 'nonce' in data
            assert 'encrypted_key' in data
            assert 'hint' in data
            assert 'version' in data

            # 验证值
            assert data['hint'] == 'hint'
            assert data['version'] == 1

            # 验证Base64编码
            import base64
            base64.b64decode(data['salt'])
            base64.b64decode(data['nonce'])
            base64.b64decode(data['encrypted_key'])
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestGetKeyData:
    """测试读取主密钥文件内容"""

    def test_get_key_data(self):
        """测试获取主密钥文件内容"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            os.unlink(temp_path)
            crypto = CryptoManager(temp_path)
            crypto.initialize('password', 'hint')

            data = crypto.get_key_data()
            assert data is not None
            assert 'salt' in data
            assert 'nonce' in data
            assert 'encrypted_key' in data
            assert data['hint'] == 'hint'
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_get_key_data_no_file(self):
        """测试文件不存在时返回 None"""
        crypto = CryptoManager('/nonexistent/master.key')
        assert crypto.get_key_data() is None

    def test_get_key_data_corrupted(self):
        """测试损坏文件返回 None"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('not json')
            temp_path = f.name

        try:
            crypto = CryptoManager(temp_path)
            assert crypto.get_key_data() is None
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestLoadExternalKey:
    """测试加载外部密钥"""

    def _make_backup_key_data(self, password='backup_pwd'):
        """创建一份备份 master.key 内容"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        os.unlink(temp_path)
        crypto = CryptoManager(temp_path)
        crypto.initialize(password, 'hint')
        data = crypto.get_key_data()
        os.unlink(temp_path)
        return data

    def test_load_external_key_correct_password(self):
        """测试正确密码解出外部密钥"""
        key_data = self._make_backup_key_data('backup_pwd')

        crypto = CryptoManager('/nonexistent/master.key')
        key = crypto.load_external_key(key_data, 'backup_pwd')

        assert key is not None
        assert len(key) == 32

    def test_load_external_key_wrong_password(self):
        """测试错误密码返回 None"""
        key_data = self._make_backup_key_data('backup_pwd')

        crypto = CryptoManager('/nonexistent/master.key')
        key = crypto.load_external_key(key_data, 'wrong_pwd')

        assert key is None

    def test_load_external_key_corrupted_data(self):
        """测试损坏数据抛 ValueError"""
        crypto = CryptoManager('/nonexistent/master.key')
        with pytest.raises(ValueError):
            crypto.load_external_key({'salt': 'bad'}, 'pwd')

    def test_load_external_key_missing_field(self):
        """测试缺少字段抛 ValueError"""
        crypto = CryptoManager('/nonexistent/master.key')
        with pytest.raises(ValueError):
            crypto.load_external_key({}, 'pwd')

    def test_load_external_key_invalid_base64(self):
        """测试长度不足的 base64 抛 ValueError"""
        crypto = CryptoManager('/nonexistent/master.key')
        # 'dGVzdA==' 解码为 4 字节，不是非法的 base64 但长度无效（load 内部 base64 仍会解码）
        # 真正的非法 base64 是 length % 4 != 0，如 'abcde'
        with pytest.raises(ValueError):
            crypto.load_external_key(
                {'salt': 'abcde', 'nonce': 'dGVzdA==', 'encrypted_key': 'dGVzdA=='},
                'pwd'
            )


class TestDecryptWithKey:
    """测试用指定密钥解密"""

    def test_decrypt_with_correct_key(self):
        """测试用正确密钥解密"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        try:
            os.unlink(temp_path)
            crypto = CryptoManager(temp_path)
            crypto.initialize('password')

            encrypted = crypto.encrypt('secret-data')
            plaintext = crypto.decrypt_with_key(crypto.key, encrypted)
            assert plaintext == 'secret-data'
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_decrypt_with_wrong_key(self):
        """测试用错误密钥解密抛出 ValueError"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        try:
            os.unlink(temp_path)

            crypto1 = CryptoManager(temp_path)
            crypto1.initialize('password1')
            encrypted = crypto1.encrypt('secret')

            crypto2 = CryptoManager(temp_path)
            crypto2.initialize('password2')

            try:
                crypto2.decrypt_with_key(crypto2.key, encrypted)
                assert False, "应该抛出异常"
            except ValueError as e:
                assert '密钥不匹配' in str(e)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestDecryptInvalidTag:
    """测试 decrypt 对损坏/密钥不匹配密文抛 ValueError（不抛 InvalidTag）"""

    def test_decrypt_wrong_key_raises_valueerror(self):
        """测试用错误密钥解密抛 ValueError 而非 InvalidTag"""
        path1 = os.path.join(tempfile.mkdtemp(), 'key1.json')
        path2 = os.path.join(tempfile.mkdtemp(), 'key2.json')
        try:
            crypto1 = CryptoManager(path1)
            crypto1.initialize('password1')
            encrypted = crypto1.encrypt('secret')

            # 用另一个独立密钥解密（合法 base64，但认证失败）
            crypto2 = CryptoManager(path2)
            crypto2.initialize('password2')

            with pytest.raises(ValueError):
                crypto2.decrypt(encrypted)
        finally:
            for p in [path1, path2]:
                if os.path.exists(p):
                    os.unlink(p)

    def test_decrypt_invalid_base64_raises_valueerror(self):
        """测试无效 base64 解密抛 ValueError"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        try:
            os.unlink(temp_path)
            crypto = CryptoManager(temp_path)
            crypto.initialize('password')

            with pytest.raises(ValueError):
                crypto.decrypt('!!!invalid_base64!!!')
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_decrypt_short_ciphertext_raises_valueerror(self):
        """测试合法 base64 但密文过短抛 ValueError"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        try:
            os.unlink(temp_path)
            crypto = CryptoManager(temp_path)
            crypto.initialize('password')

            # 4 字节，不足 nonce(12)+密文(16)
            with pytest.raises(ValueError):
                crypto.decrypt('dGVzdA==')
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestAdoptExternalKey:
    """测试替换本机主密钥"""

    def test_adopt_external_key(self):
        """测试采用外部密钥后本机可用备份密码登录"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        try:
            os.unlink(temp_path)

            # 创建备份侧密钥
            backup_crypto = CryptoManager(temp_path)
            backup_crypto.initialize('backup_pwd')
            backup_key_data = backup_crypto.get_key_data()

            # 本机（不同文件）当前用自己的密钥
            local_path = temp_path + '.local'
            if os.path.exists(local_path):
                os.unlink(local_path)
            local_crypto = CryptoManager(local_path)
            local_crypto.initialize('local_pwd')

            # 采用备份密钥
            external_key = backup_crypto.key
            local_crypto.adopt_external_key(external_key, backup_key_data)

            # 本机 master.key 文件内容应为备份内容
            with open(local_path, 'r') as f:
                saved = json.load(f)
            assert saved == backup_key_data

            # 本机应能用备份密码重新加载
            reload_crypto = CryptoManager(local_path)
            assert reload_crypto.initialize('backup_pwd') is True
            assert reload_crypto.key == external_key
        finally:
            for p in [temp_path, temp_path + '.local']:
                if os.path.exists(p):
                    os.unlink(p)


class TestVerifyPassword:
    """测试 verify_password（验证不清空会话 key）"""

    def test_verify_correct_password(self):
        """测试正确密码验证通过"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            os.unlink(temp_path)
            crypto = CryptoManager(temp_path)
            crypto.initialize('password')

            assert crypto.verify_password('password') is True
            assert crypto.key is not None
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_verify_wrong_password_preserves_session_key(self):
        """测试错误密码验证失败但不清空会话 key"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            os.unlink(temp_path)
            crypto = CryptoManager(temp_path)
            crypto.initialize('password')   # 登录成功, self.key 有效

            assert crypto.verify_password('wrong') is False
            assert crypto.key is not None, '验证失败不应清空会话 key'

            # 会话内加密仍可用
            enc = crypto.encrypt('secret')
            assert crypto.decrypt(enc) == 'secret'
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestChangePassword:
    """测试修改主密码"""

    def test_change_password_success(self):
        """测试改密成功后旧密码失效、新密码生效"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            os.unlink(temp_path)
            crypto = CryptoManager(temp_path)
            crypto.initialize('old_pwd', '旧提示')

            assert crypto.change_password('old_pwd', 'New_pwd123', '新提示') is True

            # 旧密码失效
            old = CryptoManager(temp_path)
            assert old.initialize('old_pwd') is False
            # 新密码生效
            new = CryptoManager(temp_path)
            assert new.initialize('New_pwd123') is True
            assert new.get_hint() == '新提示'
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_change_password_wrong_old(self):
        """测试旧密码错误时拒绝"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            os.unlink(temp_path)
            crypto = CryptoManager(temp_path)
            crypto.initialize('old_pwd')

            assert crypto.change_password('wrong_pwd', 'New_pwd123', '') is False
            # 原密码仍有效
            reload = CryptoManager(temp_path)
            assert reload.initialize('old_pwd') is True
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_change_password_keeps_data_decryptable(self):
        """测试改密后已有数据仍可解密"""
        from mini2fa.storage import StorageManager

        tmpdir = tempfile.mkdtemp()
        try:
            key_path = os.path.join(tmpdir, 'key')
            crypto = CryptoManager(key_path)
            crypto.initialize('old_pwd')
            storage = StorageManager(os.path.join(tmpdir, 'db.db'), crypto)
            acc_id = storage.add_account('Google', 'u@gmail.com', 'JBSWY3DPEHPK3PXP')
            secret_before = storage.get_secret(acc_id)

            assert crypto.change_password('old_pwd', 'New_pwd123', '') is True

            # 新实例加载后数据仍可解密
            new = CryptoManager(key_path)
            assert new.initialize('New_pwd123') is True
            new_storage = StorageManager(os.path.join(tmpdir, 'db.db'), new)
            assert new_storage.get_secret(acc_id) == secret_before
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
