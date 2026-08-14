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

### 状态
✅ 已完成（0.2.3 已发布到 PyPI）

---

## 2. Web 用户交互端

### 目标
提供 Web 界面，让用户通过浏览器管理 2FA 账号和查看验证码。

### 状态
❌ 已评估不实现（无实际需求，TUI 交互版已足够）

---

## 3. AI Agent 交互方式

### 目标
让 Mini2FA 支持通过 AI Agent（如 Claude Code、Cursor、Copilot）进行交互，方便在开发环境中快速使用。

### 收益
- **开发效率**：在终端中直接通过自然语言获取验证码
- **自动化**：可集成到 CI/CD 流水线中
- **无感切换**：Agent 自动识别需要验证码的场景并调用

### 已实现功能

#### 命令行子命令（0.2.3+）

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

### 已实现功能

#### Agent Skill 文件

创建 `skill/SKILL.md` 文件，详细介绍如何让 agent 使用 mini2fa。

**内容**：
- 安装方式：`pip install mini2fa`
- 命令行用法：`mini2fa list/get -p xxx`
- 使用场景：agent 获取验证码、自动化测试
- 示例代码：Python 调用示例

### 状态
✅ 已完成（命令行子命令已完成，skill 文件已创建）

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
  │   └── 支持 list/get 子命令，零交互
  ▼
Phase 3: Agent Skill 文件
  │   └── 创建 skill/SKILL.md，指导 agent 使用
  ▼
Phase 4: 未来扩展
      └── 根据需求添加新功能
```