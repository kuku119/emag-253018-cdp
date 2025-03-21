"""工具"""

from __future__ import annotations

from asyncio.tasks import sleep as async_sleep
from contextlib import asynccontextmanager
from pathlib import Path
from re import compile
from sys import stderr
from time import perf_counter
from typing import TYPE_CHECKING

from loguru import logger
from playwright.async_api import async_playwright
from scraper_utils.utils.file_util import read_file_async

from .exceptions import CaptchaError

if TYPE_CHECKING:
    from typing import Optional, AsyncGenerator, Pattern

    from playwright.async_api import Browser, BrowserContext, Page, Response, Locator

    type StrOrPath = str | Path
    type BrowserContextOrPage = BrowserContext | Page


__all__ = [
    'cwd',
    'logger',
    'check_response_captcha',
    'block_track',
    'hide_cookie_banner',
    'wait_for_element',
]


cwd = Path.cwd()


logger.remove()
logger.add(
    stderr,
    format=(
        '[<green>{time:HH:mm:ss}</green>] [<level>{level:.3}</level>] '
        '[<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan>] >>> '
        '<level>{message}</level>'
    ),
)

# _captcha_url_patterns: tuple[Pattern[str], ...] = (
#     compile(r'.*?emag\.ro/cart/remove.*'),
#     compile(r'.*?emag\.ro/newaddtocart.*'),
#     # TODO 产品详情页的还没做
#     # NOTICE 还有别的请求链接吗？
# )


async def check_response_captcha(response: Response) -> None:
    """通过检查响应状态码判断有无验证码，当出现验证码时，对应请求的响应状态码为 511"""
    # TODO 是要单纯检测到验证码然后提醒，还是检测到验证码后模拟点击？
    # FIXME 如何实时捕获 CaptchaError 并处理？
    url = response.url
    status = response.status
    # NOTICE 好像直接检测有无 511 的状态码就行了
    # if status == 511 and any(p.search(url) is not None for p in _captcha_url_patterns):
    if status == 511:
        raise CaptchaError(url=url, message=f'在 "{url}" 检测到验证码')


_track_url_patterns: tuple[Pattern[str], ...] = (
    compile(r'.*?emag\.ro/logger.json.*'),
    compile(r'.*?emag\.ro/recommendations/by-zone-position.*'),
    compile(r'.*?emag\.ro/g/collect.*'),
    compile(r'.*?googlesyndication\.com.*'),
    compile(r'.*?google-analytics\.com.*'),
    compile(r'.*?facebook\.com.*'),
    compile(r'.*?tiktok\.com.*'),
    compile(r'.*?snapchat\.com.*'),
    compile(r'.*?adtrafficquality\.google.*'),
    compile(r'.*?doubleclick\.net.*'),
    compile(r'.*?creativecdn\.com.*'),
    # NOTICE 还有别的埋点吗？
)


async def block_track(context_page: BrowserContextOrPage) -> None:
    """屏蔽 eMAG 的页面追踪埋点"""
    for p in _track_url_patterns:
        await context_page.route(p, lambda req: req.abort())


_hide_cookie_banner_js: Optional[str] = None


async def hide_cookie_banner(context_page: BrowserContextOrPage, js_path: StrOrPath) -> None:
    """隐藏 eMAG 的 Cookie 提醒"""
    global _hide_cookie_banner_js
    if _hide_cookie_banner_js is None:
        _hide_cookie_banner_js = await read_file_async(file=js_path, mode='str', encoding='utf-8')
    await context_page.add_init_script(script=_hide_cookie_banner_js)


async def wait_for_element(locator: Locator, interval: int = 1_000, timeout: int = 30_000) -> bool:
    """以 `interval` 的周期检查有无特定元素"""
    start_time = perf_counter()
    while perf_counter() - start_time > timeout / 1000:
        if await locator.count() > 0:
            return True
        await async_sleep(interval / 1000)
    return False


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
