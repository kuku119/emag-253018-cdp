"""工具"""

from __future__ import annotations

from contextlib import asynccontextmanager
from sys import stderr
from typing import TYPE_CHECKING

from loguru import logger
from playwright.async_api import async_playwright
from scraper_utils.utils.file_util import read_file_async

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Optional, AsyncGenerator

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


async def check_response_captcha(response: Response) -> None:
    """通过检查响应状态码判断有无验证码"""
    # TODO
    # NOTICE 当出现验证码时，对应请求的响应状态码为 511
    """
    NOTICE 需要检测的 endpoint
    购物车页的 Sterge 按钮 https://www.emag.ro/cart/remove
    产品类目页的加购按钮 https://www.emag.ro/newaddtocart
    TODO 还有产品详情页的
    """


async def block_track(context_or_page: BrowserContext | Page) -> None:
    """屏蔽 eMAG 的页面追踪埋点"""
    # TODO


_hide_cookie_banner_js: Optional[str] = None


async def hide_cookie_banner(page: Page, js_path: StrOrPath) -> None:
    """隐藏 Cookie 提醒"""
    global _hide_cookie_banner_js
    if _hide_cookie_banner_js is None:
        _hide_cookie_banner_js = await read_file_async(file=js_path, mode='str', encoding='utf-8')
    await page.add_init_script(script=_hide_cookie_banner_js)


# WARNING 不好用
@asynccontextmanager
async def connect_browser(
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
