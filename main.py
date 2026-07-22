"""
Mini2FA 脚本版 - 主程序

安全的本地 TOTP 验证码管理工具
"""
import os
import sys
import time
import subprocess
import platform
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from core.scanner import scan_qrcode
from core.crypto import CryptoManager
from core.storage import StorageManager
from core.totp import generate_totp, get_remaining_seconds
from core.config import (
    init_data_dir, get_data_dir, get_db_path,
    get_key_path, get_backup_dir
)


def copy_to_clipboard(text: str) -> bool:
    """
    复制文本到剪贴板（跨平台）

    Args:
        text: 要复制的文本

    Returns:
        是否成功
    """
    try:
        system = platform.system()
        if system == 'Windows':
            # Windows 使用 clip 命令
            process = subprocess.run(
                ['clip'],
                input=text.encode('utf-8'),
                check=True,
                capture_output=True
            )
        elif system == 'Darwin':  # macOS
            subprocess.run(['pbcopy'], input=text.encode('utf-8'), check=True)
        else:  # Linux
            try:
                subprocess.run(
                    ['xclip', '-selection', 'clipboard'],
                    input=text.encode('utf-8'),
                    check=True
                )
            except FileNotFoundError:
                subprocess.run(
                    ['xsel', '--clipboard', '--input'],
                    input=text.encode('utf-8'),
                    check=True
                )
        return True
    except Exception:
        return False


def display_account_with_code(account, secret: str):
    """
    显示账号信息和验证码

    Args:
        account: Account 对象
        secret: 明文密钥
    """
    code = generate_totp(secret, account.algorithm, account.digits, account.period)
    remaining = get_remaining_seconds(account.period)

    # 进度条
    progress = '█' * (30 - remaining) + '░' * remaining

    print(f"""
┌─────────────────────────────────────────────────────┐
│  {account.issuer:<25} {account.account:<25} │
│                                                     │
│  验证码:  {code[:3]} {code[3:]}                                 │
│                                                     │
│  有效期: [{progress}] {remaining:2d}s                    │
│                                                     │
│  按 Enter 复制到剪贴板 | 输入 q 返回菜单            │
└─────────────────────────────────────────────────────┘
""")


def display_banner():
    """显示程序横幅"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║                    Mini2FA 脚本版 v1.0                    ║
║           安全的本地 TOTP 验证码管理工具                   ║
║                                                           ║
║  📱 扫码添加 | 🔑 验证码生成 | 🔐 AES-256 加密            ║
╚═══════════════════════════════════════════════════════════╝
    """)


def display_menu():
    """显示主菜单"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║                      主 菜 单                             ║
╠═══════════════════════════════════════════════════════════╣
║  1. 📱  添加账号（扫码图片）                              ║
║  2. 🔑  查看验证码                                        ║
║  3. 📋  账号列表                                          ║
║  4. ✏️   编辑账号                                          ║
║  5. 🗑️   删除账号                                          ║
║  6. 💾  导出备份                                          ║
║  7. 📥  导入备份                                          ║
║  8. 🔄  刷新当前验证码                                    ║
║  0. 🚪  退出                                              ║
╚═══════════════════════════════════════════════════════════╝
    """)


def handle_add_account(storage: StorageManager):
    """处理添加账号"""
    print("\n📱 添加新账号")
    print("-" * 40)

    image_path = input("请输入图片文件路径: ").strip()

    # 移除路径两端的引号（Windows 拖拽文件时会带引号）
    if image_path.startswith('"') and image_path.endswith('"'):
        image_path = image_path[1:-1]
    elif image_path.startswith("'") and image_path.endswith("'"):
        image_path = image_path[1:-1]

    if not os.path.exists(image_path):
        print("✗ 文件不存在！请检查路径。")
        return

    print("正在扫描二维码...")

    try:
        result = scan_qrcode(image_path)
    except Exception as e:
        print(f"✗ 扫描失败: {e}")
        return

    if not result:
        print("✗ 未识别到有效的二维码！")
        print("  提示：请确保图片包含清晰的 OTP 二维码。")
        return

    # 显示识别结果
    print(f"""
✓ 识别到账号信息：
  ─────────────────────────────────────
  服务提供商: {result.issuer}
  账号:       {result.account}
  算法:       {result.algorithm}
  位数:       {result.digits}
  周期:       {result.period}秒
  类型:       {result.otp_type}
    """)

    confirm = input("确认添加？[Y/n]: ").strip().lower()
    if confirm not in ('', 'y', 'yes'):
        print("已取消。")
        return

    # 可选：添加分类和备注
    category = input("分类 (直接回车使用默认): ").strip() or 'default'
    notes = input("备注 (直接回车跳过): ").strip()

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
        print(f"✓ 账号添加成功！(ID: {account_id})")
    except ValueError as e:
        print(f"✗ {e}")


def handle_view_code(storage: StorageManager):
    """处理查看验证码"""
    accounts = storage.get_all_accounts()
    if not accounts:
        print("\n暂无账号，请先添加。")
        return

    print("\n选择账号查看验证码：")
    print("-" * 60)
    for i, acc in enumerate(accounts, 1):
        print(f"  {i:2d}. {acc.issuer:<15} {acc.account:<30}")

    print("-" * 60)

    try:
        idx = input("\n输入账号编号 (0 取消): ").strip()
        if idx == '0':
            return

        idx = int(idx)
        if idx < 1 or idx > len(accounts):
            print("✗ 无效的选择！")
            return
    except ValueError:
        print("✗ 请输入数字！")
        return

    account = accounts[idx - 1]
    secret = storage.get_secret(account.id)

    # 动态刷新验证码
    try:
        while True:
            display_account_with_code(account, secret)
            user_input = input(">>> ").strip()

            if user_input.lower() == 'q':
                break

            # 复制到剪贴板
            code = generate_totp(secret, account.algorithm, account.digits, account.period)
            if copy_to_clipboard(code):
                print(f"✓ 已复制到剪贴板: {code}")
            else:
                print(f"验证码: {code}")
                print("(自动复制失败，请手动复制)")

            # 等待一下再刷新
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n返回主菜单...")


def handle_list_accounts(storage: StorageManager):
    """处理账号列表"""
    accounts = storage.get_all_accounts()

    if not accounts:
        print("\n暂无账号。")
        return

    print(f"\n共 {len(accounts)} 个账号：\n")
    print(f"{'序号':<5} {'服务提供商':<15} {'账号':<30} {'分类':<10}")
    print("─" * 65)

    for i, acc in enumerate(accounts, 1):
        print(f"{i:<5} {acc.issuer:<15} {acc.account:<30} {acc.category:<10}")

    print("─" * 65)


def handle_edit_account(storage: StorageManager):
    """处理编辑账号"""
    accounts = storage.get_all_accounts()
    if not accounts:
        print("\n暂无账号。")
        return

    print("\n选择要编辑的账号：")
    for i, acc in enumerate(accounts, 1):
        print(f"  {i}. {acc.issuer} - {acc.account}")

    try:
        idx = input("\n输入账号编号 (0 取消): ").strip()
        if idx == '0':
            return

        idx = int(idx)
        if idx < 1 or idx > len(accounts):
            print("✗ 无效的选择！")
            return
    except ValueError:
        print("✗ 请输入数字！")
        return

    account = accounts[idx - 1]

    print(f"\n当前信息：")
    print(f"  服务提供商: {account.issuer}")
    print(f"  账号:       {account.account}")
    print(f"  分类:       {account.category}")
    print(f"  备注:       {account.notes or '(空)'}")

    print("\n输入新值（直接回车保持不变）：")

    issuer = input(f"  服务提供商 [{account.issuer}]: ").strip()
    account_name = input(f"  账号 [{account.account}]: ").strip()
    category = input(f"  分类 [{account.category}]: ").strip()
    notes = input(f"  备注 [{account.notes or ''}]: ").strip()

    updates = {}
    if issuer:
        updates['issuer'] = issuer
    if account_name:
        updates['account'] = account_name
    if category:
        updates['category'] = category
    if notes:
        updates['notes'] = notes

    if updates:
        if storage.update_account(account.id, **updates):
            print("✓ 更新成功！")
        else:
            print("✗ 更新失败！")
    else:
        print("未做任何修改。")


def handle_delete_account(storage: StorageManager):
    """处理删除账号"""
    accounts = storage.get_all_accounts()
    if not accounts:
        print("\n暂无账号。")
        return

    print("\n选择要删除的账号：")
    for i, acc in enumerate(accounts, 1):
        print(f"  {i}. {acc.issuer} - {acc.account}")

    try:
        idx = input("\n输入账号编号 (0 取消): ").strip()
        if idx == '0':
            return

        idx = int(idx)
        if idx < 1 or idx > len(accounts):
            print("✗ 无效的选择！")
            return
    except ValueError:
        print("✗ 请输入数字！")
        return

    account = accounts[idx - 1]

    print(f"\n确定要删除以下账号吗？")
    print(f"  服务提供商: {account.issuer}")
    print(f"  账号: {account.account}")
    print("\n⚠️  此操作不可恢复！")

    confirm = input("\n输入 YES 确认删除: ").strip()
    if confirm != 'YES':
        print("已取消。")
        return

    if storage.delete_account(account.id):
        print("✓ 账号已删除。")
    else:
        print("✗ 删除失败！")


def handle_export(storage: StorageManager):
    """处理导出备份"""
    backup_dir = get_backup_dir()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = backup_dir / f'mini2fa_backup_{timestamp}.json'

    try:
        count = storage.export_json(str(backup_path))
        print(f"""
✓ 导出成功！

  备份文件: {backup_path}
  账号数量: {count}

  注意：备份文件仍需主密码才能解密。
        """)
    except Exception as e:
        print(f"✗ 导出失败: {e}")


def handle_import(storage: StorageManager):
    """处理导入备份"""
    input_path = input("\n请输入备份文件路径: ").strip()

    # 移除路径两端的引号
    if input_path.startswith('"') and input_path.endswith('"'):
        input_path = input_path[1:-1]
    elif input_path.startswith("'") and input_path.endswith("'"):
        input_path = input_path[1:-1]

    if not os.path.exists(input_path):
        print("✗ 文件不存在！")
        return

    try:
        count = storage.import_json(input_path)
        print(f"✓ 成功导入 {count} 个账号！")
    except Exception as e:
        print(f"✗ 导入失败: {e}")


def handle_refresh_code(storage: StorageManager):
    """处理刷新验证码"""
    accounts = storage.get_all_accounts()
    if not accounts:
        print("\n暂无账号。")
        return

    # 显示所有账号的当前验证码
    print("\n当前所有验证码：\n")
    print(f"{'序号':<5} {'服务提供商':<15} {'验证码':<10} {'剩余':<8}")
    print("─" * 45)

    for i, acc in enumerate(accounts, 1):
        try:
            secret = storage.get_secret(acc.id)
            code = generate_totp(secret, acc.algorithm, acc.digits, acc.period)
            remaining = get_remaining_seconds(acc.period)
            print(f"{i:<5} {acc.issuer:<15} {code[:3]} {code[3:]:<7} {remaining:2d}s")
        except Exception:
            print(f"{i:<5} {acc.issuer:<15} {'ERROR':<10} -")

    print("─" * 45)


def main():
    """主程序"""
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
        print("首次使用，请设置主密码：")
        print("⚠️  请牢记此密码，丢失将无法恢复数据！\n")

        pwd = input("输入主密码: ")
        if len(pwd) < 6:
            print("✗ 密码长度至少 6 位！")
            sys.exit(1)

        pwd_confirm = input("确认主密码: ")
        if pwd != pwd_confirm:
            print("✗ 两次密码不一致！")
            sys.exit(1)

        # 设置密保提示
        hint = input("设置密码提示（用于忘记密码时提醒，可留空）: ").strip()

        if crypto.initialize(pwd, hint):
            print("✓ 主密码已设置成功！\n")
        else:
            print("✗ 初始化失败！")
            sys.exit(1)
    else:
        # 获取密保提示
        hint = crypto.get_hint()

        print("请输入主密码：")
        if hint:
            print(f"💡 密码提示：{hint}")

        for attempt in range(3):
            pwd = input(">>> ")
            if crypto.initialize(pwd):
                print("✓ 密码验证成功！\n")
                break
            remaining = 2 - attempt
            if remaining > 0:
                print(f"✗ 密码错误！剩余 {remaining} 次机会")
                if hint:
                    print(f"💡 密码提示：{hint}")
        else:
            print("✗ 密码错误次数过多，程序退出")
            sys.exit(1)

    # 初始化存储管理器
    storage = StorageManager(db_path, crypto)

    # 主循环
    while True:
        display_menu()

        choice = input("请选择操作 [0-8]: ").strip()

        if choice == '0':
            print("\n再见！🔒")
            break

        elif choice == '1':
            handle_add_account(storage)

        elif choice == '2':
            handle_view_code(storage)

        elif choice == '3':
            handle_list_accounts(storage)

        elif choice == '4':
            handle_edit_account(storage)

        elif choice == '5':
            handle_delete_account(storage)

        elif choice == '6':
            handle_export(storage)

        elif choice == '7':
            handle_import(storage)

        elif choice == '8':
            handle_refresh_code(storage)

        else:
            print("✗ 无效的选择，请重试！")

        # 按任意键继续
        input("\n按 Enter 继续...")


if __name__ == '__main__':
    main()
