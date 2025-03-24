"""处理购物车页"""

from __future__ import annotations

from asyncio import gather
from re import compile
from typing import TYPE_CHECKING

from scraper_utils.constants.time_constant import MS1000
from scraper_utils.exceptions.browser_exception import PlaywrightError

from ..exceptions import CaptchaError
from ..models import ProductCardItem
from ..utils import CART_PAGE_URL, block_track

if TYPE_CHECKING:
    from typing import Literal

    from loguru import Logger
    from playwright.async_api import BrowserContext, Page, Locator, Response


async def open_url(
    context: BrowserContext,
    logger: Logger,
    wait_until: Literal['commit', 'domcontentloaded', 'load', 'networkidle'] = 'load',
) -> Page:
    """打开购车页"""
    logger.info('尝试访问购物车页')

    page = await context.new_page()
    await block_track(page)

    response = await page.goto(CART_PAGE_URL, wait_until=wait_until)
    if response is None or response.status == 511:  # 有效
        raise CaptchaError(CART_PAGE_URL, '尝试访问购物车页时遇到验证')

    return page


# BUG 不能完全清空购物车
# 直接点击所有 Sterge 的方式
async def clear_cart(page: Page, logger: Logger) -> None:
    """清空购物车"""
    logger.info('清空购物车')

    # 全部可点击的 Sterge 按钮
    sterge_buttons = page.locator('css=button.remove-product[data-line]').filter(visible=True)

    for i in range(await sterge_buttons.count(), 0, -1):
        try:
            await sterge_buttons.nth(i).click(timeout=MS1000)
        except PlaywrightError as pe:
            logger.warning(f'尝试点击 Sterge#{i} 时出错\n{pe}')
            continue


# 点击 Sterge 按钮，然后等待响应判断是否 Sterge 成功、有无触发验证
# BUG
# async def clear_cart(page: Page, logger: Logger) -> None:
#     """清空购物车"""
#     logger.info('清空购物车')

#     # 全部可点击的 Sterge 按钮
#     sterge_buttons = page.locator('css=button.remove-product[data-line]').filter(visible=True)

#     click_sterge_tasks = [click_sterge(page, b, logger) for b in await sterge_buttons.all()]
#     sterge_results = await gather(*click_sterge_tasks)
#     if False in sterge_results:
#         raise CaptchaError(CART_PAGE_URL, '尝试清空购物车时遇到验证')


# async def click_sterge(page: Page, button: Locator, logger: Logger) -> bool:
#     """点击单个 Sterge 按钮，返回是否 Sterge 成功"""

#     # BUG Sterge 请求的响应是成功的，但还是会重复点击加购按钮

#     data_line: str = await button.get_attribute('data-line', timeout=MS1000)  # type: ignore

#     while True:
#         # async with page.expect_response(compile(r'.*?emag\.ro/cart/remove.*')) as response_event:
#         async with page.expect_response(lambda r: _sterge_response_filter(r, data_line)) as response_event:
#             try:
#                 await button.click(timeout=MS1000)
#             except PlaywrightError as pe:
#                 logger.warning(f'尝试点击 Sterge 时出错 data-line={data_line}\n{pe}')
#                 continue
#         response = await response_event.value
#         response.request.post_data_json
#         if response.ok:
#             logger.debug(f'Sterge 成功 data-line={data_line}')
#             return True
#         if response.status == 511:  # TODO 待测试
#             return False


# def _sterge_response_filter(response: Response, data_line: str) -> bool:
#     """筛选 Sterge 的请求"""
#     if compile(r'.*?emag\.ro/cart/remove.*').search(response.url) is None:
#         return False

#     request = response.request

#     if request.method == 'GET' or request.post_data is None:
#         return False

#     return data_line in request.post_data


async def parse_max_qty(page: Page, product: ProductCardItem, logger: Logger) -> None:
    """根据 pnk 解析产品的最大可加购数，通过直接修改 product 的形式保存解析结果"""

    # TODO 捆绑产品（bundle-item）的还没做

    pnk = product.pnk
    pnk_a = page.locator(f'xpath=//a[contains(@href, "pd/{pnk}")]')

    # 在购物车内用 pnk 找不到该产品，就直接返回
    if await pnk_a.count() == 0:
        logger.error(f'购物车中找不到产品 "{pnk}"')
        return

    # 可能会找到多个该产品的 input[@max] 标签，取第一个有效的作为最大可加购数
    qty_inputs = pnk_a.locator(
        'xpath=/ancestor::div[starts-with(@class, "cart-widget cart-line")]'
        '//div[@data-phino="Qty"]/input[@max]'
    )
    input_count = await qty_inputs.count()
    for i in range(input_count):
        logger.debug(f'尝试解析 "{pnk}" 的最大可加购数 #{i+1}/{input_count}')
        max_qty_text = await qty_inputs.nth(i).get_attribute('max', timeout=MS1000)
        if max_qty_text is None:
            logger.warning(f'"{pnk}" 的最大可加购数 #{i+1}，@max 为空')
            continue

        try:
            max_qty = int(max_qty_text)
        except ValueError:
            logger.error(f'无法将 "{pnk}" 的 @max="{max_qty_text}" 解析成整数')
            continue
        else:
            product.max_qty = max_qty
            break


# async def handle_cart(
#     context: BrowserContext, products: list[ProductCardItem], logger: Logger, need_clear_cart: bool
# ) -> list[ProductCardItem]:
#     """
#     1. 打开购物车页
#     2. 按照产品的 pnk 解析最大可加购数
#     3. 根据 `need_clear_cart` 清空购物车
#     """

#     page = await open_url(context, logger, 'networkidle')
#     result = [await parse_max_qty(page, p, logger) for p in products]

#     try:
#         if need_clear_cart:
#             await clear_cart(page, logger)
#     finally:  # BUG 异常会被吞掉
#         return result
