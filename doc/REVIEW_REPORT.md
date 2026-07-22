# 对抗性审查报告

## 审查范围
针对最近的菜单优化（8项 → 6项）进行代码审查

---

## 发现的问题

### 1. 文案不一致 ⚠️ 严重

**位置：** `display_account_with_code` 函数（第88-90行）

```python
│  按 Enter 复制到剪贴板 | 输入 q 返回菜单            │
```

**问题：** 提示"返回菜单"，但实际上输入 `q` 是返回列表，不是返回主菜单。

**建议修改：**
```python
│  按 Enter 复制到剪贴板 | 输入 q 返回列表            │
```

---

### 2. 缺少异常处理 ⚠️ 中等

**位置：** `handle_view_code` 函数（第222行）

```python
secret = storage.get_secret(account.id)
```

**问题：** 没有捕获 `get_secret` 可能抛出的异常。如果数据库损坏或解密失败，程序会崩溃。

**建议修改：**
```python
try:
    secret = storage.get_secret(account.id)
except Exception as e:
    print(f"✗ 获取密钥失败: {e}")
    continue
```

---

### 3. 详情页缺少返回主菜单选项 ⚠️ 轻微

**位置：** `handle_view_code` 详情页循环

**现状：** 用户可以输入 `q` 返回列表，但没有直接返回主菜单的选项。

**建议：** 在详情页增加提示"输入 0 返回主菜单"，或在列表页已有的基础上保持一致。

**分析：** 这是交互设计的权衡，当前设计（列表 → 详情 → 列表）是合理的，不算严重问题。

---

### 4. 编辑账号功能边界确认 ✓ 正确

**位置：** `handle_edit_account` 函数

**确认：** 
- 可以修改：服务商、账号名、分类、备注
- 不能修改：密钥（符合设计要求）

**结论：** 功能边界正确，无需修改。

---

### 5. 复制后自动刷新逻辑 ✓ 正确

**位置：** `handle_view_code` 详情页（第233-242行）

```python
# 复制到剪贴板
code = generate_totp(secret, account.algorithm, account.digits, account.period)
if copy_to_clipboard(code):
    print(f"✓ 已复制到剪贴板: {code}")
else:
    print(f"验证码: {code}")
    print("(自动复制失败，请手动复制)")

# 等待后刷新
time.sleep(0.5)
```

**分析：** 
- 复制后 sleep 0.5 秒再刷新，是为了让用户看到"已复制"提示
- 这个设计是合理的

---

### 6. 账号列表是否需要实时刷新？ ✓ 不需要

**位置：** `handle_view_code` 函数（第193行）

```python
accounts = storage.get_all_accounts()  # 循环外获取
```

**分析：**
- accounts 在循环外获取，循环内不会自动刷新
- 但由于用户不能在查看验证码时添加/删除账号，所以不需要实时刷新
- 如果用户想刷新，退出重新进入即可

**结论：** 当前设计合理，无需修改。

---

## 修改优先级

| 优先级 | 问题 | 影响 |
|--------|------|------|
| 高 | 文案不一致 | 用户困惑 |
| 中 | 缺少异常处理 | 程序崩溃 |
| 低 | 详情页返回选项 | 交互优化 |

---

## 建议修改

### 修改1：修复文案

```python
# 修改前
│  按 Enter 复制到剪贴板 | 输入 q 返回菜单            │

# 修改后
│  按 Enter 复制到剪贴板 | 输入 q 返回列表            │
```

### 修改2：添加异常处理

```python
# 修改前
account = accounts[idx - 1]
secret = storage.get_secret(account.id)

# 修改后
account = accounts[idx - 1]
try:
    secret = storage.get_secret(account.id)
except Exception as e:
    print(f"✗ 获取密钥失败: {e}")
    continue
```

---

## 总体评估

**代码质量：** ✓ 良好

**功能完整性：** ✓ 完整，6个功能边界清晰

**用户体验：** ✓ 基本良好，文案需要修正

**安全性：** ✓ 加密、密保提示、确认删除等机制完整

**建议：** 修复上述2个问题后即可提交。
