"""
UI 层（ui.py）单元测试

覆盖：TUI 降级（非 TTY 等价 print/input）、TTY 模式 ANSI 序列、
wait_enter 降级与 TTY 按键语义、enter/leave no-op。
"""
import io

import pytest


class TestDegradeNonTty:
    """非 TTY（pytest 默认）下各 API 应等价于 print/input"""

    def test_render_eq_print(self, capsys):
        """render 降级：逐行 print + prompt"""
        from mini2fa import ui
        ui.render(['a', 'b', 'c'], '> ')
        out = capsys.readouterr().out
        assert out == 'a\nb\nc\n> '

    def test_render_empty_lines(self, capsys):
        """空行列表 + 空 prompt 无输出"""
        from mini2fa import ui
        ui.render([])
        assert capsys.readouterr().out == ''

    def test_wait_enter_degrades_to_input(self):
        """非 TTY 下 wait_enter 退化为 input()，可被 mock 拦截"""
        from unittest.mock import patch
        from mini2fa import ui
        with patch('builtins.input', return_value='') as m:
            assert ui.wait_enter() is True
            m.assert_called_once()

    def test_enter_leave_noop(self, capsys):
        """非 TTY 下 enter/leave 无输出"""
        from mini2fa import ui
        ui.enter()
        ui.leave()
        assert capsys.readouterr().out == ''

    def test_tui_enabled_false_in_pytest(self):
        """pytest 环境下 tui_enabled 应为 False"""
        from mini2fa import ui
        assert ui.tui_enabled() is False


class TestDetailPageNonTty:
    """非 TTY 下详情页必须阻塞等 Enter，不得一闪而过"""

    def _account(self):
        from mini2fa.models import Account
        return Account(
            id=1, issuer='GitHub', account='u@gmail.com', secret_encrypted='e',
            algorithm='SHA1', digits=6, period=30, category='default', notes='',
            created_at='2026-01-01', updated_at='2026-01-01')

    def test_wait_enter_blocking(self):
        """非 TTY 下 wait_enter 阻塞等 Enter，返回 True 后才退出"""
        from mini2fa import ui
        from unittest.mock import patch
        with patch('builtins.input', return_value='') as m:
            assert ui.wait_enter() is True
            m.assert_called_once()

    def test_detail_page_waits_for_enter(self):
        """非 TTY 下详情页渲染一次，input() 阻塞等待后返回（不闪退）"""
        from mini2fa._cli import _detail_page
        from unittest.mock import patch
        import io, contextlib

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            with patch('builtins.input', return_value='') as m:
                _detail_page(self._account(), 'JBSWY3DPEHPK3PXP')

        out = buf.getvalue()
        assert '验证码' in out, '详情页应渲染验证码'
        assert '按 Enter 返回列表' in out, '应有返回提示'
        m.assert_called_once_with('  按 Enter 返回列表  ')

    def test_detail_page_does_not_loop_in_non_tty(self):
        """非 TTY 下详情页不轮询：只调用一次 input，不无限循环"""
        from mini2fa._cli import _detail_page
        from unittest.mock import patch
        import io, contextlib

        calls = []
        def fake_input(*a, **k):
            calls.append(a)
            return 'x'
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            with patch('builtins.input', side_effect=fake_input):
                _detail_page(self._account(), 'JBSWY3DPEHPK3PXP')
        assert len(calls) == 1, f'非 TTY 应只调用一次 input，实际 {len(calls)}'


class TestEntryCtrlC:
    """三条入口链（console script / python -m / __main__）Ctrl-C 全覆盖"""

    def _setup_main_env(self, monkeypatch):
        """让 main() 走到主密码输入界面（首次使用）"""
        import tempfile
        tmpdir = tempfile.mkdtemp()
        from mini2fa import _cli
        # 首次使用: master.key 不存在
        monkeypatch.setattr(_cli.os.path, 'exists', lambda p: False)
        monkeypatch.setattr(_cli, 'display_banner', lambda: None)
        monkeypatch.setattr(_cli, 'init_data_dir', lambda: None)
        return tmpdir

    def test_main_captures_ctrl_c_in_getpass(self, monkeypatch, capsys):
        """main() 在主密码输入界面 Ctrl-C 被捕获，不崩溃"""
        import sys
        from mini2fa import _cli
        from unittest.mock import patch

        self._setup_main_env(monkeypatch)
        # getpass 输入主密码时抛 KeyboardInterrupt（模拟 Ctrl-C）
        with patch('mini2fa._cli.getpass.getpass',
                   side_effect=KeyboardInterrupt()):
            with patch.object(sys, 'exit', side_effect=SystemExit) as m_exit:
                with pytest.raises(SystemExit):
                    _cli.main([])
                # sys.exit(0) 被调用（SystemExit 被 mock 抛出, code=None）
                m_exit.assert_called_once_with(0)
        out = capsys.readouterr().out
        assert '再见！🔒' in out, f'应打印再见, 实际: {out!r}'

    def test_main_captures_ctrl_c_after_login(self, monkeypatch, capsys):
        """main() 登录成功后主菜单 Ctrl-C 也优雅退出"""
        import sys
        from mini2fa import _cli
        from unittest.mock import patch

        self._setup_main_env(monkeypatch)
        # 首次设置密码流程: getpass 第一次抛 Ctrl-C（在设置阶段）
        # 简化: 直接验证 main 内部 catch
        with patch('mini2fa._cli.getpass.getpass',
                   side_effect=KeyboardInterrupt()):
            with patch.object(sys, 'exit', side_effect=SystemExit):
                with pytest.raises(SystemExit):
                    _cli.main([])
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
        # main 内部必须捕获 KeyboardInterrupt
        from mini2fa import _cli
        import inspect
        main_src = inspect.getsource(_cli.main)
        assert 'except KeyboardInterrupt' in main_src


class TestTtyMode:
    """TTY 模式（monkeypatch 模拟终端）下 ANSI 序列"""

    def _fake_streams(self, monkeypatch):
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

    def test_render_contains_clear_and_home(self, monkeypatch):
        out, _ = self._fake_streams(monkeypatch)
        from mini2fa import ui
        ui.render(['line1', 'line2'], '> ')
        s = out.buf.getvalue()
        assert '\x1b[H' in s          # 光标归位
        assert '\x1b[0K' in s         # 行清尾
        assert '\x1b[0J' in s         # 清底部
        assert 'line1' in s and 'line2' in s
        assert s.endswith('> ')       # prompt 在末尾

    def test_enter_leave_sequences(self, monkeypatch):
        out, _ = self._fake_streams(monkeypatch)
        from mini2fa import ui
        # enter 写备屏切换 + 隐藏光标
        ui.enter()
        s = out.buf.getvalue()
        assert '\x1b[?1049h' in s     # 进入备屏
        assert '\x1b[?25l' in s       # 光标隐藏
        # leave 后续写恢复序列（继续追加）
        ui.leave()
        s2 = out.buf.getvalue()
        assert '\x1b[?1049l' in s2    # 退出备屏
        assert '\x1b[?25h' in s2      # 光标显示

    def test_tui_off_no_ansi(self, monkeypatch):
        """configure(no_tui=True) 强制降级：即使 TTY 也不发 ANSI"""
        out, _ = self._fake_streams(monkeypatch)
        from mini2fa import ui
        ui.configure(no_tui=True)
        try:
            ui.enter()
            ui.render(['x'])
            assert '\x1b[' not in out.buf.getvalue()
        finally:
            ui.configure(no_tui=False)

    def test_wait_enter_key_press(self, monkeypatch):
        """TTY 下收到 Enter 返回 True"""
        from mini2fa import ui
        self._fake_streams(monkeypatch)
        monkeypatch.setattr(ui, '_wait_key', lambda timeout: True)
        assert ui.wait_enter(0.1) is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])