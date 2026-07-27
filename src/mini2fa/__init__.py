"""Mini2FA - 安全的本地 TOTP 双因素认证管理工具"""

from .totp import generate_totp, verify_totp, get_remaining_seconds
from .crypto import CryptoManager
from .storage import StorageManager
from .scanner import scan_qrcode, parse_otp_uri
from .models import Account, OTPAccountInfo

__version__ = "0.1.0"