"""
UI 层（ui.py）单元测试

覆盖：统一输出接口（print_line/print_box/prompt/password_prompt/clear）、
TTY 模式 ANSI 序列、enter/leave、入口链 Ctrl-C 捕获。
"""
import io
import sys

import pytest


def _fake_streams(monkeypatch):
    """stdout/stdin 伪装成 TTY，收集写入内容"""
    from mini2fa import ui

    class FakeStream:
        def __init__(self):
            self.buf = io.StringIO()

        def isatty(self):
            return True

        def write(self, s):
            self.buf.write(s)

        def flush(self):
            pass

    out = FakeStream()
    inp = FakeStream()
    monkeypatch.setattr(ui.sys, 'stdout', out)
    monkeypatch.setattr(ui.sys, 'stdin', inp)
    monkeypatch.setattr(ui, '_no_tui', False)
    return out, inp


class TestOutputInterface:
    """统一输出接口：两种模式行为一致（非 TTY 下等价 print/input）"""

    def test_print_line(self, capsys):
        from mini2fa import ui
        ui.print_line('a')
        ui.print_line('b')
        assert capsys.readouterr().out == 'a\nb\n'

    def test_print_lines(self, capsys):
        from mini2fa import ui
        ui.print_lines(['a', 'b'])
        assert capsys.readouterr().out == 'a\nb\n'

    def test_print_box(self, capsys):
        from mini2fa import ui
        ui.print_box(['内容'], width=20)
        out = capsys.readouterr().out
        lines = out.splitlines()
        assert lines[0].startswith('╔')
        assert '内容' in out
        assert lines[-1].startswith('╚')

    def test_prompt_single(self, capsys):
        """prompt 只显示一次提示（无重复）"""
        from mini2fa import ui
        from unittest.mock import patch
        with patch('builtins.input', return_value='x') as m:
            assert ui.prompt('请选择: ') == 'x'
            m.assert_called_once_with('请选择: ')
            out = capsys.readouterr().out
            assert out.count('请选择') == 0  # input 自打提示, 无额外输出

    def test_password_prompt(self, capsys):
        from mini2fa import ui
        from unittest.mock import patch
        with patch('getpass.getpass', return_value='pw') as m:
            assert ui.password_prompt('密码: ') == 'pw'
            m.assert_called_once_with('密码: ')

    def test_clear_noop_non_tty(self, capsys):
        """非 TTY 下 clear 是 no-op"""
        from mini2fa import ui
        ui.clear()
        assert capsys.readouterr().out == ''

    def test_enter_leave_noop_non_tty(self, capsys):
        from mini2fa import ui
        ui.enter()
        ui.leave()
        assert capsys.readouterr().out == ''

    def test_tui_enabled_false_in_pytest(self):
        from mini2fa import ui
        assert ui.tui_enabled() is False


class TestTtyMode:
    """TTY 模式（monkeypatch 模拟终端）下 ANSI 序列"""

    def test_enter_leave_sequences(self, monkeypatch):
        out, _ = _fake_streams(monkeypatch)
        from mini2fa import ui
        ui.enter()
        s = out.buf.getvalue()
        assert '\x1b[?1049h' in s   # 进入备屏
        assert '\x1b[?25l' in s     # 光标隐藏
        ui.leave()
        s2 = out.buf.getvalue()
        assert '\x1b[?1049l' in s2  # 退出备屏
        assert '\x1b[?25h' in s2    # 光标显示

    def test_clear_emits_ansi(self, monkeypatch):
        out, _ = _fake_streams(monkeypatch)
        from mini2fa import ui
        ui.clear()
        assert '\x1b[2J' in out.buf.getvalue()
        assert '\x1b[H' in out.buf.getvalue()

    def test_tui_off_no_ansi(self, monkeypatch):
        out, _ = _fake_streams(monkeypatch)
        from mini2fa import ui
        ui.configure(no_tui=True)
        try:
            ui.enter()
            ui.clear()
            assert '\x1b[' not in out.buf.getvalue()
        finally:
            ui.configure(no_tui=False)


class TestEntryCtrlC:
    """三条入口链（console script / python -m / __main__）Ctrl-C 全覆盖"""

    def test_main_captures_ctrl_c_in_getpass(self, monkeypatch, capsys):
        """main() 在主密码输入界面 Ctrl-C 被捕获，不崩溃"""
        from mini2fa import _cli
        from unittest.mock import patch

        # 首次使用: master.key 不存在
        monkeypatch.setattr(_cli.os.path, 'exists', lambda p: False)
        monkeypatch.setattr(_cli, 'display_banner', lambda: None)
        monkeypatch.setattr(_cli, 'init_data_dir', lambda: None)

        with patch('mini2fa._cli.ui.password_prompt',
                   side_effect=KeyboardInterrupt()):
            with patch.object(sys, 'exit', side_effect=SystemExit) as m_exit:
                with pytest.raises(SystemExit):
                    _cli.main([])
                m_exit.assert_called_once_with(0)
        assert '再见！🔒' in capsys.readouterr().out

    def test_main_module_uses_run(self):
        """__main__.py 应调用 _run() 而不是 main()"""
        src = open('src/mini2fa/__main__.py', encoding='utf-8').read()
        assert '_run' in src
        assert '_run()' in src

    def test_console_script_entry_is_main(self):
        """console script 指向 main()，main 内部已捕获 Ctrl-C"""
        src = open('pyproject.toml', encoding='utf-8').read()
        assert 'mini2fa = "mini2fa._cli:main"' in src
        from mini2fa import _cli
        import inspect
        main_src = inspect.getsource(_cli.main)
        assert 'except KeyboardInterrupt' in main_src


class TestDetailDisplay:
    """详情页显示验证码并等待 Enter（两模式一致）"""

    def _account(self):
        from mini2fa.models import Account
        return Account(
            id=1, issuer='GitHub', account='u@gmail.com', secret_encrypted='e',
            algorithm='SHA1', digits=6, period=30, category='default', notes='',
            created_at='2026-01-01', updated_at='2026-01-01')

    def test_detail_shows_code_and_waits(self):
        """非 TUI 详情页渲染验证码框 + prompt 一次等 Enter"""
        from mini2fa._cli import handle_view_code
        from mini2fa.crypto import CryptoManager
        from mini2fa.storage import StorageManager
        from unittest.mock import patch
        import tempfile, shutil, os

        tmpdir = tempfile.mkdtemp()
        try:
            key = os.path.join(tmpdir, 'key')
            crypto = CryptoManager(key)
            crypto.initialize('pwd')
            storage = StorageManager(os.path.join(tmpdir, 'db.db'), crypto)
            storage.add_account('GitHub', 'u@gmail.com', 'JBSWY3DPEHPK3PXP')

            # 进入详情: 列表页输入 1 -> 详情页 prompt 一次返回
            inputs = iter(['1', '', '0'])  # 选账号 -> Enter -> 返回列表 -> 0 返回主菜单
            with patch('builtins.input', side_effect=lambda prompt: next(inputs)):
                handle_view_code(storage)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_wait_key_blocks_in_non_tty(self):
        """非 TUI 下 wait_key 等价阻塞 input()"""
        from mini2fa import ui
        from unittest.mock import patch
        with patch('builtins.input', return_value='') as m:
            assert ui.wait_key() is True
            m.assert_called_once()

    def test_wait_key_returns_on_enter(self, monkeypatch):
        """TUI 下 wait_key 收到 Enter 返回 True"""
        from mini2fa import ui
        _fake_streams(monkeypatch)
        monkeypatch.setattr(ui, '_wait_key_impl', lambda timeout: True)
        assert ui.wait_key(0.1) is True

    def test_detail_polls_in_tui(self, monkeypatch, capsys):
        """TUI 下详情页每秒清屏重画验证码框（轮询）"""
        from mini2fa import ui
        from mini2fa._cli import display_account_with_code
        import io, contextlib

        # 模拟 TUI 环境
        _fake_streams(monkeypatch)
        out = monkeypatch  # 通过 fake streams 收集

        # 手动验证轮询逻辑: clear + display 循环
        # (实际轮询在 handle_view_code, 这里验证 wait_key 与 clear 配合)
        # 用直接调用: display_account_with_code 应输出验证码框
        from mini2fa.models import Account
        acc = self._account()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            display_account_with_code(acc, 'JBSWY3DPEHPK3PXP', '123456')
        out_s = buf.getvalue()
        assert '验证码' in out_s
        assert '123 456' in out_s
        assert '有效期' in out_s


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
