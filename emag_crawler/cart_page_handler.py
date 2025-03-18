"""处理购物车页"""

from __future__ import annotations

from typing import TYPE_CHECKING

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
    # TODO
