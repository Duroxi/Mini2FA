"""
终端 UI 层（统一输出/输入接口）

业务层（_cli.py）只调用本模块接口，不直接 print/input：
  print_line / print_lines / print_box / prompt / password_prompt / clear

行为一致性（两种模式行为一致，差异只在内部实现）：
- 真实终端（TTY）: 输出追加到备用屏幕；enter/leave 切换备用屏幕，退出后无残留
- 非 TTY（管道/CI/--no-tui）: 等价 print/input 自动降级
- clear 在 TTY 下清屏（页面入口/循环迭代调用），非 TTY no-op
"""
import os
import sys
import atexit

# ANSI 序列
_ENTER_ALT = '\x1b[?1049h'   # 进入备用屏幕
_LEAVE_ALT = '\x1b[?1049l'   # 退出备用屏幕
_CLEAR_ALL = '\x1b[2J'       # 清屏
_MOVE_HOME = '\x1b[H'        # 光标归位
_CURSOR_OFF = '\x1b[?25l'    # 隐藏光标
_CURSOR_ON = '\x1b[?25h'     # 显示光标

# 模块级配置（由 _cli.configure() 设置；默认按 TTY 自动判定）
_no_tui = False


def _is_tty() -> bool:
    """stdout/stdin 都是真实终端时才启用 TUI"""
    try:
        return sys.stdout.isatty() and sys.stdin.isatty()
    except (AttributeError, ValueError):
        return False


def configure(no_tui: bool = False):
    """由 _cli 在 main() 开头调用，设置 TUI 开关（默认自动判定）"""
    global _no_tui
    _no_tui = bool(no_tui)


def tui_enabled() -> bool:
    """当前是否处于 TUI 模式"""
    return not _no_tui and _is_tty()


def enter():
    """进入 TUI：切备用屏幕并清空。非 TTY 下 no-op"""
    if not tui_enabled():
        return
    sys.stdout.write(_ENTER_ALT + _CURSOR_OFF + _CLEAR_ALL)
    sys.stdout.flush()
    # 兜底：即使发生未捕获异常，进程退出时也恢复主屏幕
    atexit.register(leave)


def leave():
    """退出 TUI：恢复主屏幕。非 TTY 下 no-op"""
    if not tui_enabled():
        return
    sys.stdout.write(_CURSOR_ON + _LEAVE_ALT)
    sys.stdout.flush()


# ---------------------------------------------------------------
# 统一输出接口（追加式，两模式行为一致）
# ---------------------------------------------------------------

def print_line(text: str = ''):
    """输出一行（追加到当前输出末尾）"""
    print(text)


def print_lines(lines: list):
    """输出多行（追加）"""
    for line in lines:
        print(line)


def print_box(lines: list, width: int = 55):
    """输出一个边框盒子（追加，不清屏）

    Args:
        lines: 内容行列表（不含边框）
        width: 边框内部总显示宽度（按 wcswidth 计算，中文/emoji 宽 2）
    """
    from wcwidth import wcswidth
    top = '╔' + '═' * (width - 2) + '╗'
    bottom = '╚' + '═' * (width - 2) + '╝'
    print(top)
    for line in lines:
        pad_w = width - wcswidth(line) - 2
        if pad_w < 1:  # 内容超宽时不再硬填，保持内容完整
            print('║' + line + '║')
        else:
            print('║' + line + ' ' * pad_w + '║')
    print(bottom)


def prompt(text: str) -> str:
    """显示提示并读取输入（提示只显示一次）"""
    return input(text)


def password_prompt(text: str) -> str:
    """显示提示并读取隐藏输入（提示只显示一次）"""
    import getpass as _getpass
    return _getpass.getpass(text)


def clear():
    """清屏（仅 TTY 模式生效；非 TTY no-op）。

    页面入口/交互循环迭代时调用，保证整屏干净；
    普通流程内的输出全部追加，不清屏。
    """
    if tui_enabled():
        sys.stdout.write(_CLEAR_ALL + _MOVE_HOME)
        sys.stdout.flush()


def wait_key(timeout=1.0) -> bool:
    """非阻塞等待 Enter（仅 TUI 模式轮询用）

    TTY 模式：轮询 stdin，超时返回 False，收到 Enter 返回 True。
    非 TTY：不适用（调用方应使用 prompt 阻塞）；此处等价阻塞 input()。

    Returns:
        True = 收到 Enter；False = 超时（仅 TTY 模式）
    """
    if not tui_enabled():
        input()  # 降级：等价阻塞等 Enter（供测试/非 TUI 调用）
        return True
    return _wait_key_impl(timeout)


def _wait_key_impl(timeout):
    """平台相关的非阻塞轮询实现"""
    if os.name == 'nt':
        return _wait_key_windows(timeout)
    return _wait_key_unix(timeout)


def _wait_key_windows(timeout):
    """Windows: msvcrt 非阻塞轮询，Ctrl-C 转 KeyboardInterrupt"""
    import msvcrt
    import time
    deadline = time.time() + timeout
    while time.time() < deadline:
        if msvcrt.kbhit():
            key = msvcrt.getwch()
            if key == '\r':
                return True
            if key == '\x03':
                raise KeyboardInterrupt
        else:
            time.sleep(0.02)
    return False


def _wait_key_unix(timeout):
    """Unix: termios raw 模式 + select 轮询，退出必须恢复终端"""
    import select
    import termios
    import tty
    import time

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)  # raw 模式：按键不换行、不回显
        deadline = time.time() + timeout
        while time.time() < deadline:
            if select.select([sys.stdin], [], [], 0.02)[0]:
                ch = sys.stdin.read(1)
                if ch in ('\r', '\n'):
                    return True
                if ch == '\x03':
                    raise KeyboardInterrupt
        return False
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
