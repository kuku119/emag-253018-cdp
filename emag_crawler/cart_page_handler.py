"""处理购物车页"""

from __future__ import annotations

from typing import TYPE_CHECKING

from scraper_utils.constants.time_constant import MS1000
from scraper_utils.exceptions.browser_exception import PlaywrightError

from .utils import cwd, logger, block_track, hide_cookie_banner, wait_for_element

if TYPE_CHECKING:
    from typing import Literal

    from playwright.async_api import BrowserContext, Page


CART_PAGE_URL = 'https://www.emag.ro/cart/products'


async def goto_cart_page(
    context: BrowserContext,
    wait_until: Literal['commit', 'domcontentloaded', 'load', 'networkidle'] = 'load',
) -> Page:
    """打开购物车页，检查购物车内有无产品"""
    page = await context.new_page()
    # 隐藏 cookie 提示
    await hide_cookie_banner(page, js_path=cwd / 'js/hide-cookie-banner.js')
    # 屏蔽 eMAG 埋点
    await block_track(page)

    logger.info('正在打开购物车页')
    await page.goto(CART_PAGE_URL, wait_until=wait_until)

    # 检查购物车内有无产品（有无可见的 Sterge 按钮）
    if not await wait_for_element(
        page.locator('css=button.remove-product').filter(visible=True),
    ):
        logger.warning('购物车为空')
    else:
        logger.info('成功访问购物车页')

    return page


async def parse_max_qty(page: Page):
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
    """购物车是否为空"""
    # 有无可见的 Sterge 按钮
    visible_sterge_buttons = page.locator('css=button.remove-product').filter(visible=True)
    return await visible_sterge_buttons.count() == 0
