"""
终端 UI 层（零依赖 ANSI 轻量 TUI）

提供两套渲染行为，自动降级：
- TTY 模式：备用屏幕（alt screen）整屏重绘，退出后终端无残留；
          详情页支持非阻塞按键轮询 + 每秒刷新
- 非 TTY 模式（管道/IDE/pytest）：等价于 print + input，行为与旧版一致

所有 ANSI 序列只对 TTY 发出；非 TTY 下所有函数均为安全 no-op 或 print 降级。
"""
import os
import sys
import atexit

# 终端控制序列
_ENTER_ALT = '\x1b[?1049h'   # 进入备用屏幕（自动清空备屏）
_LEAVE_ALT = '\x1b[?1049l'   # 退出备用屏幕，恢复主屏幕
_CLEAR_ALL = '\x1b[2J'       # 清屏
_MOVE_HOME = '\x1b[H'        # 光标移到左上角
_CURSOR_OFF = '\x1b[?25l'    # 隐藏光标
_CURSOR_ON = '\x1b[?25l'.replace('l', 'h')  # 显示光标
_CLEAR_TO_EOL = '\x1b[0K'    # 清除光标右侧到行尾
_CLEAR_TO_BOTTOM = '\x1b[0J' # 清除光标下方全部

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


def render(lines, prompt='', start_line=0, end_line=None):
    """整屏重绘一帧

    在 TUI 模式下，将光标移动到 start_line 行首，逐行清除并重画
    [start_line, end_line) 区域，最后把光标停在 prompt 所在行，等待输入。

    Args:
        lines: 内容行列表（不含边框）
        prompt: 输入提示，渲染在最后一行（TUI 下不可见实际输入内容之外）
        start_line: 从第几行开始重绘（0 = 光标归位整屏重绘）
        end_line: 重绘到第几行（None = 清除底部剩余内容）
    """
    if not tui_enabled():
        # 降级：等价于 print 逐行输出
        for line in lines:
            print(line)
        sys.stdout.write(prompt)
        sys.stdout.flush()
        return

    out = []
    if start_line == 0:
        out.append(_MOVE_HOME)
    else:
        out.append(f'\x1b[{start_line + 1}A')  # 上移 start_line 行
    out.append(_CURSOR_ON)  # 输入提示时显示光标

    for i, line in enumerate(lines):
        if end_line is not None and i >= end_line - start_line:
            break
        out.append(_CLEAR_TO_EOL + line + '\n')
    if end_line is None:
        out.append(_CLEAR_TO_BOTTOM)
    out.append(_CURSOR_OFF)  # 输入提示完成，隐藏光标避免残留
    out.append(prompt)
    sys.stdout.write(''.join(out))
    sys.stdout.flush()


def wait_enter(timeout=1.0):
    """非阻塞等待 Enter 键（或任意结束键）

    TTY 模式下：轮询 stdin，超时返回 False，收到 Enter 返回 True。
    非 TTY 模式下：退化为阻塞 input()（供测试 mock 拦截）。

    Returns:
        True = 收到 Enter；False = 超时（仅 TTY 模式）
    """
    if not tui_enabled():
        input()  # 降级：测试中 mock 拦截
        return True
    return _wait_key(timeout)


# ---------------------------------------------------------------
# 跨平台非阻塞键盘轮询
# ---------------------------------------------------------------

def _wait_key(timeout):
    """平台相关的轮询实现：超时返回 False，Enter 返回 True"""
    if os.name == 'nt':
        return _wait_key_windows(timeout)
    return _wait_key_unix(timeout)


def _wait_key_windows(timeout):
    """Windows: msvcrt 非阻塞轮询，Ctrl-C 转 KeyboardInterrupt"""
    import msvcrt
    deadline = _now() + timeout
    while _now() < deadline:
        if msvcrt.kbhit():
            key = msvcrt.getwch()
            if key == '\r':
                return True
            if key == '\x03':
                raise KeyboardInterrupt
        else:
            _sleep(0.02)
    return False


def _wait_key_unix(timeout):
    """Unix: termios raw 模式 + select 轮询，退出必须恢复终端"""
    import select
    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)  # raw 模式：按键不换行、不回显
        deadline = _now() + timeout
        while _now() < deadline:
            if select.select([sys.stdin], [], [], 0.02)[0]:
                ch = sys.stdin.read(1)
                if ch in ('\r', '\n'):
                    return True
                if ch == '\x03':
                    raise KeyboardInterrupt
        return False
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _now():
    return __import__('time').time()


def _sleep(seconds):
    __import__('time').sleep(seconds)
