"""购物车页"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..models import ProductCardData, ProductCartDataList

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext, Page, Locator


async def goto_cart_page(context: BrowserContext) -> Page:
    """访问购物车页"""


async def parse_max_qty(page: Page, products: ProductCartDataList) -> ProductCartDataList:
    """解析产品的最大可加购数"""


async def clear_cart(page: Page) -> None:
    """清空购物车"""
