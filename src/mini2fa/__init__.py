"""Mini2FA - 安全的本地 TOTP 双因素认证管理工具"""

from .totp import generate_totp, verify_totp, get_remaining_seconds
from .crypto import CryptoManager
from .storage import StorageManager
from .scanner import scan_qrcode, scan_qrcode_from_raw_data, parse_otp_uri, preprocess_image, UnsupportedOTPTypeError
from .models import Account, OTPAccountInfo

__version__ = "0.2.0"