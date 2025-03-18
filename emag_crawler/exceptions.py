"""异常"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class CaptchaError(Exception):
    """遇到验证码时的异常"""

    def __init__(self, url: str, message: str, *args: object) -> None:
        super().__init__(*args)
        self.url = url
        self.message = message

    def __str__(self) -> str:
        return f'{self.__class__.__name__}: "{self.url}" {self.message}'
