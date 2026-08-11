"""
Mini2FA 脚本版 - 主程序

安全的本地 TOTP 验证码管理工具

业务层只调用 ui 模块的统一接口（print_line/print_box/prompt/password_prompt），
不直接 print/input；输出与输入机制由 ui 层统一管理（TTY 自动 TUI，非 TTY 降级）。
"""
import os
import sys
import functools
import argparse
from pathlib import Path
from datetime import datetime
import json

from .scanner import scan_qrcode, UnsupportedOTPTypeError
from .crypto import CryptoManager
from .storage import StorageManager, StorageCorruptedError
from .totp import generate_totp, get_remaining_seconds
from . import ui
from .config import (
    init_data_dir, get_data_dir, get_db_path,
    get_key_path, get_backup_dir
)

PASSWORD_REQUIREMENTS = "至少 6 位，且包含大写字母、小写字母和数字"
MAX_PASSWORD_ATTEMPTS = 5  # 首次设置主密码的重试上限
MAX_NOTES_LENGTH = 20      # 备注输入长度上限


def _validate_password_strength(pwd: str) -> tuple:
    """验证主密码强度

    Returns:
        (True, '') 或 (False, 错误描述)
    """
    if len(pwd) < 6:
        return False, "密码长度至少 6 位！"
    if not any(c.isupper() for c in pwd):
        return False, "密码必须包含至少一个大写字母！"
    if not any(c.islower() for c in pwd):
        return False, "密码必须包含至少一个小写字母！"
    if not any(c.isdigit() for c in pwd):
        return False, "密码必须包含至少一个数字！"
    return True, ''


def _cancelable(func):
    """装饰器：操作过程中 Ctrl-C 放弃当前操作，返回主菜单"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            ui.print_line("\n已取消，返回主菜单。")
            return
    return wrapper


def display_account_with_code(account, secret: str, code: str = None):
    """
    显示账号信息和验证码

    框宽按内容自适应（不截断任何信息），右边缘始终对齐。
    输出为追加式（普通终端与 TUI 一致），由调用方决定是否清屏。

    Args:
        account: Account 对象
        secret: 明文密钥
        code: 可选的验证码（如果已计算，避免重复计算）
    """
    from wcwidth import wcswidth
    code = code or generate_totp(secret, account.algorithm, account.digits, account.period)
    remaining = get_remaining_seconds(account.period)

    # 进度条
    period = account.period
    progress = '█' * (period - remaining) + '░' * remaining

    # 收集所有内容行（完整显示，不截断）
    lines = [
        f'│  {account.issuer} {account.account}',
        f'│  验证码:  {code[:3]} {code[3:]}',
        f'│  有效期: [{progress}] {remaining:2d}s',
    ]
    if account.notes:
        lines.insert(2, f'│  备注: {account.notes}')
    lines.append('│  按 Enter 返回列表')

    # 框宽 = 内容最大显示宽度 + 左右边距
    content_w = max(wcswidth(line) for line in lines)
    box_w = content_w + 4

    top = '┌' + '─' * (box_w - 2) + '┐'
    bottom = '└' + '─' * (box_w - 2) + '┘'
    blank = '│' + ' ' * (box_w - 2) + '│'

    # 内容行交错空白行，右边缘对齐
    body = []
    for line in lines:
        body.append(blank)
        body.append(line + ' ' * (box_w - wcswidth(line) - 1) + '│')

    ui.print_line(top)
    ui.print_line('\n'.join(body))
    ui.print_line(bottom)


def display_banner():
    """显示程序横幅"""
    from . import __version__
    lines = [
        f'          Mini2FA v{__version__}',
        '    安全的本地 TOTP 验证码管理工具',
        '',
        '  📱 扫码添加 | 🔑 验证码生成 | 🔐 AES-256 加密',
    ]
    ui.print_box(lines)


def _menu_lines() -> list:
    """主菜单内容行"""
    return [
        '                    主 菜 单',
        '———————————————————————————————————',
        '  📱  1. 添加账号（扫码图片）',
        '  🔑  2. 查看验证码',
        '  ✏️  3. 编辑账号',
        '  🗑️  4. 删除账号',
        '  💾  5. 导出备份',
        '  📥  6. 导入备份',
        '  🔒  7. 修改主密码',
        '  🚪  0. 退出',
    ]


def display_menu():
    """显示主菜单"""
    ui.print_box(_menu_lines())


@_cancelable
def handle_add_account(storage: StorageManager):
    """处理添加账号"""
    ui.print_line("\n📱 添加新账号")
    ui.print_line("-" * 40)

    image_path = ui.prompt("请输入图片文件路径: ").strip()

    # 移除路径两端的引号（Windows 拖拽文件时会带引号）
    if image_path.startswith('"') and image_path.endswith('"'):
        image_path = image_path[1:-1]
    elif image_path.startswith("'") and image_path.endswith("'"):
        image_path = image_path[1:-1]

    if not os.path.exists(image_path):
        ui.print_line("✗ 文件不存在！请检查路径。")
        return

    ui.print_line("正在扫描二维码...")

    try:
        result = scan_qrcode(image_path)
    except UnsupportedOTPTypeError as e:
        ui.print_line(f"✗ 该二维码是 {e.otp_type.upper()} 协议，本工具仅支持 TOTP。")
        return
    except Exception as e:
        ui.print_line(f"✗ 扫描失败: {e}")
        return

    if not result:
        ui.print_line("✗ 未识别到有效的二维码！")
        ui.print_line("  提示：请确保图片包含清晰的 OTP 二维码。")
        return

    # 查重：已存在则直接提示，不进入填字段流程
    existing = storage.find_by_identity(result.issuer, result.account)
    if existing is not None:
        ui.print_line(f"✗ 账号已存在: {result.issuer} - {result.account}")
        ui.print_line("  该账号已在库中（分类: {0}, ID: {1}）。".format(
            existing.category, existing.id))
        return

    # 显示识别结果
    ui.print_line("✓ 识别到账号信息：")
    ui.print_line("  ─────────────────────────────────────")
    ui.print_line(f"  服务提供商: {result.issuer}")
    ui.print_line(f"  账号:       {result.account}")
    ui.print_line(f"  算法:       {result.algorithm}")
    ui.print_line(f"  位数:       {result.digits}")
    ui.print_line(f"  周期:       {result.period}秒")
    ui.print_line(f"  类型:       {result.otp_type}")

    # 先收集分类和备注
    category = ui.prompt("分类 (直接回车使用默认): ").strip()[:50] or 'default'
    notes = ui.prompt(f"备注 (直接回车跳过, 最多 {MAX_NOTES_LENGTH} 字): ").strip()[:MAX_NOTES_LENGTH]

    # 展示完整摘要，一次性确认
    ui.print_line("确认添加以下账号？")
    ui.print_line("  ─────────────────────────────────────")
    ui.print_line(f"  服务提供商: {result.issuer}")
    ui.print_line(f"  账号:       {result.account}")
    ui.print_line(f"  分类:       {category}")
    ui.print_line(f"  备注:       {notes or '(空)'}")
    ui.print_line("  ─────────────────────────────────────")

    confirm = ui.prompt("确认添加？[Y/n]: ").strip().lower()
    if confirm not in ('', 'y', 'yes'):
        ui.print_line("已取消。")
        return

    try:
        account_id = storage.add_account(
            issuer=result.issuer,
            account=result.account,
            secret=result.secret,
            algorithm=result.algorithm,
            digits=result.digits,
            period=result.period,
            category=category,
            notes=notes
        )
        ui.print_line(f"✓ 账号添加成功！(ID: {account_id})")
    except ValueError as e:
        ui.print_line(f"✗ {e}")


def list_accounts_grouped(accounts) -> list:
    """
    按分类分组打印账号列表（default 排最前，其余按名称排序）
    编号全局连续，返回【按显示顺序重排】的账号列表。

    Args:
        accounts: Account 对象列表

    Returns:
        按显示编号顺序排列的账号列表（调用方必须用此返回值选号，
        即 listed[idx-1]，不能用原 accounts[idx-1]）
    """
    groups = {}
    for acc in accounts:
        groups.setdefault(acc.category, []).append(acc)

    # default 排最前，其余按名称排序
    categories = sorted(groups.keys(), key=lambda c: (c != 'default', c))

    ordered = []
    idx = 0
    for category in categories:
        ui.print_line(f"\n  [{category}]")
        for acc in groups[category]:
            idx += 1
            ui.print_line(f"    {idx:2d}. {acc.issuer} - {acc.account}")
            ordered.append(acc)
    ui.print_line()
    return ordered


@_cancelable
def handle_view_code(storage: StorageManager):
    """统一查看验证码（列表 + 详情 + 搜索）"""
    all_accounts = storage.get_all_accounts()
    if not all_accounts:
        ui.print_line("\n暂无账号，请先添加。")
        return

    accounts = all_accounts  # 当前显示的列表（全量或搜索结果）
    searching = False

    while True:
        ui.clear()  # 进入列表页/迭代：清屏重绘整页

        # 显示账号列表（按分类分组），返回按显示顺序排列的列表
        ui.print_line(f"\n共 {len(accounts)} 个账号：")
        accounts = list_accounts_grouped(accounts)
        ui.print_line("─" * 50)
        if searching:
            ui.print_line("  输入编号查看详情 | 0 返回全量列表 | 输入文字搜索")
        else:
            ui.print_line("  输入编号查看详情 | 0 返回主菜单 | 输入文字搜索")

        raw = ui.prompt("\n>>> ").strip()

        if raw == '0':
            if searching:
                searching = False
                accounts = all_accounts  # 返回全量列表
                continue
            break  # 返回主菜单

        if raw == '':
            continue  # 空输入不操作

        if raw.isdigit():
            idx = int(raw)
            if idx < 1 or idx > len(accounts):
                ui.print_line("✗ 无效的选择！")
                continue
            account = accounts[idx - 1]
        else:
            # 非数字 → 搜索 issuer/account/notes
            keyword = raw.lower()
            accounts = [
                a for a in all_accounts
                if keyword in a.issuer.lower()
                or keyword in a.account.lower()
                or keyword in (a.notes or '').lower()
            ]
            searching = True
            if not accounts:
                ui.print_line("✗ 未找到匹配账号，已返回全量列表。")
                accounts = all_accounts
                searching = False
            continue
        try:
            secret = storage.get_secret(account.id)
        except Exception as e:
            ui.print_line(f"✗ 获取密钥失败: {e}")
            continue

        # 进入详情页
        if ui.tui_enabled():
            # TUI：每秒清屏重画验证码框，非阻塞等 Enter
            while True:
                ui.clear()
                display_account_with_code(account, secret)
                if ui.wait_key(timeout=1.0):
                    break
        else:
            # 非 TUI：清屏 no-op，一次渲染后阻塞等 Enter
            ui.clear()
            display_account_with_code(account, secret)
            ui.prompt(">>> ")


@_cancelable
def handle_edit_account(storage: StorageManager):
    """处理编辑账号"""
    accounts = storage.get_all_accounts()
    if not accounts:
        ui.print_line("\n暂无账号。")
        return

    ui.print_line("\n选择要编辑的账号（按分类分组）：")
    accounts = list_accounts_grouped(accounts)

    try:
        idx = ui.prompt("输入账号编号 (0 取消): ").strip()
        if idx == '0':
            return

        idx = int(idx)
        if idx < 1 or idx > len(accounts):
            ui.print_line("✗ 无效的选择！")
            return
    except ValueError:
        ui.print_line("✗ 请输入数字！")
        return

    account = accounts[idx - 1]

    ui.print_line(f"\n当前信息：")
    ui.print_line(f"  服务提供商: {account.issuer}")
    ui.print_line(f"  账号:       {account.account}")
    ui.print_line(f"  分类:       {account.category}")
    ui.print_line(f"  备注:       {account.notes or '(空)'}")

    ui.print_line("\n输入新值（直接回车保持不变，输入 . 清空）：")

    category = ui.prompt(f"  分类 [{account.category}]: ").strip()
    notes = ui.prompt(f"  备注 [{account.notes or ''}]: ").strip()

    updates = {}
    changes = []
    if category == '.':
        # 清空分类 → 回 default
        if account.category != 'default':
            updates['category'] = 'default'
            changes.append(f"分类: {account.category} → default")
    elif category and category != account.category:
        updates['category'] = category
        changes.append(f"分类: {account.category} → {category}")

    if notes == '.':
        # 清空备注
        if account.notes:
            updates['notes'] = ''
            changes.append(f"备注: {account.notes or '(空)'} → (空)")
    elif notes and notes != account.notes:
        updates['notes'] = notes
        changes.append(f"备注: {account.notes or '(空)'} → {notes}")

    if updates:
        if storage.update_account(account.id, **updates):
            ui.print_line("✓ 更新成功！")
            for c in changes:
                ui.print_line(f"  {c}")
        else:
            ui.print_line("✗ 更新失败！")
    else:
        ui.print_line("未做任何修改。")


@_cancelable
def handle_delete_account(storage: StorageManager):
    """处理删除账号"""
    accounts = storage.get_all_accounts()
    if not accounts:
        ui.print_line("\n暂无账号。")
        return

    ui.print_line("\n选择要删除的账号（按分类分组）：")
    accounts = list_accounts_grouped(accounts)

    try:
        idx = ui.prompt("输入账号编号 (0 取消): ").strip()
        if idx == '0':
            return

        idx = int(idx)
        if idx < 1 or idx > len(accounts):
            ui.print_line("✗ 无效的选择！")
            return
    except ValueError:
        ui.print_line("✗ 请输入数字！")
        return

    account = accounts[idx - 1]
    confirm_phrase = f"YES, delete {account.issuer} - {account.account}"

    ui.print_line(f"\n确定要删除以下账号吗？")
    ui.print_line(f"  服务提供商: {account.issuer}")
    ui.print_line(f"  账号: {account.account}")
    ui.print_line("\n⚠️  此操作不可恢复！")
    ui.print_line("请输入以下内容确认删除：")
    ui.print_line(f"  {confirm_phrase}")

    confirm = ui.prompt("\n>>> ").strip()
    if confirm != confirm_phrase:
        ui.print_line("已取消。")
        return

    if storage.delete_account(account.id):
        ui.print_line(f"✓ 已删除: {account.issuer} - {account.account}")
    else:
        ui.print_line("✗ 删除失败！")


@_cancelable
def handle_export(storage: StorageManager):
    """处理导出备份"""
    backup_dir = get_backup_dir()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    default_path = backup_dir / f'mini2fa_backup_{timestamp}.json'

    user_path = ui.prompt(f"\n导出路径（直接回车使用默认）:\n  [{default_path}]: ").strip()

    # 移除路径两端的引号
    if user_path.startswith('"') and user_path.endswith('"'):
        user_path = user_path[1:-1]
    elif user_path.startswith("'") and user_path.endswith("'"):
        user_path = user_path[1:-1]

    if not user_path:
        backup_path = default_path
    elif os.path.isdir(user_path):
        # 用户指定了已有目录，使用默认文件名
        backup_path = Path(user_path) / default_path.name
    else:
        backup_path = Path(user_path)

    # 检查文件名是否包含非法字符
    invalid_chars = set('*?<>|"')
    if user_path and any(c in os.path.basename(backup_path) for c in invalid_chars):
        ui.print_line("✗ 文件名包含非法字符（* ? < > | \"），请重新输入。")
        return

    # 目标文件已存在时确认覆盖
    if backup_path.exists():
        confirm = ui.prompt(f"\n文件已存在：{backup_path}\n覆盖？[y/N]: ").strip().lower()
        if confirm not in ('y', 'yes'):
            ui.print_line("已取消。")
            return

    # 确保父目录存在
    backup_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        count = storage.export_json(str(backup_path))
        ui.print_line("✓ 导出成功！")
        ui.print_line()
        ui.print_line(f"  备份文件: {backup_path}")
        ui.print_line(f"  账号数量: {count}")
        ui.print_line()
        ui.print_line("  注意：备份文件仍需主密码才能解密。")
    except Exception as e:
        ui.print_line(f"✗ 导出失败: {e}")


@_cancelable
def handle_change_password(crypto: CryptoManager):
    """处理修改主密码（验证旧密码 → 新密码 → 重设提示）"""
    ui.print_line("\n🔒 修改主密码")

    # 1. 验证旧密码（最多 3 次，验证失败不污染当前会话）
    for attempt in range(3):
        old_pwd = ui.password_prompt("输入当前主密码: ")
        if crypto.verify_password(old_pwd):
            break
        ui.print_line("✗ 旧密码错误！")
        if attempt < 2:
            ui.print_line(f"  剩余 {2 - attempt} 次尝试。")
    else:
        ui.print_line("✗ 验证失败次数过多，已返回主菜单。")
        return

    ui.print_line("✓ 旧密码验证通过！")

    # 2. 输入新密码（复用密码强度校验）
    for attempt in range(MAX_PASSWORD_ATTEMPTS):
        new_pwd = ui.password_prompt("输入新主密码: ")
        valid, msg = _validate_password_strength(new_pwd)
        if not valid:
            ui.print_line(f"✗ {msg}")
            remaining = MAX_PASSWORD_ATTEMPTS - attempt - 1
            if remaining > 0:
                ui.print_line(f"  还需满足要求，剩余 {remaining} 次尝试。")
            continue

        new_confirm = ui.password_prompt("确认新主密码: ")
        if new_pwd == new_confirm:
            break
        ui.print_line("✗ 两次密码不一致！")
        remaining = MAX_PASSWORD_ATTEMPTS - attempt - 1
        if remaining > 0:
            ui.print_line(f"  请重新输入，剩余 {remaining} 次尝试。")
    else:
        ui.print_line(f"\n✗ 新密码设置失败：已尝试 {MAX_PASSWORD_ATTEMPTS} 次。")
        ui.print_line("  请重新运行 mini2fa 重试。")
        return

    # 3. 重设密保提示（回车保留原提示）
    hint = ui.prompt("设置新的密码提示（直接回车保留原提示）: ").strip()
    if not hint:
        hint = crypto.get_hint()

    # 4. 执行修改
    if crypto.change_password(old_pwd, new_pwd, hint):
        ui.print_line("✓ 主密码已修改成功！请记住新密码。")
    else:
        ui.print_line("✗ 修改失败！")


def _print_import_result(result: dict):
    """打印导入结果统计"""
    parts = [f"新增 {result['imported']} 个"]
    if result['updated']:
        parts.append(f"更新 {result['updated']} 个")
    if result['conflict_skipped']:
        parts.append(f"保留当前 {result['conflict_skipped']} 个")
    if result['damaged_skipped']:
        parts.append(f"损坏跳过 {result['damaged_skipped']} 个")
    ui.print_line("✓ 导入完成：" + "，".join(parts))


@_cancelable
def handle_import(storage: StorageManager):
    """处理导入备份"""
    input_path = ui.prompt("\n请输入备份文件路径: ").strip()

    if not input_path:
        ui.print_line("✗ 路径不能为空！")
        return

    # 移除路径两端的引号
    if input_path.startswith('"') and input_path.endswith('"'):
        input_path = input_path[1:-1]
    elif input_path.startswith("'") and input_path.endswith("'"):
        input_path = input_path[1:-1]

    # 检查文件名是否包含非法字符
    invalid_chars = set('*?<>|"')
    if any(c in os.path.basename(input_path) for c in invalid_chars):
        ui.print_line("✗ 文件名包含非法字符（* ? < > | \"），请重新输入。")
        return

    if not os.path.exists(input_path):
        ui.print_line("✗ 文件不存在！")
        return

    try:
        # 判断备份是否内嵌主密钥（跨机备份）
        with open(input_path, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        embedded_key = backup_data.get('master_key')

        # 跨机备份：验证备份密码并解出备份主密钥
        external_key = None
        if embedded_key is not None:
            ui.print_line("\n检测到备份来自其他安装（内嵌主密钥）。")
            bk_pwd = ui.password_prompt("请输入备份对应的主密码: ")
            try:
                external_key = storage.crypto.load_external_key(embedded_key, bk_pwd)
            except ValueError as e:
                ui.print_line(f"✗ {e}")
                return
            if external_key is None:
                ui.print_line("✗ 备份主密码错误！")
                return
            ui.print_line("✓ 备份主密码验证通过！")

        # 预览（同机/跨机都用 external_key 做解密校验）
        preview = storage.preview_import(input_path, external_key=external_key)

        if preview['total'] == 0:
            ui.print_line("✗ 备份文件中没有账号数据。")
            return

        ui.print_line("\n📋 备份文件预览：")
        ui.print_line("─" * 60)

        if preview['to_import']:
            ui.print_line(f"  将导入（{len(preview['to_import'])} 个）：")
            for acc in preview['to_import']:
                ui.print_line(f"    ✓ {acc['issuer']} - {acc['account']}")

        if preview['to_skip']:
            ui.print_line(f"  已存在（{len(preview['to_skip'])} 个）：")
            for acc in preview['to_skip']:
                ui.print_line(f"    - {acc['issuer']} - {acc['account']}")

        if preview['damaged']:
            ui.print_line(f"  损坏无法导入（{len(preview['damaged'])} 个）：")
            for acc in preview['damaged']:
                ui.print_line(f"    ✗ {acc['issuer']} - {acc['account']}")

        ui.print_line("─" * 60)
        ui.print_line(f"  共 {preview['total']} 个，将导入 {len(preview['to_import'])} 个")

        if not preview['to_import']:
            ui.print_line("  没有新账号需要导入。")
            return

        confirm = ui.prompt("\n确认导入？[Y/n]: ").strip().lower()
        if confirm not in ('', 'y', 'yes'):
            ui.print_line("已取消。")
            return

        # 冲突账号（库里已存在）逐账号询问：用当前的还是备份的
        decisions = {}
        if preview['to_skip']:
            ui.print_line(f"\n以下 {len(preview['to_skip'])} 个账号在库中已存在，请选择使用哪个版本：")
            for acc in preview['to_skip']:
                ui.print_line(f"  {acc['issuer']} - {acc['account']}")
                choice = ui.prompt("    用当前的还是备份的？[当前/备份，默认当前]: ").strip().lower()
                if choice in ('备份', 'backup', 'b'):
                    decisions[(acc['issuer'], acc['account'])] = 'backup'
                # 其余（含回车）保留当前

        # 按本机状态分流导入
        local_has_accounts = bool(storage.get_all_accounts())

        if external_key is not None and not local_has_accounts:
            # 情况 A：本机空库。先采用备份主密钥，再原样入库
            # （此时 self.key 已是备份 key，能解密备份数据）
            storage.crypto.adopt_external_key(external_key, embedded_key)
            result = storage.import_json(input_path, decisions=decisions)
            _print_import_result(result)
            ui.print_line("✓ 已采用备份的主密钥，请用备份对应的主密码登录本工具。")
        elif external_key is not None:
            # 情况 B：本机已有账号，用备份密钥解密重加密，本机密码不变
            result = storage.import_json(input_path, external_key=external_key, decisions=decisions)
            _print_import_result(result)
        else:
            # 同机备份：现有逻辑
            result = storage.import_json(input_path, decisions=decisions)
            _print_import_result(result)
    except json.JSONDecodeError:
        ui.print_line("✗ 导入失败：备份文件格式错误，不是有效的 JSON 文件。")
    except Exception as e:
        err_msg = str(e)
        if 'InvalidTag' in err_msg or 'decrypt' in err_msg.lower():
            ui.print_line("✗ 导入失败：无法解密备份文件，可能是主密码不匹配或文件已损坏。")
        else:
            ui.print_line(f"✗ 导入失败: {e}")


def _build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器（供 main 与未来命令行子命令复用）"""
    from . import __version__
    parser = argparse.ArgumentParser(
        prog='mini2fa',
        description='安全的本地 TOTP 双因素认证管理工具',
    )
    parser.add_argument(
        '--no-tui', action='store_true',
        help='禁用终端 UI，使用纯文本输出（脚本/CI 用）',
    )
    parser.add_argument(
        '--version', action='version', version=f'mini2fa {__version__}',
        help='显示版本号并退出',
    )
    return parser


def main(argv=None):
    """主程序（所有入口统一调用：console script、python -m、_run）

    Args:
        argv: 命令行参数列表（None 时用 sys.argv[1:]）。
              由 argparse 解析，支持 --no-tui、--version。

    Ctrl-C 在任意阶段（含主密码输入）都被捕获，优雅退出。
    """
    args = _build_parser().parse_args(argv)
    ui.configure(no_tui=args.no_tui)
    ui.enter()
    try:
        try:
            _main_inner()
        except KeyboardInterrupt:
            ui.print_line("\n再见！🔒")
            sys.exit(0)
    finally:
        ui.leave()


def _main_inner():
    """程序主体（不含 TUI 生命周期）"""
    ui.clear()  # 启动：清屏后显示 banner，保证顶部干净
    display_banner()

    # 初始化数据目录
    init_data_dir()

    # 获取配置路径
    db_path = str(get_db_path())
    key_path = str(get_key_path())

    # 初始化加密管理器
    crypto = CryptoManager(key_path)

    # 主密码验证
    if not os.path.exists(key_path):
        ui.print_line("首次使用，请设置主密码：")
        ui.print_line("⚠️  请牢记此密码，丢失将无法恢复数据！")
        ui.print_line(f"密码要求：{PASSWORD_REQUIREMENTS}")

        pwd = None
        for attempt in range(MAX_PASSWORD_ATTEMPTS):
            pwd = ui.password_prompt("输入主密码: ")
            valid, msg = _validate_password_strength(pwd)
            if not valid:
                ui.print_line(f"✗ {msg}")
                remaining = MAX_PASSWORD_ATTEMPTS - attempt - 1
                if remaining > 0:
                    ui.print_line(f"  还需满足要求，剩余 {remaining} 次尝试。")
                continue

            pwd_confirm = ui.password_prompt("确认主密码: ")
            if pwd == pwd_confirm:
                break
            ui.print_line("✗ 两次密码不一致！")
            remaining = MAX_PASSWORD_ATTEMPTS - attempt - 1
            if remaining > 0:
                ui.print_line(f"  请重新输入，剩余 {remaining} 次尝试。")
        else:
            ui.print_line(f"\n✗ 主密码设置失败：已尝试 {MAX_PASSWORD_ATTEMPTS} 次。")
            ui.print_line("  请重新运行 mini2fa 重新设置。")
            sys.exit(1)

        # 设置密保提示
        hint = ui.password_prompt("设置密码提示（用于忘记密码时提醒，可留空）: ").strip()

        if crypto.initialize(pwd, hint):
            ui.print_line("✓ 主密码已设置成功！")
        else:
            ui.print_line("✗ 初始化失败！")
            sys.exit(1)
    else:
        # 获取密保提示
        hint = crypto.get_hint()

        ui.print_line("请输入主密码：")

        for attempt in range(3):
            pwd = ui.password_prompt(">>> ")
            if crypto.initialize(pwd):
                ui.print_line("✓ 密码验证成功！")
                break
            if attempt < 2:
                ui.print_line("✗ 密码错误")
                if hint:
                    ui.print_line(f"💡 密码提示：{hint}")
        else:
            ui.print_line("✗ 密码错误")
            sys.exit(1)

    # 初始化存储管理器
    storage = StorageManager(db_path, crypto)

    # 主循环
    while True:
        ui.clear()  # 每次回到主菜单：清屏重绘，保证菜单在顶部
        display_menu()

        choice = ui.prompt("请选择操作 [0-7]: ").strip()

        if choice == '0':
            ui.print_line("\n再见！🔒")
            break

        elif choice == '1':
            handle_add_account(storage)

        elif choice == '2':
            handle_view_code(storage)

        elif choice == '3':
            handle_edit_account(storage)

        elif choice == '4':
            handle_delete_account(storage)

        elif choice == '5':
            handle_export(storage)

        elif choice == '6':
            handle_import(storage)

        elif choice == '7':
            handle_change_password(crypto)

        else:
            ui.print_line("✗ 无效的选择，请重试！")


def _run():
    """程序入口：捕获 Ctrl-C 优雅退出、数据库损坏提示"""
    try:
        main()
    except KeyboardInterrupt:
        ui.print_line("\n再见！🔒")
        sys.exit(0)
    except StorageCorruptedError as e:
        ui.print_line(f"\n✗ {e}")
        ui.print_line("  请检查数据文件是否完整，或从备份恢复。")
        sys.exit(1)


if __name__ == '__main__':
    _run()
