# Mini2FA API 文档

本文档详细介绍 Mini2FA 各模块的 API 接口，供开发者使用。

## TOTP 模块

TOTP（Time-based One-Time Password）模块实现 RFC 6238 标准的验证码生成和验证。

### generate_totp

生成 TOTP 验证码。

```python
from mini2fa import generate_totp

code = generate_totp(
    secret='JBSWY3DPEHPK3PXP',  # Base32 编码的密钥
    algorithm='SHA1',            # 哈希算法
    digits=6,                    # 验证码位数
    period=30                    # 时间步长（秒）
)
print(code)  # '123456'
```

**参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `secret` | `str` | 必需 | Base32 编码的密钥 |
| `algorithm` | `str` | `'SHA1'` | 哈希算法：`'SHA1'`、`'SHA256'`、`'SHA512'` |
| `digits` | `int` | `6` | 验证码位数 |
| `period` | `int` | `30` | 时间步长（秒） |

**返回值**：`str` - 验证码字符串（如 `'123456'`）

**示例**：

```python
from mini2fa import generate_totp

# 默认参数
code = generate_totp('JBSWY3DPEHPK3PXP')
print(code)  # '123456'

# 自定义参数
code = generate_totp(
    secret='JBSWY3DPEHPK3PXP',
    algorithm='SHA256',
    digits=8,
    period=60
)
print(code)  # '12345678'
```

### get_remaining_seconds

获取当前周期剩余秒数。

```python
from mini2fa import get_remaining_seconds

remaining = get_remaining_seconds(period=30)
print(remaining)  # 15（剩余 15 秒）
```

**参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `period` | `int` | `30` | 时间步长（秒） |

**返回值**：`int` - 剩余秒数（1-30）

**示例**：

```python
from mini2fa import get_remaining_seconds

# 默认 30 秒周期
remaining = get_remaining_seconds()
print(f"剩余 {remaining} 秒")  # 剩余 15 秒

# 自定义 60 秒周期
remaining = get_remaining_seconds(period=60)
print(f"剩余 {remaining} 秒")  # 剩余 45 秒
```

### verify_totp

验证 TOTP 验证码。

```python
from mini2fa import verify_totp

is_valid = verify_totp(
    code='123456',               # 用户输入的验证码
    secret='JBSWY3DPEHPK3PXP',  # Base32 编码的密钥
    algorithm='SHA1',            # 哈希算法
    digits=6,                    # 验证码位数
    period=30,                   # 时间步长
    window=1                     # 验证窗口
)
print(is_valid)  # True 或 False
```

**参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `code` | `str` | 必需 | 用户输入的验证码 |
| `secret` | `str` | 必需 | Base32 编码的密钥 |
| `algorithm` | `str` | `'SHA1'` | 哈希算法 |
| `digits` | `int` | `6` | 验证码位数 |
| `period` | `int` | `30` | 时间步长（秒） |
| `window` | `int` | `1` | 验证窗口（允许前/后 N 个周期） |

**返回值**：`bool` - 验证是否成功

**示例**：

```python
from mini2fa import generate_totp, verify_totp

secret = 'JBSWY3DPEHPK3PXP'

# 生成验证码
code = generate_totp(secret)
print(f"验证码: {code}")

# 验证验证码
is_valid = verify_totp(code, secret)
print(f"验证结果: {is_valid}")  # True

# 验证窗口
# window=1 表示允许前一个、当前、后一个周期的验证码
is_valid = verify_totp(code, secret, window=1)
print(f"验证结果: {is_valid}")  # True
```

---

## 加密模块

加密模块实现双层密钥加密，保护账号密钥安全。

### CryptoManager

加密管理器类，负责密钥管理和加解密操作。

```python
from mini2fa.crypto import CryptoManager

crypto = CryptoManager(master_key_path='~/.mini2fa/master.key')
```

**构造函数参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `master_key_path` | `str` | 主密钥文件路径 |

**属性**：

| 属性 | 类型 | 说明 |
|------|------|------|
| `key` | `bytes` | 派生密钥（初始化后可用） |

#### initialize

初始化或加载主密钥。

```python
success = crypto.initialize(
    master_password='MyPassword123',  # 用户主密码
    hint='我的宠物名字'                # 密保提示（首次设置时使用）
)
```

**参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `master_password` | `str` | 必需 | 用户主密码 |
| `hint` | `str` | `''` | 密保提示（首次设置时使用） |

**返回值**：`bool` - 是否成功

**行为**：
- 如果主密钥文件不存在：创建新密钥文件
- 如果主密钥文件存在：加载并验证密码
- 密码错误：返回 `False`，清空 `self.key`

#### get_hint

获取密保提示。

```python
hint = crypto.get_hint()
print(hint)  # '我的宠物名字'
```

**返回值**：`str` - 密保提示（不存在返回空字符串）

#### verify_password

验证密码是否正确（不改变当前会话的 key）。

```python
is_valid = crypto.verify_password('MyPassword123')
print(is_valid)  # True 或 False
```

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `password` | `str` | 要验证的密码 |

**返回值**：`bool` - 是否正确

**行为**：
- 验证成功：保持当前会话的 key 不变
- 验证失败：恢复当前会话的 key（不污染会话）

#### change_password

修改主密码。

```python
success = crypto.change_password(
    old_password='OldPassword123',  # 旧密码
    new_password='NewPassword456',  # 新密码
    hint='新的密保提示'              # 新密保提示
)
```

**参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `old_password` | `str` | 必需 | 当前主密码 |
| `new_password` | `str` | 必需 | 新主密码 |
| `hint` | `str` | `''` | 新密保提示（传 `''` 会清空） |

**返回值**：`bool` - 是否成功（旧密码错误返回 `False`）

**行为**：
- 验证旧密码
- 用新密码重新加密 master_key
- 修改后旧密码立即失效
- 数据库中的密文不变

#### encrypt

加密字符串。

```python
ciphertext = crypto.encrypt('JBSWY3DPEHPK3PXP')
print(ciphertext)  # Base64 编码的密文
```

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `plaintext` | `str` | 明文 |

**返回值**：`str` - Base64 编码的密文（含 nonce）

**异常**：`RuntimeError` - 未初始化密钥

#### decrypt

解密字符串。

```python
plaintext = crypto.decrypt(ciphertext)
print(plaintext)  # 'JBSWY3DPEHPK3PXP'
```

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `ciphertext_b64` | `str` | Base64 编码的密文 |

**返回值**：`str` - 明文

**异常**：
- `RuntimeError` - 未初始化密钥
- `ValueError` - 密文损坏或密钥不匹配

#### decrypt_with_key

用指定密钥解密（不改变 self.key）。

```python
plaintext = crypto.decrypt_with_key(
    key=external_key,          # 解密用的密钥
    ciphertext_b64=ciphertext  # Base64 编码的密文
)
```

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `key` | `bytes` | 解密用的密钥（如备份的主密钥） |
| `ciphertext_b64` | `str` | Base64 编码的密文 |

**返回值**：`str` - 明文

**异常**：`ValueError` - key 无效或密文损坏

#### load_external_key

用密码验证并解出备份文件中的主密钥（不改动 self.key）。

```python
external_key = crypto.load_external_key(
    key_data=backup_data['master_key'],  # 备份文件中嵌入的 master_key 内容
    master_password='BackupPassword'      # 备份对应的主密码
)
```

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `key_data` | `dict` | 备份文件中嵌入的 master_key 内容 dict |
| `master_password` | `str` | 备份对应的主密码 |

**返回值**：`bytes` - 解出的备份主密钥；密码错误返回 `None`

**异常**：`ValueError` - key_data 字段缺失或 Base64 数据损坏

#### adopt_external_key

跨机导入（空库）：用备份主密钥替换本机主密钥。

```python
crypto.adopt_external_key(
    external_key=external_key,  # 备份主密钥
    key_data=backup_data        # 备份内嵌的 master_key 内容 dict
)
```

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `external_key` | `bytes` | 备份主密钥（已由 load_external_key 解出） |
| `key_data` | `dict` | 备份内嵌的 master_key 内容 dict |

**行为**：
- 写回本机 master.key 文件
- 更新内存中的 self.key
- 此后本机使用备份对应的主密码登录

#### get_key_data

读取当前主密钥文件内容（导出备份用）。

```python
key_data = crypto.get_key_data()
print(key_data)  # {'salt': '...', 'nonce': '...', 'encrypted_key': '...', 'hint': '...', 'version': 1}
```

**返回值**：`dict` - 主密钥文件内容；文件不存在或损坏时返回 `None`

---

## 存储模块

存储模块使用 SQLite 存储账号数据，支持 JSON 导入导出。

### StorageManager

存储管理器类，负责账号数据的 CRUD 操作。

```python
from mini2fa.storage import StorageManager
from mini2fa.crypto import CryptoManager

crypto = CryptoManager('~/.mini2fa/master.key')
crypto.initialize('MyPassword123')

storage = StorageManager(
    db_path='~/.mini2fa/mini2fa.db',  # 数据库文件路径
    crypto_manager=crypto              # 加密管理器实例
)
```

**构造函数参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `db_path` | `str` | 数据库文件路径 |
| `crypto_manager` | `CryptoManager` | 加密管理器实例 |

**行为**：
- 初始化数据库（如果不存在）
- 创建 accounts 表和索引

#### add_account

添加新账号。

```python
account_id = storage.add_account(
    issuer='GitHub',                    # 服务提供商
    account='user@example.com',         # 账号名
    secret='JBSWY3DPEHPK3PXP',         # OTP 密钥（明文，将自动加密）
    algorithm='SHA1',                   # 哈希算法
    digits=6,                           # 验证码位数
    period=30,                          # 时间步长
    category='default',                 # 分类
    notes='公司账号'                     # 备注
)
print(f"新账号 ID: {account_id}")
```

**参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `issuer` | `str` | 必需 | 服务提供商 |
| `account` | `str` | 必需 | 账号名 |
| `secret` | `str` | 必需 | OTP 密钥（明文，将自动加密） |
| `algorithm` | `str` | `'SHA1'` | 哈希算法 |
| `digits` | `int` | `6` | 验证码位数 |
| `period` | `int` | `30` | 时间步长（秒） |
| `category` | `str` | `'default'` | 分类 |
| `notes` | `str` | `''` | 备注 |

**返回值**：`int` - 新账号 ID

**异常**：`ValueError` - 账号已存在（相同 issuer + account）

#### get_account

获取单个账号。

```python
account = storage.get_account(account_id=1)
print(account)  # Account(id=1, issuer='GitHub', ...)
```

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `account_id` | `int` | 账号 ID |

**返回值**：`Account` - 账号对象；不存在返回 `None`

#### get_all_accounts

获取所有账号。

```python
accounts = storage.get_all_accounts()
print(len(accounts))  # 3
```

**参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `category` | `str` | `None` | 按分类过滤（可选） |

**返回值**：`List[Account]` - 账号列表

#### get_secret

解密并获取密钥。

```python
secret = storage.get_secret(account_id=1)
print(secret)  # 'JBSWY3DPEHPK3PXP'
```

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `account_id` | `int` | 账号 ID |

**返回值**：`str` - 明文密钥

**异常**：`ValueError` - 账号不存在

#### find_by_identity

按 (issuer, account) 精确查找账号。

```python
account = storage.find_by_identity(
    issuer='GitHub',
    account='user@example.com'
)
print(account)  # Account(id=1, issuer='GitHub', ...)
```

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `issuer` | `str` | 服务提供商 |
| `account` | `str` | 账号名 |

**返回值**：`Account` - 账号对象；不存在返回 `None`

#### update_account

更新账号信息（只能修改 category 和 notes）。

```python
success = storage.update_account(
    account_id=1,
    category='工作',
    notes='公司账号'
)
print(success)  # True
```

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `account_id` | `int` | 账号 ID |
| `**kwargs` | - | 要更新的字段（只允许 `category` 和 `notes`） |

**返回值**：`bool` - 是否成功

**限制**：只能修改 `category` 和 `notes` 字段

#### delete_account

删除账号。

```python
success = storage.delete_account(account_id=1)
print(success)  # True
```

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `account_id` | `int` | 账号 ID |

**返回值**：`bool` - 是否成功

#### export_json

导出为 JSON 文件（密钥仍加密，内嵌主密钥文件以支持跨机器迁移）。

```python
count = storage.export_json(output_path='backup.json')
print(f"导出了 {count} 个账号")
```

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `output_path` | `str` | 输出文件路径 |

**返回值**：`int` - 导出的账号数量

**备份文件格式**：

```json
{
  "version": 1,
  "exported_at": "2026-08-14T23:00:00",
  "master_key": {
    "salt": "...",
    "nonce": "...",
    "encrypted_key": "...",
    "hint": "...",
    "version": 1
  },
  "accounts": [
    {
      "issuer": "GitHub",
      "account": "user@example.com",
      "secret_encrypted": "...",
      "algorithm": "SHA1",
      "digits": 6,
      "period": 30,
      "category": "default",
      "notes": ""
    }
  ]
}
```

#### import_json

从 JSON 文件导入（密钥仍加密）。

```python
result = storage.import_json(
    input_path='backup.json',
    external_key=external_key,  # 备份对应的主密钥（跨机导入时用）
    decisions={                  # 冲突决策映射
        ('GitHub', 'user@example.com'): 'backup'
    }
)
print(result)
# {
#   'imported': 2,
#   'updated': 1,
#   'conflict_skipped': 0,
#   'damaged_skipped': 0
# }
```

**参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `input_path` | `str` | 必需 | 输入文件路径 |
| `external_key` | `bytes` | `None` | 备份对应的主密钥（跨机导入时用）；None 时用当前 self.key |
| `decisions` | `dict` | `None` | 冲突决策映射：`'backup'` 用备份覆盖，`'current'` 保留当前 |

**返回值**：`dict` - 导入结果统计

```python
{
    'imported': 2,           # 新增数
    'updated': 1,            # 覆盖数
    'conflict_skipped': 0,   # 冲突保留当前数
    'damaged_skipped': 0     # 数据损坏跳过数
}
```

#### preview_import

预览导入内容，不实际导入。

```python
preview = storage.preview_import(
    input_path='backup.json',
    external_key=external_key  # 备份对应的主密钥（跨机导入时用）
)
print(preview)
# {
#   'total': 3,
#   'to_import': [{'issuer': 'Google', ...}, ...],
#   'to_skip': [{'issuer': 'GitHub', ...}, ...],
#   'damaged': [{'issuer': 'X', ...}, ...]
# }
```

**参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `input_path` | `str` | 必需 | 输入文件路径 |
| `external_key` | `bytes` | `None` | 备份对应的主密钥（跨机导入时用） |

**返回值**：`dict` - 预览结果

```python
{
    'total': 3,                    # 总数
    'to_import': [...],            # 将导入的账号列表
    'to_skip': [...],              # 已存在账号列表
    'damaged': [...]               # 无法解密的损坏条目
}
```

---

## 扫码模块

扫码模块从图片文件中识别二维码并解析 OTP URI。

### scan_qrcode

从图片文件中扫描二维码并解析 OTP URI。

```python
from mini2fa.scanner import scan_qrcode

result = scan_qrcode(image_path='qrcode.png')
print(result)
# OTPAccountInfo(issuer='GitHub', account='user@example.com', ...)
```

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `image_path` | `str` | 图片文件路径 |

**返回值**：`OTPAccountInfo` - 解析结果；识别失败返回 `None`

**异常**：
- `FileNotFoundError` - 文件不存在
- `UnsupportedOTPTypeError` - 二维码是 HOTP 等非 TOTP 类型
- `ValueError` - 扫描失败

**行为**：
1. 尝试直接识别
2. 如果失败，预处理图片（灰度、增强对比度、缩放）后重试
3. 如果图片含多个二维码，优先返回 TOTP 类型

### parse_otp_uri

解析 otpauth:// URI。

```python
from mini2fa.scanner import parse_otp_uri

result = parse_otp_uri(
    uri='otpauth://totp/Example:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=Example'
)
print(result)
# OTPAccountInfo(issuer='Example', account='user@example.com', ...)
```

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `uri` | `str` | OTP URI 字符串 |

**返回值**：`OTPAccountInfo` - 解析结果；格式无效返回 `None`

**异常**：`UnsupportedOTPTypeError` - URI 类型不是 TOTP

**URI 格式**：

```
otpauth://totp/Example:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=Example&algorithm=SHA1&digits=6&period=30
```

**参数说明**：

| 参数 | 说明 |
|------|------|
| `totp` | OTP 类型（只支持 TOTP） |
| `Example:user@example.com` | 标签（issuer:account 格式） |
| `secret` | Base32 编码的密钥（必需） |
| `issuer` | 服务提供商（可选） |
| `algorithm` | 哈希算法（可选，默认 SHA1） |
| `digits` | 验证码位数（可选，默认 6） |
| `period` | 时间步长（可选，默认 30） |

### scan_qrcode_from_raw_data

从原始数据中解析二维码。

```python
from mini2fa.scanner import scan_qrcode_from_raw_data

result = scan_qrcode_from_raw_data(data=image_bytes)
print(result)
# OTPAccountInfo(issuer='GitHub', account='user@example.com', ...)
```

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `data` | `bytes` | 原始字节数据 |

**返回值**：`OTPAccountInfo` - 解析结果；失败返回 `None`

**异常**：`UnsupportedOTPTypeError` - 数据是 HOTP 等非 TOTP 类型

### preprocess_image

图片预处理，提高识别率。

```python
from mini2fa.scanner import preprocess_image
from PIL import Image

image = Image.open('qrcode.png')
processed = preprocess_image(image)
```

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `image` | `Image.Image` | 原始图片 |

**返回值**：`Image.Image` - 预处理后的图片

**处理步骤**：
1. 转换为灰度图
2. 调整对比度（增强 2.0 倍）
3. 缩放到合理尺寸（宽度不超过 1024 像素）

---

## 数据模型

### Account

账号数据模型。

```python
from mini2fa.models import Account

account = Account(
    id=1,
    issuer='GitHub',
    account='user@example.com',
    secret_encrypted='encrypted...',
    algorithm='SHA1',
    digits=6,
    period=30,
    category='default',
    notes='',
    created_at='2026-08-14 23:00:00',
    updated_at='2026-08-14 23:00:00'
)
```

**字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `int` | 账号 ID（自增主键） |
| `issuer` | `str` | 服务提供商（如 GitHub、Google） |
| `account` | `str` | 账号名（如 user@example.com） |
| `secret_encrypted` | `str` | 加密后的密钥 |
| `algorithm` | `str` | 算法：SHA1/SHA256/SHA512 |
| `digits` | `int` | 验证码位数 |
| `period` | `int` | 时间步长（秒） |
| `category` | `str` | 分类 |
| `notes` | `str` | 备注 |
| `created_at` | `str` | 创建时间 |
| `updated_at` | `str` | 更新时间 |

### OTPAccountInfo

从二维码解析出的 OTP 账号信息。

```python
from mini2fa.models import OTPAccountInfo

info = OTPAccountInfo(
    issuer='GitHub',
    account='user@example.com',
    secret='JBSWY3DPEHPK3PXP',
    algorithm='SHA1',
    digits=6,
    period=30,
    otp_type='totp'
)
```

**字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `issuer` | `str` | 服务提供商 |
| `account` | `str` | 账号名 |
| `secret` | `str` | 明文密钥（Base32） |
| `algorithm` | `str` | 哈希算法 |
| `digits` | `int` | 验证码位数 |
| `period` | `int` | 时间步长（秒） |
| `otp_type` | `str` | OTP 类型（只支持 `'totp'`） |

---

## 配置参数

### 安全参数

| 参数 | 值 | 说明 |
|------|-----|------|
| `SALT_SIZE` | 16 | 盐长度（字节） |
| `KEY_SIZE` | 32 | 密钥长度（256 位） |
| `ITERATIONS` | 600,000 | PBKDF2 迭代次数（OWASP 推荐） |
| `NONCE_SIZE` | 12 | GCM Nonce 长度（字节） |

### 默认 OTP 参数

| 参数 | 值 | 说明 |
|------|-----|------|
| `DEFAULT_ALGORITHM` | `'SHA1'` | 默认哈希算法 |
| `DEFAULT_DIGITS` | 6 | 默认验证码位数 |
| `DEFAULT_PERIOD` | 30 | 默认时间步长（秒） |
| `DEFAULT_CATEGORY` | `'default'` | 默认分类 |

### 数据目录

| 路径 | 说明 |
|------|------|
| `~/.mini2fa/` | 数据目录 |
| `~/.mini2fa/mini2fa.db` | SQLite 数据库 |
| `~/.mini2fa/master.key` | 主密钥文件 |
| `~/.mini2fa/backups/` | 备份目录 |
