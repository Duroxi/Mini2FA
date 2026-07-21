"""
加密解密模块

使用 AES-256-GCM 认证加密，PBKDF2-SHA256 派生密钥
"""
import os
import json
import base64
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

    def initialize(self, master_password: str) -> bool:
        """
        初始化或加载主密钥

        Args:
            master_password: 用户主密码

        Returns:
            是否成功
        """
        if os.path.exists(self.master_key_path):
            # 加载现有密钥
            return self._load_key(master_password)
        else:
            # 首次使用，创建新密钥
            return self._create_key(master_password)

    def _create_key(self, master_password: str) -> bool:
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
            'version': 1
        }

        with open(self.master_key_path, 'w') as f:
            json.dump(data, f, indent=2)

        self.key = master_key
        return True

    def _load_key(self, master_password: str) -> bool:
        """从文件加载主密钥"""
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
        try:
            aesgcm = AESGCM(derived_key)
            self.key = aesgcm.decrypt(nonce, encrypted_master, None)
            return True
        except Exception:
            return False  # 密码错误

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
        """
        if not self.key:
            raise RuntimeError("未初始化密钥")

        combined = base64.b64decode(ciphertext_b64)
        nonce = combined[:NONCE_SIZE]
        ciphertext = combined[NONCE_SIZE:]

        aesgcm = AESGCM(self.key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode('utf-8')
