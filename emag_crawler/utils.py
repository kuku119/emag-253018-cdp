"""工具"""

from __future__ import annotations

from asyncio import sleep as async_sleep
from pathlib import Path
from re import compile
from sys import stderr
from time import perf_counter
from typing import TYPE_CHECKING

from loguru import logger
from scraper_utils.utils.emag_util import parse_pnk as _parse_pnk
from scraper_utils.utils.file_util import read_file

from .exceptions import ParsePNKError


if TYPE_CHECKING:
    from asyncio import Event
    from typing import Pattern, Optional

    from playwright.async_api import BrowserContext, Page, Response, Locator

    type StrOrPath = str | Path
    type BrowserContextOrPage = BrowserContext | Page


cwd = Path.cwd()


logger.remove()
logger.add(
    stderr,
    format=(
        '[<green>{time:HH:mm:ss}</green>] [<level>{level:.3}</level>] '
        '[<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan>] >>> '
        '<level>{message}</level>'
    ),
    filter=lambda record: len(record['extra']) == 0,
)


async def check_response_captcha(response: Response, allow_flag: Event) -> None:
    """通过检查响应状态码判断有无验证码，当出现验证码时，对应请求的响应状态码为 511"""
    page = response.frame.page
    url = response.url
    status = response.status
    # 当检测到验证码时清空 event，不允许再继续爬取
    if status == 511:
        logger.error(f'在 "{page.url}" 页面的 "{url}" 请求检测到验证码')
        allow_flag.clear()
    else:
        allow_flag.set()


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


def build_category_url(category: str, page: int = 1) -> str:
    """构造类目页链接"""
    if page <= 0:
        raise ValueError(f'页码必须为正整数，而不是 {page}')
    if page == 1:
        return f'https://www.emag.ro/{category}/c'
    return f'https://www.emag.ro/{category}/p{page}/c'


_parse_category_page_pattern = compile(r'/p{(\d+)}/c')


def parse_category_page(url: str) -> Optional[int]:
    """从类目链接解析当前页码"""
    m = _parse_category_page_pattern.search(url)
    if m is not None:
        try:
            return int(m.group(1))
        except ValueError:
            pass


def parse_pnk_from_url(v) -> str:
    """从链接中提取 pnk"""
    if v is None:
        raise ParsePNKError('')
    r = _parse_pnk(v)
    if r is None:
        raise ParsePNKError(v)
    return r
