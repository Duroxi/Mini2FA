---
name: mini2fa
description: "当用户提到验证码、2FA、TOTP、双因素认证、登录码、auth code 时，使用此技能指导 Claude 通过 mini2fa 命令行工具获取验证码。也适用于用户说'获取验证码'、'认证码'、'登录码'等场景。"
---

# Mini2FA Agent 技能

指导 Claude 使用 mini2fa 命令行工具获取 TOTP 验证码。

## 前置条件

确保已安装 mini2fa：
```bash
pip install mini2fa
```

## 核心命令

### 列出所有账号
```bash
mini2fa list -p <密码>
```

输出示例：
```
  [default]
      1. GitHub - CharlesHahn
      2. Google - user@gmail.com
```

### 根据账号 ID 获取验证码
```bash
mini2fa get -p <密码> <id>
```

输出示例：
```
GitHub - CharlesHahn: 681025 (12s)
```

输出格式：`服务商 - 账号: 验证码 (剩余秒数)`

## 使用模式

### 模式 1：直接获取验证码
当用户需要验证码且已知账号 ID 时：
```bash
mini2fa get -p 我的密码 1
```

### 模式 2：先列出再获取
当用户需要验证码但不知道账号 ID 时：
```bash
# 第 1 步：列出账号获取 ID
mini2fa list -p 我的密码

# 第 2 步：使用 ID 获取验证码
mini2fa get -p 我的密码 1
```

### 模式 3：提取验证码用于自动化
集成到其他工具时，从输出中提取 6 位验证码：
```python
import subprocess
import re

result = subprocess.run(
    ['mini2fa', 'get', '-p', '我的密码', '1'],
    capture_output=True, text=True
)
# 提取 6 位验证码
match = re.search(r': (\d{6}) \(', result.stdout)
code = match.group(1) if match else None
```

## 错误处理

| 错误信息 | 含义 | 处理方式 |
|---------|------|---------|
| `密码错误` | 密码错误 | 要求用户提供正确密码 |
| `账号不存在: <id>` | 无效的账号 ID | 运行 `list` 命令查找正确 ID |
| `错误: 缺少密码参数` | 缺少 -p 参数 | 在命令中添加 `-p <密码>` |

## 重要说明

- **零交互**：所有参数必须通过命令行传入，无任何提示词
- **密码安全**：密码会在命令历史中可见，需谨慎使用
- **只读接口**：命令行仅支持 `list` 和 `get`。账号管理（添加/编辑/删除）请使用 TUI 交互模式（直接运行 `mini2fa`）
- **ID 稳定性**：账号 ID 在删除操作前保持稳定。如有疑问，先运行 `list` 命令

## 示例对话

用户："我需要 GitHub 的验证码"

Claude：
```bash
mini2fa list -p <用户提供的密码>
```
（看到 GitHub 的 ID 是 1）

```bash
mini2fa get -p <用户提供的密码> 1
```
（将验证码展示给用户）
