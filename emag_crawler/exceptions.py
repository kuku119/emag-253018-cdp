"""异常"""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import unquote

if TYPE_CHECKING:
    pass


__all__ = [
    'CaptchaError',
    'ParsePNKError',
]


class CaptchaError(Exception):
    """遇到验证码时的异常"""

    def __init__(self, url: str, message: str, *args: object):
        super().__init__(*args)
        self.url = unquote(url)
        self.message = message

    def __str__(self):
        return self.message


class ParsePNKError(Exception):
    """解析 pnk 失败时的异常"""

    def __init__(self, origin_str: str, *args: object):
        super().__init__(*args)
        self.origin_str = origin_str

    def __str__(self):
        return self.origin_str


class NoProductCardError(Exception):
    """在类目页找不到产品卡片时的异常"""

    def __init__(self, url: str, *args: object) -> None:
        super().__init__(*args)
        self.url = unquote(url)

    def __str__(self):
        return self.url


class CartEmptyError(Exception):
    """购物车页无产品时的异常"""
