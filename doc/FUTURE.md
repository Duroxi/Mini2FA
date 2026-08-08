# 未来规划

## 1. 开发为 PyPI 库

### 目标
将 Mini2FA 的核心功能封装为 `pip install mini2fa` 即可安装的 Python 包。

### 收益
- **模块化**：核心逻辑与展示层分离，供其他项目调用
- **生态整合**：可嵌入其他工具、脚本、框架中
- **版本管理**：通过语义化版本控制，方便迭代

### 实现思路

```python
# 用户使用示例（当前实际 API）
from mini2fa import generate_totp, verify_totp

# 生成验证码
code = generate_totp('JBSWY3DPEHPK3PXP')
print(code)  # 123456

# 验证码验证（window=1 允许前后一个周期）
ok = verify_totp(code, 'JBSWY3DPEHPK3PXP')
```

### 技术方案
- 已使用 `pyproject.toml` 配置构建系统（src 布局）
- 发布到 PyPI 和 GitHub Releases
- 保持现有模块（totp/crypto/storage/scanner）不变，封装简洁的公开 API

---

## 2. Web 用户交互端

### 目标
提供 Web 界面，让用户通过浏览器管理 2FA 账号和查看验证码。

### 收益
- **跨平台**：只要有浏览器就可以使用，无需安装 Python
- **移动端支持**：手机浏览器访问，扫码更方便
- **多设备共享**：部署到服务器后，多台设备同步访问

### 方案对比

| 方案 | 框架 | 复杂度 | 推荐场景 |
|------|------|--------|---------|
| Flask | Python | ⭐⭐ | 轻量级，快速开发 |
| FastAPI | Python | ⭐⭐ | 异步性能好，自动生成 API 文档 |
| Streamlit | Python | ⭐ | 极简易用，适合原型 |

### 架构设计

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Web 浏览器   │────▶│  FastAPI     │────▶│  核心模块     │
│  (PWA)       │◀────│  (REST API)  │◀────│  (TOTP+加密)  │
└──────────────┘     └──────────────┘     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │  SQLite      │
                     │  + Key file  │
                     └──────────────┘
```

### 功能规划
- 扫码页：上传图片 → 识别二维码 → 添加账号
- 验证码页：卡片列表展示所有账号的验证码
- 管理页：编辑、删除、导入导出
- 安全：登录密码验证 + HTTPS 加密传输

---

## 3. AI Agent 交互方式

### 目标
让 Mini2FA 支持通过 AI Agent（如 Claude Code、Cursor、Copilot）进行交互，方便在开发环境中快速使用。

### 收益
- **开发效率**：在终端中直接通过自然语言获取验证码
- **自动化**：可集成到 CI/CD 流水线中
- **无感切换**：Agent 自动识别需要验证码的场景并调用

### 交互方式

#### 方式 A：命令行 + 参数模式

```bash
# 命令行参数模式
mini2fa --list
mini2fa --code Google
mini2fa --add screenshot.png
mini2fa --export backup.json
```

#### 方式 B：AI Agent 技能（Skill）模式

```yaml
# mini2fa-agent-skill.md
name: mini2fa
description: 管理 TOTP 双因素认证码

tools:
  - name: list_accounts
    description: 列出所有已添加的2FA账号
  - name: get_code
    description: 获取指定账号的当前验证码
    args:
      - issuer: 服务提供商名称
  - name: add_account
    description: 从图片添加2FA账号
    args:
      - image_path: 二维码图片路径
```

#### 方式 C：MCP Server 模式

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Claude      │────▶│  MCP Server  │────▶│  核心模块     │
│  Code        │     │  (mini2fa)   │     │  (TOTP+加密)  │
│  / Cursor    │◀────│              │◀────│              │
└──────────────┘     └──────────────┘     └──────────────┘
```

通过 MCP 协议暴露工具，让 AI Agent 直接调用：
- `list_accounts` → 返回账号列表
- `get_code(issuer)` → 返回验证码
- `add_account(image_path)` → 添加账号

### 实现优先级

| 方式 | 优先度 | 开发量 | 说明 |
|------|--------|--------|------|
| 命令行参数 | ⭐⭐⭐ | 小 | 快速实现，立即可用 |
| Agent 技能 | ⭐⭐⭐ | 中 | 需要定义技能描述文件 |
| MCP Server | ⭐⭐ | 中 | 需要实现 MCP 协议接口 |

---

## 路线图概览

```
现在                            ⭐ 当前阶段
  │
  ▼
Phase 1: PyPI 发布
  │   └── 封装核心API、发布到 PyPI
  ▼
Phase 2: 命令行参数
  │   └── 支持 --flag 模式，非交互式使用
  ▼
Phase 3: Web 界面
  │   └── Flask/FastAPI 提供浏览器访问
  ▼
Phase 4: AI Agent 集成
      └── MCP Server / Skill 文件
```