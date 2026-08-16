# Mini2FA 开发指南

本文档介绍 Mini2FA 的架构设计、测试方法和贡献指南。

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                          用户                               │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      CLI 层 (_cli.py)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ TUI 交互模式 │  │ 命令行模式  │  │  UI 层      │         │
│  │ (mini2fa)   │  │ (list/get)  │  │  (ui.py)    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      业务层                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ 扫码模块    │  │ TOTP 模块   │  │  加密模块   │         │
│  │ (scanner.py)│  │ (totp.py)   │  │ (crypto.py) │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      数据层                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ 存储模块    │  │  数据模型   │  │  配置模块   │         │
│  │(storage.py) │  │ (models.py) │  │ (config.py) │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      外部依赖                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   SQLite    │  │  文件系统   │  │  pyzbar     │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

### 模块职责

#### CLI 层 (`_cli.py`)

**职责**：
- 用户交互界面（TUI 交互模式、命令行模式）
- 参数解析和验证
- 错误处理和提示
- 调用业务层功能

**关键设计**：
- 使用 `argparse` 解析命令行参数
- 使用 `ui.py` 统一输出接口（`print_line`、`prompt`、`password_prompt`）
- 使用 `_cancelable` 装饰器处理 Ctrl-C 中断
- 错误后暂停等待用户确认（防止信息一闪而过）

#### UI 层 (`ui.py`)

**职责**：
- 统一输出/输入接口
- TUI 模式管理（备用屏幕、清屏、轮询）
- 非 TTY 降级（纯文本输出）

**关键设计**：
- 所有输出走 `print_line`/`print_box`/`prompt`/`password_prompt`
- `clear()` 只在页面边界调用（主菜单、列表页、详情页）
- `wait_key()` 非阻塞按键轮询（详情页每秒刷新）
- `enter()`/`leave()` 切换备用屏幕

#### 扫码模块 (`scanner.py`)

**职责**：
- 从图片文件识别二维码
- 解析 OTP URI
- 提取 TOTP 账号信息

**关键设计**：
- 使用 `pyzbar` 识别二维码
- 使用 `Pillow` 预处理图片（灰度、增强对比度、缩放）
- 只支持 TOTP，HOTP 等抛出 `UnsupportedOTPTypeError`
- 图片含多个二维码时优先返回 TOTP 类型

#### TOTP 模块 (`totp.py`)

**职责**：
- 实现 RFC 6238 标准的 TOTP 算法
- 生成验证码
- 验证验证码

**关键设计**：
- 支持 SHA1/SHA256/SHA512 哈希算法
- 支持自定义验证码位数和时间步长
- 验证窗口支持（允许前/后 N 个周期）

#### 加密模块 (`crypto.py`)

**职责**：
- 双层密钥加密
- 密钥管理（创建、加载、修改）
- 加解密操作

**关键设计**：
- 主密码 → PBKDF2-SHA256（600k 迭代）→ KEK
- KEK 加密随机生成的 master_key
- master_key 加密每个账号的 secret
- 修改密码只重加密 master_key，数据库密文不变

#### 存储模块 (`storage.py`)

**职责**：
- SQLite 数据库操作
- 账号数据的 CRUD
- JSON 导入导出

**关键设计**：
- 使用 `UNIQUE(issuer, account)` 约束防止重复
- 所有 `sqlite3.Error` 统一转 `StorageCorruptedError`
- 导出备份内嵌主密钥（支持跨机器迁移）
- 导入支持冲突处理（逐账号询问）

#### 数据模型 (`models.py`)

**职责**：
- 定义数据结构
- 账号信息和 OTP 信息的数据类

#### 配置模块 (`config.py`)

**职责**：
- 管理数据目录路径
- 定义安全参数和默认值

### 数据流

#### 添加账号流程

```
用户输入图片路径
    ↓
scan_qrcode(image_path)
    ↓
parse_otp_uri(uri)
    ↓
OTPAccountInfo(issuer, account, secret, ...)
    ↓
storage.find_by_identity(issuer, account)
    ↓
storage.add_account(issuer, account, secret, ...)
    ↓
crypto.encrypt(secret)
    ↓
SQLite 存储
```

#### 查看验证码流程

```
storage.get_all_accounts()
    ↓
list_accounts_grouped(accounts)
    ↓
用户选择账号 ID
    ↓
storage.get_secret(account_id)
    ↓
crypto.decrypt(secret_encrypted)
    ↓
generate_totp(secret, algorithm, digits, period)
    ↓
显示验证码
```

#### 导出备份流程

```
storage.export_json(output_path)
    ↓
storage.get_all_accounts()
    ↓
crypto.get_key_data()
    ↓
JSON 序列化（含主密钥）
    ↓
写入文件
```

#### 导入备份流程（跨机器）

```
读取备份文件
    ↓
load_external_key(key_data, password)
    ↓
验证备份密码
    ↓
preview_import(input_path, external_key)
    ↓
用户确认导入
    ↓
storage.import_json(input_path, external_key, decisions)
    ↓
解密备份 → 重加密 → 存储
```

---

## 测试指南

### 运行测试

```bash
# 运行所有测试
python -m pytest

# 运行单个测试文件
python -m pytest tests/test_cli.py

# 运行单个测试
python -m pytest tests/test_cli.py::TestAddAccountFlow::test_add_new_account_with_summary

# 运行带关键字的测试
python -m pytest tests/test_cli.py -k test_display_with_notes

# 显示详细输出
python -m pytest tests/ -v

# 显示覆盖率
python -m pytest tests/ --cov=mini2fa --cov-report=html
```

### 测试结构

```
tests/
├── __init__.py
├── conftest.py           # 公共 fixtures
├── test_cli.py           # CLI 层测试
├── test_crypto.py        # 加密模块测试
├── test_models.py        # 数据模型测试
├── test_scanner.py       # 扫码模块测试
├── test_storage.py       # 存储模块测试
├── test_totp.py          # TOTP 模块测试
└── test_ui.py            # UI 层测试
```

### 测试覆盖率

测试覆盖以下场景：

1. **CLI 层测试** (`test_cli.py`)
   - 分组展示逻辑
   - 编辑账号（清空语义、保持不变、新值更新）
   - 修改主密码（成功、失败）
   - 显示详情（备注、超长内容）
   - 添加账号（查重、摘要确认、取消）
   - Ctrl-C 取消

2. **UI 层测试** (`test_ui.py`)
   - 非 TTY 降级（print_line、prompt、clear）
   - TTY 模式（ANSI 序列）
   - 入口链 Ctrl-C 捕获
   - 详情页显示
   - argparse 解析

3. **加密模块测试** (`test_crypto.py`)
   - 密钥创建和加载
   - 加解密操作
   - 密码验证
   - 修改密码
   - 跨机导入

4. **存储模块测试** (`test_storage.py`)
   - 账号 CRUD
   - 导入导出
   - 冲突处理
   - 错误处理

5. **TOTP 模块测试** (`test_totp.py`)
   - 验证码生成
   - 验证码验证
   - 剩余秒数

6. **扫码模块测试** (`test_scanner.py`)
   - 二维码识别
   - URI 解析
   - 错误处理

### 编写测试

#### 使用 fixtures

```python
import pytest

@pytest.fixture
def crypto_manager(tmp_path):
    """创建加密管理器实例"""
    from mini2fa.crypto import CryptoManager
    key_path = str(tmp_path / 'master.key')
    crypto = CryptoManager(key_path)
    crypto.initialize('test_password', 'test_hint')
    return crypto

@pytest.fixture
def storage_manager(tmp_path, crypto_manager):
    """创建存储管理器实例"""
    from mini2fa.storage import StorageManager
    db_path = str(tmp_path / 'test.db')
    return StorageManager(db_path, crypto_manager)
```

#### Mock 输入输出

```python
from unittest.mock import patch, MagicMock

def test_handle_add_account(monkeypatch):
    """测试添加账号"""
    from mini2fa._cli import handle_add_account
    from mini2fa.models import OTPAccountInfo

    # Mock 输入
    inputs = iter(['fake.png', 'default', '', 'y'])
    monkeypatch.setattr('builtins.input', lambda prompt: next(inputs))

    # Mock 扫码
    info = OTPAccountInfo('GitHub', 'u@gmail.com', 'JBSWY3DPEHPK3PXP', 'SHA1', 6, 30, 'totp')
    monkeypatch.setattr('mini2fa._cli.scan_qrcode', lambda path: info)

    # Mock 文件存在
    monkeypatch.setattr('os.path.exists', lambda path: True)

    # 运行测试
    handle_add_account(storage)
```

#### 测试错误处理

```python
def test_handle_add_account_duplicate(capsys):
    """测试重复账号检测"""
    from mini2fa._cli import handle_add_account

    # 预置重复账号
    storage.add_account('GitHub', 'u@gmail.com', 'JBSWY3DPEHPK3PXP')

    # Mock 输入
    inputs = iter(['fake.png'])
    with patch('builtins.input', side_effect=lambda prompt: next(inputs)):
        with patch('mini2fa._cli.os.path.exists', return_value=True):
            with patch('mini2fa._cli.scan_qrcode', return_value=info):
                handle_add_account(storage)

    # 验证输出
    out = capsys.readouterr().out
    assert '账号已存在' in out
```

---

## 贡献指南

### 代码规范

1. **命名规范**
   - 变量、函数：小写下划线（`snake_case`）
   - 类：大驼峰（`CamelCase`）
   - 常量：大写下划线（`UPPER_CASE`）

2. **注释规范**
   - 模块级文档字符串
   - 函数级文档字符串（Args、Returns、Raises）
   - 复杂逻辑的行内注释

3. **类型注解**
   - 使用 `typing` 模块的类型注解
   - 函数参数和返回值都要有类型注解

### 提交规范

1. **提交信息格式**
   ```
   <type>(<scope>): <subject>

   <body>

   <footer>
   ```

2. **类型**
   - `feat`: 新功能
   - `fix`: 修复 bug
   - `docs`: 文档更新
   - `style`: 代码格式（不影响功能）
   - `refactor`: 重构（不是新功能也不是修复）
   - `perf`: 性能优化
   - `test`: 测试相关
   - `chore`: 构建/工具相关

3. **示例**
   ```
   feat(cli): 添加命令行子命令 list 和 get

   - list 命令列出所有账号
   - get 命令获取验证码
   - 使用 -p 参数传入密码

   Closes #123
   ```

### PR 流程

1. **Fork 项目**
   ```bash
   git clone https://github.com/YOUR_USERNAME/Mini2FA.git
   cd Mini2FA
   ```

2. **创建分支**
   ```bash
   git checkout -b feature/my-feature
   ```

3. **开发和测试**
   ```bash
   # 安装依赖
   pip install -e ".[dev]"

   # 运行测试
   python -m pytest

   # 检查代码风格
   flake8 src/ tests/
   ```

4. **提交代码**
   ```bash
   git add .
   git commit -m "feat(module): 添加新功能"
   ```

5. **推送到 GitHub**
   ```bash
   git push origin feature/my-feature
   ```

6. **创建 PR**
   - 访问 GitHub 仓库页面
   - 点击 "New Pull Request"
   - 填写 PR 描述
   - 等待代码审查

### 开发环境设置

```bash
# 克隆项目
git clone https://github.com/Duroxi/Mini2FA.git
cd Mini2FA

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -e ".[dev]"

# 运行测试
python -m pytest

# 运行程序
python -m mini2fa
```

### 发布流程

1. **更新版本号**
   - `pyproject.toml` 的 `[project] version`
   - `src/mini2fa/__init__.py` 的 `__version__`

2. **构建**
   ```bash
   python -m build
   ```

3. **检查**
   ```bash
   twine check dist/*
   ```

4. **上传 PyPI**
   ```bash
   twine upload dist/*
   ```

5. **创建 GitHub Release**
   - 访问 GitHub 仓库页面
   - 点击 "Releases" → "Create a new release"
   - 填写版本号和发布说明
   - 上传 whl 和 tar.gz 文件
