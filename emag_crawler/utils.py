"""工具"""

from __future__ import annotations

from contextlib import asynccontextmanager
from re import compile
from sys import stderr
from typing import TYPE_CHECKING

from loguru import logger
from playwright.async_api import async_playwright
from scraper_utils.utils.file_util import read_file_async

from .exceptions import CaptchaError

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Optional, AsyncGenerator, Pattern

    from playwright.async_api import Browser, BrowserContext, Page, Response

    type StrOrPath = str | Path


__all__ = [
    'logger',
    'check_response_captcha',
    'block_track',
    'hide_cookie_banner',
]


logger.remove()
logger.add(
    stderr,
    format=(
        '[<green>{time:HH:mm:ss}</green>] [<level>{level:.3}</level>] '
        '[<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan>] >>> '
        '<level>{message}</level>'
    ),
)

_captcha_url_patterns: tuple[Pattern[str], ...] = (
    compile(r'.*?emag\.ro/cart/remove.*'),
    compile(r'.*?emag\.ro/newaddtocart.*'),
    # TODO 产品详情页的还没做
    # NOTICE 还有别的请求链接吗？
)


async def check_response_captcha(response: Response) -> None:
    """通过检查响应状态码判断有无验证码，当出现验证码时，对应请求的响应状态码为 511"""
    url = response.url
    status = response.status
    # if status == 511 and any(p.search(url) is not None for p in _captcha_url_patterns):
    if status == 511:  # NOTICE 好像直接检测有无 511 的状态码就行了
        raise CaptchaError(url=url, message=f'在 "{url}" 检测到验证码')


_track_url_patterns: tuple[Pattern[str], ...] = (
    compile(r'.*?emag\.ro/logger.json.*'),
    compile(r'.*?emag\.ro/recommendations/by-zone-position.*'),
    compile(r'.*?emag\.ro/g/collect.*'),
    # NOTICE 还有别的埋点吗？
)


async def block_track(context_page: BrowserContext | Page) -> None:
    """屏蔽 eMAG 的页面追踪埋点"""
    for p in _track_url_patterns:
        await context_page.route(p, lambda req: req.abort())


_hide_cookie_banner_js: Optional[str] = None


async def hide_cookie_banner(page: Page, js_path: StrOrPath) -> None:
    """隐藏 eMAG 的 Cookie 提醒"""
    global _hide_cookie_banner_js
    if _hide_cookie_banner_js is None:
        _hide_cookie_banner_js = await read_file_async(file=js_path, mode='str', encoding='utf-8')
    await page.add_init_script(script=_hide_cookie_banner_js)


# WARNING 不好用
@asynccontextmanager
async def connect_brightdata_browser(
    ws_url: str,
    *,
    headers: Optional[dict[str, str]] = None,
    timeout: Optional[int] = None,
    slow_mo: Optional[int] = None,
) -> AsyncGenerator[Browser]:
    """连接到 BrightData 提供的 ScrapingBrowser"""
    async with async_playwright() as pwr:
        browser = None
        try:
            browser = await pwr.chromium.connect_over_cdp(
                endpoint_url=ws_url,
                headers=headers,
                timeout=timeout,
                slow_mo=slow_mo,
            )
            yield browser
        finally:
            if browser is not None and browser.is_connected():
                await browser.close()
