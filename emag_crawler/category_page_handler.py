"""处理产品类目页"""

from __future__ import annotations


from typing import TYPE_CHECKING

from .utils import logger

if TYPE_CHECKING:
    from asyncio.locks import Lock

    from playwright.async_api import BrowserContext, Page, Locator
    from scraper_utils.constants.time_constant import MS1000
    from scraper_utils.exceptions.browser_exception import PlaywrightError


async def handle_cart_dialog(page: Page, lock: Lock, interval: int = MS1000) -> None:
    """
    处理类目页面点击加购按钮后可能出现的弹窗

    当页面还未关闭时，每隔 `interval` 毫秒尝试点击一次加购弹窗的关闭按钮

    """
    logger.info(f'启动处理加购弹窗任务 "{page.url}"')
    while page.is_closed() is False:
        dialog_close_button = page.locator('xpath=//button[@class="close gtm_6046yfqs"]')
        async with lock:
            try:
                await dialog_close_button.click(timeout=interval)
            except PlaywrightError:
                pass
    logger.info(f'检测到页面关闭，处理加购弹窗任务即将关闭')


async def parse_first_page(context: BrowserContext, url: str, category: str, lock: Lock):
    """解析类目页的第 1 页"""
    # TODO


async def parse_other_page(context: BrowserContext, url: str, category: str, lock: Lock):
    """解析类目页的 2-5 页"""
    # TODO


async def add_to_cart(add_to_cart_button: Locator, lock: Lock):
    """加购一个产品"""
    # TODO
