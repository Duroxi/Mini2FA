# Mini2FA 🔑

安全的本地 TOTP 双因素认证管理工具 — Python 包。

## 安装

```bash
pip install mini2fa
```

## 使用

### 命令行

```bash
mini2fa
```

### 作为库

```python
from mini2fa import generate_totp, verify_totp

code = generate_totp('JBSWY3DPEHPK3PXP')
print(code)  # 123456
```

## 功能

- 📱 从图片扫码添加 2FA 账号
- 🔑 生成符合 RFC 6238 的 TOTP 验证码
- 🔐 AES-256-GCM 加密存储（PBKDF2 密钥派生）
- 💾 JSON 导入/导出备份
- 🖥️ 跨平台（Windows/Linux/macOS）

## 项目

- GitHub: https://github.com/Duroxi/Mini2FA
- License: MIT
