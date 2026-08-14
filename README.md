# Mini2FA 🔑

安全的本地 TOTP 双因素认证管理工具 — Python 包。

## 安装

```bash
pip install mini2fa
```

## 使用

### 交互模式（TUI）

```bash
mini2fa
```

在真实终端中运行时使用轻量 TUI（备用屏幕整屏重绘）：退出后终端不留任何残留，
查看验证码时进度条与剩余秒数每秒自动刷新。非交互环境（管道/脚本/CI）自动降级
为纯文本输出；也可显式禁用：

```bash
mini2fa --no-tui
```

### 命令行模式（给 Agent 使用）

```bash
# 列出所有账号（ID + issuer + account）
mini2fa list -p <password>

# 获取验证码（简洁一行式，零交互）
mini2fa get -p <password> <id>
# 输出示例：GitHub - CharlesHahn: 681025 (12s)
```

**设计原则**：
- 命令行版给 agent 使用，**零交互**（无任何提示词，所有参数通过命令行传入）
- 密码通过 `-p` 参数传入（全局参数，放在子命令后面）
- 只读接口，不提供管理功能（删除/编辑/改密码留给 TUI 交互版）

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
- 🤖 命令行子命令（`list`/`get`）供 Agent 零交互使用

## 项目

- GitHub: https://github.com/Duroxi/Mini2FA
- License: GPL-3.0-or-later
