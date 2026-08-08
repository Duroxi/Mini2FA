"""
加密解密模块

使用 AES-256-GCM 认证加密，PBKDF2-SHA256 派生密钥
"""
import os
import json
import base64
import binascii
from typing import Optional
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

from .config import SALT_SIZE, KEY_SIZE, ITERATIONS, NONCE_SIZE


class CryptoManager:
    """加密管理器"""

    def __init__(self, master_key_path: str):
        """
        初始化加密管理器

        Args:
            master_key_path: 主密钥文件路径
        """
        self.master_key_path = master_key_path
        self.key = None  # 派生密钥

    def initialize(self, master_password: str, hint: str = '') -> bool:
        """
        初始化或加载主密钥

        Args:
            master_password: 用户主密码
            hint: 密保提示（首次设置时使用）

        Returns:
            是否成功
        """
        if os.path.exists(self.master_key_path):
            # 加载现有密钥
            return self._load_key(master_password)
        else:
            # 首次使用，创建新密钥
            return self._create_key(master_password, hint)

    def _create_key(self, master_password: str, hint: str = '') -> bool:
        """创建新的主密钥文件"""
        salt = os.urandom(SALT_SIZE)

        # 派生密钥
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=KEY_SIZE,
            salt=salt,
            iterations=ITERATIONS,
            backend=default_backend()
        )
        derived_key = kdf.derive(master_password.encode('utf-8'))

        # 生成主密钥（随机）
        master_key = os.urandom(KEY_SIZE)

        # 用派生密钥加密主密钥
        aesgcm = AESGCM(derived_key)
        nonce = os.urandom(NONCE_SIZE)
        encrypted_master = aesgcm.encrypt(nonce, master_key, None)

        # 保存到文件
        data = {
            'salt': base64.b64encode(salt).decode(),
            'nonce': base64.b64encode(nonce).decode(),
            'encrypted_key': base64.b64encode(encrypted_master).decode(),
            'hint': hint,  # 密保提示（明文存储）
            'version': 1
        }

        with open(self.master_key_path, 'w') as f:
            json.dump(data, f, indent=2)

        self.key = master_key
        return True

    def get_hint(self) -> str:
        """获取密保提示"""
        if not os.path.exists(self.master_key_path):
            return ''

        try:
            with open(self.master_key_path, 'r') as f:
                data = json.load(f)
            return data.get('hint', '')
        except Exception:
            return ''

    def get_key_data(self) -> dict:
        """
        读取当前主密钥文件内容（导出备份用）

        Returns:
            主密钥文件内容 dict；文件不存在或损坏时返回 None
        """
        if not os.path.exists(self.master_key_path):
            return None

        try:
            with open(self.master_key_path, 'r') as f:
                return json.load(f)
        except Exception:
            return None

    def decrypt_with_key(self, key: bytes, ciphertext_b64: str) -> str:
        """
        用指定密钥解密（不改变 self.key），供跨机导入重加密使用

        Args:
            key: 解密用的密钥（如备份的主密钥）
            ciphertext_b64: Base64 编码的密文

        Returns:
            明文

        Raises:
            ValueError: key 无效或密文损坏（base64 解码失败或 AES-GCM 认证失败）
        """
        try:
            combined = base64.b64decode(ciphertext_b64)
            nonce = combined[:NONCE_SIZE]
            ciphertext = combined[NONCE_SIZE:]

            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext.decode('utf-8')
        except Exception:
            raise ValueError("密钥不匹配或密文已损坏")

    def _load_key(self, master_password: str) -> bool:
        """从文件加载主密钥"""
        try:
            with open(self.master_key_path, 'r') as f:
                data = json.load(f)

            salt = base64.b64decode(data['salt'])
            nonce = base64.b64decode(data['nonce'])
            encrypted_master = base64.b64decode(data['encrypted_key'])

            # 派生密钥
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=KEY_SIZE,
                salt=salt,
                iterations=ITERATIONS,
                backend=default_backend()
            )
            derived_key = kdf.derive(master_password.encode('utf-8'))

            # 解密主密钥
            aesgcm = AESGCM(derived_key)
            self.key = aesgcm.decrypt(nonce, encrypted_master, None)
            return True
        except Exception:
            self.key = None
            return False

    def load_external_key(self, key_data: dict, master_password: str) -> Optional[bytes]:
        """
        用密码验证并解出备份文件中的主密钥（不改动 self.key）

        Args:
            key_data: 备份文件中嵌入的 master_key 内容 dict
            master_password: 备份对应的主密码

        Returns:
            解出的备份主密钥 bytes；密码错误返回 None

        Raises:
            ValueError: key_data 字段缺失或 Base64 数据损坏（不是密码问题）
        """
        try:
            salt = base64.b64decode(key_data['salt'])
            nonce = base64.b64decode(key_data['nonce'])
            encrypted_master = base64.b64decode(key_data['encrypted_key'])
        except (KeyError, TypeError, ValueError, binascii.Error):
            raise ValueError("备份文件中的主密钥数据损坏，无法读取")

        try:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=KEY_SIZE,
                salt=salt,
                iterations=ITERATIONS,
                backend=default_backend()
            )
            derived_key = kdf.derive(master_password.encode('utf-8'))

            aesgcm = AESGCM(derived_key)
            return aesgcm.decrypt(nonce, encrypted_master, None)
        except Exception:
            return None  # 密码错误

    def verify_password(self, password: str) -> bool:
        """
        验证密码是否正确（不改变 self.key）

        与 initialize 不同：验证失败不会清空当前会话 key，
        供会话内验证旧密码等场景使用。
        """
        saved_key = self.key
        result = self._load_key(password)
        if not result:
            self.key = saved_key  # 失败时恢复，不污染会话
        return result

    def change_password(self, old_password: str, new_password: str, hint: str = '') -> bool:
        """
        修改主密码：验证旧密码 → 用新密码重新加密 master_key

        数据库中的 secret_encrypted 不受影响（master_key 不变），
        修改后旧密码立即失效（新 salt + 新 nonce）。

        Args:
            old_password: 当前主密码
            new_password: 新主密码
            hint: 新密保提示（传 '' 会清空，调用方负责保留原 hint）

        Returns:
            是否成功（旧密码错误返回 False）
        """
        # 1. 验证旧密码（解出当前 master_key；失败不污染会话 key）
        if not self.verify_password(old_password):
            return False
        master_key = self.key

        # 2. 用新密码派生新 KEK，重新加密 master_key
        salt = os.urandom(SALT_SIZE)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=KEY_SIZE,
            salt=salt,
            iterations=ITERATIONS,
            backend=default_backend()
        )
        derived_key = kdf.derive(new_password.encode('utf-8'))

        aesgcm = AESGCM(derived_key)
        nonce = os.urandom(NONCE_SIZE)
        encrypted_master = aesgcm.encrypt(nonce, master_key, None)

        # 3. 写回 master.key
        data = {
            'salt': base64.b64encode(salt).decode(),
            'nonce': base64.b64encode(nonce).decode(),
            'encrypted_key': base64.b64encode(encrypted_master).decode(),
            'hint': hint,
            'version': 1
        }
        with open(self.master_key_path, 'w') as f:
            json.dump(data, f, indent=2)

        # 4. self.key 保持 master_key，会话内继续可用
        return True

    def adopt_external_key(self, external_key: bytes, key_data: dict) -> None:
        """
        跨机导入（空库）：用备份主密钥替换本机主密钥

        写回本机 master.key 文件并更新内存中的 self.key，
        此后本机使用备份对应的主密码登录。

        Args:
            external_key: 备份主密钥（已由 load_external_key 解出）
            key_data: 备份内嵌的 master_key 内容 dict
        """
        with open(self.master_key_path, 'w') as f:
            json.dump(key_data, f, indent=2)
        self.key = external_key

    def encrypt(self, plaintext: str) -> str:
        """
        加密字符串

        Args:
            plaintext: 明文

        Returns:
            Base64 编码的密文（含 nonce）
        """
        if not self.key:
            raise RuntimeError("未初始化密钥")

        aesgcm = AESGCM(self.key)
        nonce = os.urandom(NONCE_SIZE)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)

        # 合并 nonce 和密文
        combined = nonce + ciphertext
        return base64.b64encode(combined).decode()

    def decrypt(self, ciphertext_b64: str) -> str:
        """
        解密字符串

        Args:
            ciphertext_b64: Base64 编码的密文

        Returns:
            明文

        Raises:
            RuntimeError: 未初始化密钥
            ValueError: base64 解码失败或 AES-GCM 认证失败（密文损坏/密钥不匹配）
        """
        if not self.key:
            raise RuntimeError("未初始化密钥")

        try:
            combined = base64.b64decode(ciphertext_b64)
            nonce = combined[:NONCE_SIZE]
            ciphertext = combined[NONCE_SIZE:]

            aesgcm = AESGCM(self.key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext.decode('utf-8')
        except Exception:
            raise ValueError("密文已损坏或密钥不匹配")
