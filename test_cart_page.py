"""测试购物车页的操作"""

from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING

from playwright.async_api import async_playwright
from scraper_utils.exceptions.browser_exception import PlaywrightError
from scraper_utils.utils.browser_util import abort_resources, ResourceType, MS1000

from emag_crawler.handlers.category_page import open_url as open_category_page, handle_cart_dialog
from emag_crawler.handlers.cart_page import open_url as open_cart_page
from emag_crawler.logger import logger as _logger
from emag_crawler.utils import block_track

if TYPE_CHECKING:
    from typing import Optional

    from loguru import Logger
    from playwright.async_api import Page


# https://www.emag.ro/acuarele-pensule-si-blocuri-de-desen/brand/daco/c

# TODO 手动处理验证码的话要怎么做？


########## 每次点击最后一个产品卡片的 Sterge 按钮，当卡片内有 preloader 时等待 ##########
async def clear_cart(page: Page, logger: Logger) -> None:
    """清空购物车"""

    logger.info('开始清空购物车')

    captcha_flag = False

    # 产品卡片
    product_cart_divs = page.locator('css=div.cart-widget[data-id]')

    while await product_cart_divs.count() > 0:
        logger.info('准备 Sterge 一个产品')
        # 遇到验证
        if captcha_flag:
            logger.critical('遇到验证')
            break

        # 页面已被关闭
        if page.is_closed():
            logger.info('页面关闭')
            break

        # 等待 preloader 消失
        while await product_cart_divs.locator('css=div.preloader').count() > 0:
            await asyncio.sleep(0.1)

        # 点击 Sterge 按钮，然后等待 cart/remove 响应
        try:
            async with page.expect_response(
                re.compile(r'emag\.ro/cart/remove'), timeout=30 * MS1000
            ) as response_event:
                logger.debug('尝试点击 Sterge')
                try:
                    await product_cart_divs.last.locator('css=button.btn-remove-product').filter(
                        visible=True
                    ).click(timeout=MS1000)
                except PlaywrightError as pe:
                    logger.error(f'点击 Sterge 时出错\n{pe}')
                    # 取消等待 cart/remove 响应的 response_event
                    response_event._cancel()

        except PlaywrightError as pe:
            logger.error(f'等待 cart/remove 的响应时出错\n{pe}')
        except asyncio.CancelledError as ce:
            pass

        else:
            response = await response_event.value
            if response.ok:
                logger.success('成功 Sterge 一个产品')
            if response.status == 511:
                captcha_flag = True

    logger.info('结束清空购物车')


async def wait_page_close(page: Page):
    while not page.is_closed():
        await asyncio.sleep(1)


async def test_add_cart_parse_qty_clear_cart():
    """测试加购产品、解析最大可加购数、清空购物车"""
    category = 'acuarele-pensule-si-blocuri-de-desen'
    logger = _logger.bind(category=category)

    async with async_playwright() as pwr:
        browser = await pwr.chromium.connect_over_cdp('http://localhost:9222', timeout=MS1000)
        context = browser.contexts[0]
        await abort_resources(
            context,
            (ResourceType.IMAGE, ResourceType.MEDIA, ResourceType.FONT),
        )

        # 加购产品
        category_page = await open_category_page(
            context,
            'https://www.emag.ro/acuarele-pensule-si-blocuri-de-desen/brand/daco/c',
            logger,
            wait_until='networkidle',
        )
        handle_cart_dialog_task = asyncio.create_task(handle_cart_dialog(category_page, logger))
        products_ids = await handle_category_page(category_page, logger)

        # 解析购物车内的产品、清空购物车
        cart_page = await open_cart_page(context, logger, wait_until='networkidle')
        product_id_qty_list = await handle_cart_page(cart_page, products_ids, logger)
        for i, q in product_id_qty_list:
            print(i, q)

        await handle_cart_dialog_task


async def handle_category_page(page: Page, logger: Logger) -> list[str]:
    logger.info('处理类目页')
    product_cart_divs = page.locator(
        'div.card-item[data-offer-id]',
        has_not=page.locator('css=span.card-v2-badge-cmp.bg-light'),
        has=page.locator('css=button.yeahIWantThisProduct'),
    )

    data_offer_ids: list[str] = list()

    for i in range(min(40, await product_cart_divs.count())):
        while await product_cart_divs.locator('css=div.preloader').count() > 0:
            await asyncio.sleep(0.5)

        logger.info(f'正在加购第 {i+1} 个产品')

        data_offer_id: str = await product_cart_divs.nth(i).get_attribute('data-offer-id', timeout=MS1000)  # type: ignore
        while True:
            try:
                await product_cart_divs.nth(i).locator('css=button.yeahIWantThisProduct').click()
            except PlaywrightError as pe:
                logger.error(f'尝试点击第 {i+1} 个加购按钮时出错')
                continue
            else:
                data_offer_ids.append(data_offer_id)
                logger.success(f'成功点击了第 {i+1} 个加购按钮 data-offer-id={data_offer_id}')
                break

    return data_offer_ids


async def handle_cart_page(
    page: Page, product_ids: list[str], logger: Logger
) -> list[tuple[str, Optional[str]]]:
    logger.info('处理购物车页')

    product_id_qty_list: list[tuple[str, Optional[str]]] = list()

    # 每个产品卡片
    product_cart_divs = page.locator('css=div.cart-widget[data-id]')

    # 每个产品卡片的 qty-value 标签
    qty_value_spans = product_cart_divs.locator('css=span.qty-value').filter(visible=True)
    # await qty_value_spans.highlight()
    # 每个 qty-value 标签对应的加购数量输入框（可以获取最大可加购数）
    max_qty_inputs = qty_value_spans.locator('xpath=/preceding-sibling::input[@max]')
    for i in range(await max_qty_inputs.count()):
        # 该输入框对应的产品卡片
        ancestor_cart_div = max_qty_inputs.nth(i).locator(
            'xpath=/ancestor::div[contains(@class,"cart-widget") and @data-id]'
        )
        # 产品卡片包含的 data-id
        data_id: str = await ancestor_cart_div.get_attribute('data-id', timeout=MS1000)  # type: ignore
        data_id = re.search(r'_?(\d+)$', data_id).group(1)  # type: ignore
        # 该输入框的最大可加购数
        qty = await max_qty_inputs.nth(i).get_attribute('max', timeout=MS1000)
        product_id_qty_list.append((data_id, qty))

    temp: dict[str, Optional[str]] = dict()
    for pid in product_ids:
        temp[pid] = None
    for pid, qty in product_id_qty_list:
        temp[pid] = qty

    try:
        await clear_cart(page, logger)
    except PlaywrightError as pe:
        logger.error(f'清空购物车时出错\n{pe}')

    return [(pid, qty) for pid, qty in temp.items()]


if __name__ == '__main__':
    # run(test_bm())
    # asyncio.run(test_pcm())
    asyncio.run(test_add_cart_parse_qty_clear_cart())
