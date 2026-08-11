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

在真实终端中运行时使用轻量 TUI（备用屏幕整屏重绘）：退出后终端不留任何残留，
查看验证码时进度条与剩余秒数每秒自动刷新。非交互环境（管道/脚本/CI）自动降级
为纯文本输出；也可显式禁用：

```bash
mini2fa --no-tui
```

### 作为库

```python
from mini2fa import generate_totp, verify_totp

code = generate_totp('JBSWY3DPEHPK3PXP')
print(code)  # 123456
```

## 功能

- 📱 从图片扫码添加 2FA 账号（仅支持 TOTP）
- 🔑 生成符合 RFC 6238 的 TOTP 验证码
- 🔐 AES-256-GCM 加密存储（PBKDF2 密钥派生）
- 📂 分类分组显示 + 关键字搜索
- 💾 JSON 导入/导出备份（内嵌主密钥，支持跨机器迁移）
- 🔒 修改主密码、密保提示
- 🖥️ 跨平台（Windows/Linux/macOS）

## 项目

- GitHub: https://github.com/Duroxi/Mini2FA
- License: MIT
