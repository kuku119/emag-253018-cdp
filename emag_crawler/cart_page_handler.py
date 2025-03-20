"""处理购物车页"""

from __future__ import annotations

from typing import TYPE_CHECKING

from scraper_utils.constants.time_constant import MS1000
from scraper_utils.exceptions.browser_exception import PlaywrightError
from scraper_utils.utils.browser_util import wait_for_selector

from .utils import logger

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext, Page


__all__ = [
    'CART_PAGE_URL',
]


CART_PAGE_URL = 'https://www.emag.ro/cart/products'


async def goto_cart_page(context: BrowserContext) -> Page:
    """打开购物车页"""
    page = await context.new_page()
    await page.goto(CART_PAGE_URL)
    return page


async def parse_qty(page: Page):
    """解析购物车内产品的最大可加购数"""
    # TODO


async def clear_cart(page: Page) -> None:
    """清空购物车"""
    logger.info('开始清空购物车')

    # TODO 所有的 Sterge 按钮都点击一遍后，是否需要检测购物车是否已经清空？

    sterge_buttons = page.locator('css=button.remove-product').filter(visible=True)
    for i in range(await sterge_buttons.count(), 0, -1):
        try:
            await sterge_buttons.nth(i).click(timeout=MS1000)
        except PlaywrightError as pe:
            logger.warning(f'尝试点击第 {i} 个 Sterge 按钮时出错\n{pe}')
        else:
            logger.debug(f'Sterge #{i} 成功')

    logger.info('购物车已清空')


async def is_empty(page: Page) -> bool:
    """
    检测购物车是否为空

    通过检测有无可见的 Sterge 按钮来判断购物车是否为空
    """
    visible_sterge_buttons = page.locator('css=button.remove-product').filter(visible=True)
    return await visible_sterge_buttons.count() == 0
