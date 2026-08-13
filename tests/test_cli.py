"""
CLI 层单元测试（分组展示逻辑）
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from mini2fa.models import Account


def _make_account(issuer, category, aid):
    """构造 Account 对象"""
    return Account(
        id=aid,
        issuer=issuer,
        account=f"user@{issuer.lower()}.com",
        secret_encrypted='enc',
        algorithm='SHA1',
        digits=6,
        period=30,
        category=category,
        notes='',
        created_at='2026-01-01',
        updated_at='2026-01-01'
    )


class TestListAccountsGrouped:
    """测试 list_accounts_grouped 分组展示"""

    def test_default_category_first(self, capsys):
        """测试 default 分类排最前"""
        from mini2fa._cli import list_accounts_grouped

        accounts = [
            _make_account('GitHub', '工作', 2),
            _make_account('Google', 'default', 1),
            _make_account('Amazon', '个人', 3),
        ]

        ordered = list_accounts_grouped(accounts)

        # 编号对应：default 组最前
        issuers = [a.issuer for a in ordered]
        assert issuers == ['Google', 'Amazon', 'GitHub']

        out = capsys.readouterr().out
        # default 组先显示
        assert out.index('[default]') < out.index('[个人]')
        assert out.index('[个人]') < out.index('[工作]')

    def test_returns_same_accounts(self):
        """测试返回列表与原列表是同一批账号（无丢失/重复）"""
        from mini2fa._cli import list_accounts_grouped

        accounts = [
            _make_account('GitHub', '工作', 2),
            _make_account('Google', 'default', 1),
        ]

        ordered = list_accounts_grouped(accounts)

        assert len(ordered) == 2
        assert set(a.id for a in ordered) == {1, 2}

    def test_single_category(self):
        """测试全 default 时无重复分组"""
        from mini2fa._cli import list_accounts_grouped

        accounts = [
            _make_account('Google', 'default', 1),
            _make_account('GitHub', 'default', 2),
        ]

        ordered = list_accounts_grouped(accounts)

        assert [a.issuer for a in ordered] == ['Google', 'GitHub']  # 组内保持输入顺序


class TestEditClearSemantics:
    """测试编辑账号的清空语义（输入 . 清空，回车保持不变）"""

    def _setup(self):
        """创建带分类/备注的账号，返回 storage"""
        from mini2fa.crypto import CryptoManager
        from mini2fa.storage import StorageManager

        tmpdir = tempfile.mkdtemp()
        key = os.path.join(tmpdir, 'key')
        crypto = CryptoManager(key)
        crypto.initialize('pwd')
        storage = StorageManager(os.path.join(tmpdir, 'db.db'), crypto)
        acc_id = storage.add_account(
            'Google', 'u@gmail.com', 'JBSWY3DPEHPK3PXP',
            category='工作', notes='旧备注'
        )
        return storage, acc_id, tmpdir

    def test_clear_category_and_notes(self):
        """输入 . 清空分类（回 default）和备注"""
        from unittest.mock import patch
        from mini2fa._cli import handle_edit_account

        storage, acc_id, tmpdir = self._setup()
        try:
            inputs = iter(['1', '.', '.'])
            with patch('builtins.input', side_effect=lambda prompt: next(inputs)):
                handle_edit_account(storage)

            acc = storage.get_account(acc_id)
            assert acc.category == 'default'
            assert acc.notes == ''
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_enter_keeps_values(self):
        """回车保持不变"""
        from unittest.mock import patch
        from mini2fa._cli import handle_edit_account

        storage, acc_id, tmpdir = self._setup()
        try:
            inputs = iter(['1', '', ''])
            with patch('builtins.input', side_effect=lambda prompt: next(inputs)):
                handle_edit_account(storage)

            acc = storage.get_account(acc_id)
            assert acc.category == '工作'
            assert acc.notes == '旧备注'
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_new_values_update(self):
        """输入新值更新"""
        from unittest.mock import patch
        from mini2fa._cli import handle_edit_account

        storage, acc_id, tmpdir = self._setup()
        try:
            inputs = iter(['1', '个人', '新备注'])
            with patch('builtins.input', side_effect=lambda prompt: next(inputs)):
                handle_edit_account(storage)

            acc = storage.get_account(acc_id)
            assert acc.category == '个人'
            assert acc.notes == '新备注'
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestChangePasswordCLI:
    """测试修改主密码 CLI 流程"""

    def _setup(self):
        """创建带旧密码的 crypto，返回 (crypto, key_path, tmpdir)"""
        from mini2fa.crypto import CryptoManager

        tmpdir = tempfile.mkdtemp()
        key = os.path.join(tmpdir, 'key')
        crypto = CryptoManager(key)
        crypto.initialize('old_pwd', '旧提示')
        return crypto, key, tmpdir

    def test_change_password_success_keeps_hint(self):
        """改密成功，回车保留原 hint"""
        from unittest.mock import patch
        from mini2fa._cli import handle_change_password

        crypto, key, tmpdir = self._setup()
        try:
            # getpass: 旧密码, 新密码, 确认新密码; input: hint(回车)
            inputs = iter(['old_pwd', 'New_pwd123', 'New_pwd123', ''])
            with patch('getpass.getpass', side_effect=lambda prompt: next(inputs)):
                with patch('builtins.input', side_effect=lambda prompt: next(inputs)):
                    handle_change_password(crypto)

            from mini2fa.crypto import CryptoManager
            reload = CryptoManager(key)
            assert reload.initialize('New_pwd123') is True
            assert reload.get_hint() == '旧提示'
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_change_password_wrong_old_rejected(self):
        """旧密码错误被拒绝"""
        from unittest.mock import patch
        from mini2fa._cli import handle_change_password

        crypto, key, tmpdir = self._setup()
        try:
            # getpass 3次都是错误旧密码
            inputs = iter(['wrong1', 'wrong2', 'wrong3'])
            with patch('getpass.getpass', side_effect=lambda prompt: next(inputs)):
                with patch('builtins.input', return_value=''):
                    handle_change_password(crypto)

            from mini2fa.crypto import CryptoManager
            reload = CryptoManager(key)
            assert reload.initialize('old_pwd') is True, '原密码应仍有效'
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestDisplayNotes:
    """测试详情框显示备注"""

    def test_display_with_notes(self):
        """测试有备注时详情框显示备注"""
        from mini2fa.crypto import CryptoManager
        from mini2fa.storage import StorageManager
        from mini2fa._cli import display_account_with_code
        import io
        import contextlib

        tmpdir = tempfile.mkdtemp()
        try:
            key = os.path.join(tmpdir, 'key')
            crypto = CryptoManager(key)
            crypto.initialize('pwd')
            storage = StorageManager(os.path.join(tmpdir, 'db.db'), crypto)
            acc_id = storage.add_account(
                'GitHub', 'me@g.com', 'JBSWY3DPEHPK3PXP', notes='公司主邮箱'
            )
            acc = storage.get_account(acc_id)

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                display_account_with_code(acc, 'JBSWY3DPEHPK3PXP', '123456')
            assert '公司主邮箱' in buf.getvalue()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_display_without_notes(self):
        """测试无备注时不显示备注行"""
        from mini2fa._cli import display_account_with_code
        import io
        import contextlib

        acc = _make_account('Google', 'default', 1)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            display_account_with_code(acc, 'JBSWY3DPEHPK3PXP', '123456')
        assert '备注' not in buf.getvalue()

    def test_display_long_notes_full(self):
        """测试超长备注完整显示（不截断，框自适应变宽）"""
        from mini2fa._cli import display_account_with_code
        import io
        import contextlib

        long_notes = '很' * 100  # 100 个汉字, 200 显示宽度
        acc = _make_account('GitHub', 'default', 1)
        acc.notes = long_notes

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            display_account_with_code(acc, 'JBSWY3DPEHPK3PXP', '123456')
        out = buf.getvalue()
        assert long_notes in out, '超长备注应完整显示，不截断'
        assert '...' not in out, '不应出现截断省略号'

    def test_display_long_issuer_full_and_aligned(self):
        """测试超长 issuer 完整显示且右边缘对齐"""
        from mini2fa._cli import display_account_with_code
        import io
        import contextlib

        acc = _make_account('A' * 60, 'default', 1)  # 60 字符超长 issuer
        acc.notes = ''

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            display_account_with_code(acc, 'JBSWY3DPEHPK3PXP', '123456')
        out = buf.getvalue()
        lines = out.strip().split('\n')

        # issuer 完整显示
        assert ('A' * 60) in out

        # 中间内容行右边缘对齐（以 │ 结尾，且显示宽度等宽）
        from wcwidth import wcswidth
        body_lines = [l for l in lines if l.startswith('│')]
        assert len(body_lines) > 0, '应有内容行'
        assert all(l.endswith('│') for l in body_lines), '内容行应以 │ 结尾'
        widths = {wcswidth(l) for l in body_lines}
        assert len(widths) == 1, f'内容行显示宽度应等宽, 实际: {widths}'


class TestAddAccountFlow:
    """测试添加账号流程（查重 → 填字段 → 摘要确认）"""

    def _setup(self):
        """创建 storage 和 mock 用 OTPAccountInfo"""
        from mini2fa.crypto import CryptoManager
        from mini2fa.storage import StorageManager
        from mini2fa.models import OTPAccountInfo

        tmpdir = tempfile.mkdtemp()
        key = os.path.join(tmpdir, 'key')
        crypto = CryptoManager(key)
        crypto.initialize('pwd')
        storage = StorageManager(os.path.join(tmpdir, 'db.db'), crypto)
        info = OTPAccountInfo('Google', 'u@gmail.com', 'MFRGGZDFMZTWQ2LK', 'SHA1', 6, 30, 'totp')
        return storage, info, tmpdir

    def test_duplicate_detected_before_fields(self):
        """测试重复账号在填字段前被检测"""
        from unittest.mock import patch
        from mini2fa._cli import handle_add_account

        storage, info, tmpdir = self._setup()
        # 预置重复账号
        storage.add_account('Google', 'u@gmail.com', 'JBSWY3DPEHPK3PXP')
        try:
            # 若流程错误进入填字段, next() 会 StopIteration 崩溃
            # 需要两个 input: 图片路径 + 按 Enter 返回主菜单
            inputs = iter(['fake.png', ''])
            with patch('mini2fa._cli.os.path.exists', return_value=True):
                with patch('mini2fa._cli.scan_qrcode', return_value=info):
                    with patch('builtins.input', side_effect=lambda prompt: next(inputs)):
                        handle_add_account(storage)
            # 未崩溃 = 查重拦截成功
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_add_new_account_with_summary(self):
        """测试新账号填字段后入库"""
        from unittest.mock import patch
        from mini2fa._cli import handle_add_account

        storage, info, tmpdir = self._setup()
        try:
            inputs = iter(['fake.png', '个人', '备用', 'y'])
            with patch('mini2fa._cli.os.path.exists', return_value=True):
                with patch('mini2fa._cli.scan_qrcode', return_value=info):
                    with patch('builtins.input', side_effect=lambda prompt: next(inputs)):
                        handle_add_account(storage)
            acc = storage.find_by_identity('Google', 'u@gmail.com')
            assert acc is not None
            assert acc.category == '个人'
            assert acc.notes == '备用'
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_cancel_confirmation_does_not_add(self):
        """测试确认时取消不入库"""
        from unittest.mock import patch
        from mini2fa._cli import handle_add_account

        storage, info, tmpdir = self._setup()
        try:
            inputs = iter(['fake.png', '', '', 'n'])
            with patch('mini2fa._cli.os.path.exists', return_value=True):
                with patch('mini2fa._cli.scan_qrcode', return_value=info):
                    with patch('builtins.input', side_effect=lambda prompt: next(inputs)):
                        handle_add_account(storage)
            assert storage.find_by_identity('Google', 'u@gmail.com') is None
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

class TestCancelableHandlers:
    """测试 Ctrl-C 中断操作性作（放弃当前操作，返回主菜单）"""

    def test_handle_add_account_ctrl_c_cancels(self):
        """添加账号过程中 Ctrl-C 被捕获，不冒泡"""
        from unittest.mock import patch
        from mini2fa._cli import handle_add_account
        from mini2fa.crypto import CryptoManager
        from mini2fa.storage import StorageManager
        from mini2fa.models import OTPAccountInfo

        tmpdir = tempfile.mkdtemp()
        try:
            key = os.path.join(tmpdir, 'key')
            crypto = CryptoManager(key)
            crypto.initialize('Abc123')
            storage = StorageManager(os.path.join(tmpdir, 'db.db'), crypto)
            info = OTPAccountInfo('GitHub', 'g@g.com', 'JBSWY3DPEHPK3PXP', 'SHA1', 6, 30, 'totp')

            def kb(*a, **k):
                raise KeyboardInterrupt()

            # 输入图片路径时 Ctrl-C
            with patch('mini2fa._cli.os.path.exists', return_value=True):
                with patch('mini2fa._cli.scan_qrcode', return_value=info):
                    with patch('builtins.input', side_effect=kb):
                        # 不应抛出 KeyboardInterrupt（被 _cancelable 捕获）
                        handle_add_account(storage)
            # 未入库
            assert storage.find_by_identity('GitHub', 'g@g.com') is None
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_handle_view_code_ctrl_c_cancels(self):
        """查看验证码过程中 Ctrl-C 被捕获，不冒泡"""
        from unittest.mock import patch
        from mini2fa._cli import handle_view_code
        from mini2fa.crypto import CryptoManager
        from mini2fa.storage import StorageManager

        tmpdir = tempfile.mkdtemp()
        try:
            key = os.path.join(tmpdir, 'key')
            crypto = CryptoManager(key)
            crypto.initialize('Abc123')
            storage = StorageManager(os.path.join(tmpdir, 'db.db'), crypto)
            storage.add_account('Google', 'u@gmail.com', 'JBSWY3DPEHPK3PXP')

            def kb(*a, **k):
                raise KeyboardInterrupt()

            with patch('builtins.input', side_effect=kb):
                # 不应抛出 KeyboardInterrupt
                handle_view_code(storage)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
