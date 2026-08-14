# Mini2FA 文档

## 项目简介

Mini2FA 是一个安全的本地 TOTP 双因素认证管理工具，以 Python 包形式发布到 PyPI。

**核心特性**：
- 🔐 **安全**：AES-256-GCM 加密存储，PBKDF2-SHA256 密钥派生
- 🖥️ **跨平台**：支持 Windows、Linux、macOS
- 🎨 **TUI 交互**：零依赖 ANSI 终端 UI，退出后终端无残留
- 🤖 **命令行**：零交互子命令，供 Agent 自动化使用
- 📦 **易于安装**：`pip install mini2fa` 一行命令安装

## 安装

### 使用 pip 安装（推荐）

```bash
pip install mini2fa
```

### 从源码安装

```bash
git clone https://github.com/Duroxi/Mini2FA.git
cd Mini2FA
pip install -e .
```

### 依赖说明

Mini2FA 依赖以下 Python 包（自动安装）：
- `pyzbar`：二维码识别
- `Pillow`：图像处理
- `cryptography`：加密算法
- `wcwidth`：终端显示宽度计算

### 平台支持

| 平台 | 支持状态 |
|------|---------|
| Windows 10/11 | ✅ 完全支持 |
| Linux（主流发行版） | ✅ 完全支持 |
| macOS | ✅ 完全支持 |

**系统要求**：
- Python >= 3.10
- 终端支持 ANSI 转义序列（Windows Terminal、iTerm2、大多数 Linux 终端）

## 快速开始

### 1. 首次使用（设置主密码）

```bash
mini2fa
```

首次运行会提示设置主密码：
```
首次使用，请设置主密码：
⚠️  请牢记此密码，丢失将无法恢复数据！

密码要求：至少 6 位，且包含大写字母、小写字母和数字

输入主密码: ********
确认主密码: ********
设置密码提示（用于忘记密码时提醒，可留空）: 我的宠物名字
✓ 主密码已设置成功！
```

### 2. 添加第一个账号

在主菜单选择 `1. 添加账号（扫码图片）`，输入二维码图片路径：
```
📱 添加新账号
请输入图片文件路径: /path/to/qrcode.png
正在扫描二维码...

✓ 识别到账号信息：
  服务提供商: GitHub
  账号:       user@example.com
  算法:       SHA1
  位数:       6
  周期:       30秒

分类 (直接回车使用默认): 
备注 (直接回车跳过, 最多 20 字): 

确认添加以下账号？
  服务提供商: GitHub
  账号:       user@example.com
  分类:       default
  备注:       (空)

确认添加？[Y/n]: y
✓ 账号添加成功！(ID: 1)
```

### 3. 查看验证码

在主菜单选择 `2. 查看验证码`：
```
共 1 个账号：

  [default]
     1. GitHub - user@example.com

──────────────────────────────────────────────────
  输入编号查看详情 | 0 返回主菜单 | 输入文字搜索

>>> 1
```

进入详情页（每秒自动刷新）：
```
┌─────────────────────────────────────────────────┐
│                                                 │
│  GitHub user@example.com                        │
│                                                 │
│  验证码:  123 456                               │
│                                                 │
│  有效期: [█████████████████░░░░░░░░░░░░░] 15s   │
│                                                 │
│  按 Enter 返回列表                              │
└─────────────────────────────────────────────────┘
```

### 4. 命令行快速获取（给 Agent 使用）

```bash
# 列出所有账号
mini2fa list -p MyPassword123

# 获取验证码
mini2fa get -p MyPassword123 1
```

输出：
```
GitHub - user@example.com: 123456 (15s)
```

## 功能概览

### TUI 交互模式（`mini2fa`）

| 功能 | 说明 |
|------|------|
| 📱 添加账号 | 扫描二维码图片添加 2FA 账号 |
| 🔑 查看验证码 | 列表展示所有账号，详情页每秒刷新 |
| ✏️ 编辑账号 | 修改分类、备注 |
| 🗑️ 删除账号 | 确认删除（不可恢复） |
| 💾 导出备份 | 导出 JSON 备份文件（内嵌主密钥） |
| 📥 导入备份 | 从 JSON 文件导入（支持跨机器迁移） |
| 🔒 修改主密码 | 验证旧密码后设置新密码 |

### 命令行模式（`mini2fa list/get`）

| 命令 | 说明 |
|------|------|
| `mini2fa list -p <password>` | 列出所有账号（ID + 服务商 + 账号） |
| `mini2fa get -p <password> <id>` | 获取验证码（简洁一行式） |

### 安全特性

- **双层密钥加密**：主密码 → PBKDF2 → KEK → 加密 master_key → 加密每个账号的 secret
- **跨机器迁移**：备份文件内嵌主密钥，可在另一台机器解密
- **密码强度检查**：≥6 位，且包含大小写字母和数字
- **安全退出**：TUI 模式退出后终端无残留

## 许可证

Mini2FA 使用 [GPL-3.0-or-later](https://www.gnu.org/licenses/gpl-3.0.html) 许可证。

## 链接

- **GitHub**: https://github.com/Duroxi/Mini2FA
- **PyPI**: https://pypi.org/project/mini2fa/
- **问题反馈**: https://github.com/Duroxi/Mini2FA/issues
