"""工具"""

from __future__ import annotations

from asyncio import sleep as async_sleep
from pathlib import Path
from re import compile as re_compile, search as re_search
from time import perf_counter
from typing import TYPE_CHECKING

from scraper_utils.utils.emag_util import parse_pnk as _parse_pnk
from scraper_utils.utils.file_util import read_file

from .exceptions import ParsePNKError


if TYPE_CHECKING:
    from typing import Pattern, Optional

    from playwright.async_api import BrowserContext, Page, Locator

    type StrOrPath = str | Path
    type BrowserContextOrPage = BrowserContext | Page


cwd = Path.cwd()
CART_PAGE_URL = 'https://www.emag.ro/cart/products'


_track_url_patterns: tuple[Pattern[str], ...] = (
    re_compile(r'.*?emag\.ro/logger.json.*'),
    re_compile(r'.*?emag\.ro/recommendations/by-zone-position.*'),
    re_compile(r'.*?emag\.ro/g/collect.*'),
    re_compile(r'.*?emag\.ro/favorites.*'),
    re_compile(r'.*?googlesyndication\.com.*'),
    re_compile(r'.*?google-analytics\.com.*'),
    re_compile(r'.*?facebook\.com.*'),
    re_compile(r'.*?tiktok\.com.*'),
    re_compile(r'.*?snapchat\.com.*'),
    re_compile(r'.*?adtrafficquality\.google.*'),
    re_compile(r'.*?doubleclick\.net.*'),
    re_compile(r'.*?creativecdn\.com.*'),
    re_compile(r'.*?ingest\.de\.sentry\.io.*'),
    # NOTICE 还有别的埋点吗？
)


async def block_track(context_page: BrowserContextOrPage) -> None:
    """屏蔽 eMAG 的页面追踪埋点"""
    for p in _track_url_patterns:
        await context_page.route(p, lambda req: req.abort())


_hide_cookie_banner_js: Optional[str] = None


async def hide_cookie_banner(context_page: BrowserContextOrPage) -> None:
    """隐藏 eMAG 的 Cookie 提醒"""
    global _hide_cookie_banner_js
    if _hide_cookie_banner_js is None:
        _hide_cookie_banner_js = await read_file(
            file=cwd / 'js/hide-cookie-banner.js', mode='str', async_mode=True
        )
    await context_page.add_init_script(script=_hide_cookie_banner_js)


async def wait_for_element(locator: Locator, interval: int = 1_000, timeout: int = 30_000) -> bool:
    """以 `interval` 的周期检查有无特定元素"""
    start_time = perf_counter()
    while perf_counter() - start_time > timeout / 1000:
        if await locator.count() > 0:
            return True
        await async_sleep(interval / 1000)
    return False


def parse_pnk_from_url(v) -> str:
    """从链接中提取 pnk"""
    if v is None:
        raise ParsePNKError('')
    r = _parse_pnk(v)
    if r is None:
        raise ParsePNKError(v)
    return r
