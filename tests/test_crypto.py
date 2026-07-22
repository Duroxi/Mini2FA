"""
加密模块单元测试
"""
import os
import sys
import json
import tempfile
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.crypto import CryptoManager


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
