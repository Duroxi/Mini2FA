# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概览

Mini2FA 是一个本地 TOTP 双因素认证管理工具，以 pip 包形式发布到 PyPI（GPL-3.0-or-later，src 布局）。主入口是 `mini2fa` 命令（_cli.py），核心库模块（totp/crypto/storage/scanner）也可独立使用。

## 常用命令

```bash
# 测试（pytest.ini 已配置 testpaths/addopts；conftest.py 把 src 注入 sys.path）
python -m pytest
# 单个测试
python -m pytest tests/test_cli.py -k test_display_with_notes

# 构建发布
python -m build          # 产物在 dist/
twine check dist/*
twine upload dist/*      # ~/.pypirc 已配置 token
```

⚠️ 不要用 `python -c "import mini2fa"` 验证本地改动——可能命中 site-packages 里已安装的旧版本（真实踩过的坑）；验证一律走 pytest。

## 架构

### 双层密钥加密（crypto.py）
- 主密码 → PBKDF2-SHA256（16B salt，600k 迭代）→ KEK
- KEK 用 AES-256-GCM 加密随机 master_key（32B），存 master.key 文件（JSON：salt/nonce/encrypted_key/hint/version）
- master_key 加密每个账号的 secret，密文存 SQLite（secret_encrypted）
- 改密码只重加密 master_key（`change_password`），数据库密文不变；旧密码立即失效
- 三个"不污染当前会话"的方法：`verify_password`（失败恢复 self.key）、`decrypt_with_key`（用指定 key 解密）、`load_external_key`（解出备份 key）——跨机导入和改密场景都依赖这一点

### 跨机迁移（备份/导入）
- `export_json` 备份内嵌 master_key 文件 dict → 备份可在另一台机器解密
- 导入三态（handle_import）：
  - 空库：先 `adopt_external_key` 覆盖本机 master.key，再原样 import——**顺序是先 adopt 后 import，颠倒会解密失败**
  - 本机已有账号：`decrypt_with_key` 解密备份 → 用本机 key 重加密 → import，本机密码不变
  - 同机备份：直接用当前 key 解密
- `import_json` 返回 `{'imported','updated','conflict_skipped','damaged_skipped'}`；`preview_import` 返回含 damaged 列表的预览；冲突账号逐账号询问，默认保留当前

### 存储（storage.py）
- SQLite，`UNIQUE(issuer, account)` 约束；`update_account` 只允许 category/notes 两字段
- 所有 sqlite3.Error 经 `_guard_errors`/`_connect` 统一转 `StorageCorruptedError`，主循环顶层捕获并提示从备份恢复

### CLI（_cli.py）
- `_cancelable` 装饰器：7 个 handler 内 Ctrl-C = 取消当前操作返回主菜单（不是退出）；`_run` 顶层捕获 KeyboardInterrupt 才是优雅退出
- 列表按分类分组展示，default 排最前；`list_accounts_grouped` 返回**按显示顺序重排**的列表，调用方选号必须用其返回值
- 边框/对齐一律用 wcswidth 计算显示宽度（中文/emoji 宽 2，len 不可用）
- 铁律：信息完整性第一，内容绝不截断，框宽自适应（`display_account_with_code`、`_print_box`）
- `main(argv)` 解析 `--no-tui`，**内部捕获 KeyboardInterrupt**（"再见！🔒" + exit 0）；入口链：console script 直连 `main()`，`__main__.py` 和 `_cli.py` 的 `__main__` 分支走 `_run()`（再兜底一次）。三条入口 Ctrl-C 均优雅退出——**改入口时必须保持 main 内部捕获，否则 console script 会崩溃**

### UI 层（ui.py，零依赖 ANSI TUI）
- 自动降级：stdio 非 TTY（管道/IDE/pytest）时所有函数等价于 print/input；`configure(no_tui=True)` 强制降级
- TTY 模式：`enter()/leave()` 切备用屏幕（`\x1b[?1049h/l`，退出后终端无残留，atexit 兜底恢复）；`render(lines, prompt)` 整屏重绘
- `wait_enter(timeout)` 非阻塞按键轮询：Windows 用 msvcrt、Unix 用 termios+select（Ctrl-C 转 KeyboardInterrupt）；非 TTY 退化为阻塞 `input()`（测试 mock 仍拦截）
- 详情页 `_detail_page` 是唯一轮询页面：TUI 下每秒重绘验证码/进度条，Enter 返回；**非 TUI 下单次渲染 + 阻塞 `input()` 等 Enter（绝不闪退，防"一帧即返回"）**；其余页面均为"渲染一帧 → 输入 → 下一帧"
- 改造规矩：handler 输出全部走 `_show_message(lines)`/`_input_lines(prompt)`，文案与逻辑顺序零改动

### 扫码（scanner.py）
- 仅支持 TOTP；HOTP 等抛 `UnsupportedOTPTypeError`（CLI 给出明确类型提示）；图片含多码时优先返回 totp

### 数据位置（config.py）
- `~/.mini2fa/` 下：mini2fa.db、master.key、backups/（导出默认目录，路径不可配置）

## 命令行子命令（0.2.3+）

### 设计原则
- 命令行版给 agent 使用，**零交互**（无任何提示词，所有参数通过命令行传入）
- 密码通过 `-p` 参数传入（全局参数，放在子命令后面）
- 只读接口，不提供管理功能（删除/编辑/改密码留给 TUI 交互版）

### 核心命令

```bash
# 列出所有账号（ID + issuer + account）
mini2fa list -p <password>

# 获取验证码（简洁一行式）
mini2fa get -p <password> <id>
# 输出示例：GitHub - CharlesHahn: 681025 (12s)
```

### 使用场景
- **人类**：TUI 交互版（`mini2fa`）用于管理+使用
- **Agent**：命令行版（`mini2fa get -p xxx <id>`）只用于获取验证码

### 与其他工具的对比
| 工具 | 设计哲学 |
|---|---|
| `opencode` | CLI 工具，零交互，所有参数通过命令行传入 |
| `claude` | CLI 工具，零交互，所有参数通过命令行传入 |
| `mini2fa` | 命令行版：零交互，只读接口（get/list） |

## 交互约定

- 编辑字段：回车保持不变，输入 `.` 清空（分类清空回 default）
- 删除确认：必须完整输入 `YES, delete <issuer> - <account>`
- 备注限 20 字符（MAX_NOTES_LENGTH）；密码强度要求 ≥6 位且含大小写字母+数字
- 首次设置密码 5 次尝试上限；登录/改密/旧密码验证 3 次上限
- 界面文案用中文，emoji 前缀（📱🔑✏️ 等）保持一致
- **错误处理**：所有错误后暂停等待用户确认（按 Enter 或停留1.5秒），防止信息一闪而过

## 发布流程

- 版本号两处同步：pyproject.toml 的 `[project] version` 与 `src/mini2fa/__init__.py` 的 `__version__`
- 构建前确认 LICENSE 存在（pyproject 的 license-files 引用它）
- PyPI 不允许重复上传同名同版本；发布后发现问题需升版本号再传
- 已知不一致：README 末尾 License 仍写 MIT，与 pyproject.toml 的 GPL-3.0-or-later 不符（doc/ISSUES.md 未追踪此问题）