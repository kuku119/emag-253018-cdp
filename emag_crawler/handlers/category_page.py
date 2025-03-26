"""处理类目页"""

from __future__ import annotations

from asyncio import create_task
from re import compile, search
from typing import TYPE_CHECKING

from scraper_utils.constants.time_constant import MS1000
from scraper_utils.exceptions.browser_exception import PlaywrightError

from .cart_page import clear_cart, open_url as open_cart_page, parse_max_qty
from ..exceptions import CaptchaError, ParsePNKError
from ..models import ProductCardItem
from ..utils import block_track, hide_cookie_banner, parse_pnk_from_url

if TYPE_CHECKING:
    from typing import Literal, Iterable

    from loguru import Logger
    from playwright.async_api import BrowserContext, Page, Locator, Response


async def open_url(
    context: BrowserContext,
    url: str,
    logger: Logger,
    wait_until: Literal['commit', 'domcontentloaded', 'load', 'networkidle'] = 'load',
) -> Page:
    """打开类目页链接"""
    logger.info(f'尝试访问 "{url}"')

    page = await context.new_page()
    await hide_cookie_banner(page)
    await block_track(page)

    response = await page.goto(url, wait_until=wait_until)
    if response is None or response.status == 511:
        raise CaptchaError(url, f'尝试访问 "{url}" 时遇到验证')

    return page


async def handle_cart_dialog(page: Page, logger: Logger, interval: int = 1000) -> None:
    """
    处理类目页面点击加购按钮后可能出现的弹窗

    当页面还未关闭时，每隔 `interval` 毫秒尝试点击一次加购弹窗的关闭按钮
    """
    logger.info(f'为 "{page.url}" 启动处理加购弹窗任务')
    while page.is_closed() is False:
        dialog_close_button = page.locator('xpath=//button[@class="close gtm_6046yfqs"]')
        try:
            await dialog_close_button.click(timeout=interval)
        except PlaywrightError:
            pass
    logger.info(f'检测到页面 "{page.url}" 关闭，处理加购弹窗任务即将关闭')


async def parse_card(
    card_div: Locator, category: str, source_url: str, rank: int, logger: Logger
) -> ProductCardItem:
    """传入一个产品卡片，解析该产品卡片的产品信息"""
    # 解析 pnk
    data_url = await card_div.get_attribute('data-url', timeout=MS1000)
    if data_url is None:
        raise ParsePNKError('')
    pnk = parse_pnk_from_url(data_url)

    # 解析 product-id
    

    # 解析是否带 Top Favorite 标志
    top_favorite_span = card_div.locator(
        'css=span.card-v2-badge-cmp',
        has_text=compile(r'Top Favorite'),
    )
    top_favorite = await top_favorite_span.count() == 1
    if await top_favorite_span.count() > 1:
        logger.warning(f'第 {rank} 个产品卡片找到了多个 top_favorite_span')

    # 解析价格
    price = None
    price_p = card_div.locator('css=p.product-new-price')
    price_p_text = await price_p.inner_text(timeout=MS1000)
    price_text_match = search(r'(\d+),(\d+) Lei', price_p_text)
    if price_text_match is not None:
        price = float(f'{price_text_match.group(1)}.{price_text_match.group(2)}')
    else:
        logger.error(f'第 {rank} 个产品卡片，正则表达式从 "{price_p_text}" 匹配不到价格')

    # 解析评分
    average_rating = None
    average_rating_span = card_div.locator('css=span.average-rating')
    if await average_rating_span.count() == 1:
        average_rating_span_text = await average_rating_span.inner_text(timeout=MS1000)
        try:
            average_rating = float(average_rating_span_text)
        except ValueError:
            logger.error(f'第 {rank} 个产品卡片，无法将 "{average_rating_span_text}" 转为小数形式的评分')
    else:
        logger.debug(f'第 {rank} 个产品卡片没有评分')

    # 解析评论数
    review_count = None
    review_count_span = card_div.locator('css=span.visible-xs-inline-block')
    if await review_count_span.count() == 1:
        review_count_span_text = await review_count_span.inner_text(timeout=MS1000)
        review_count_text_match = search(r'\((\d+)\)', review_count_span_text)
        if review_count_text_match is not None:
            review_count = int(review_count_text_match.group(1))
        else:
            logger.error(f'第 {rank} 个产品卡片，正则表达式从 "{review_count_span_text}" 匹配不到评论数')
    else:
        logger.debug(f'第 {rank} 个产品卡片没有评论数')

    # 评分和评论数不同时为空或同时非空
    if (average_rating is None and review_count is not None) or (
        average_rating is not None and review_count is None
    ):
        logger.error(
            f'第 {rank} 个产品卡片，评分和评论数不同时为空或同时非空，评分="{average_rating}"评论数="{review_count}"'
        )

    # return ProductCardItem(
    #     pnk=pnk,
    #     category=category,
    #     source_url=source_url,
    #     rank=rank,
    #     is_top_favorite=top_favorite,
    #     price=price,
    #     rating=average_rating,
    #     review_count=review_count,
    #     cart_added=False,
    #     max_qty=None,
    # )


async def add_cart(page: Page, card_div: Locator, rank: int, logger: Logger) -> None:
    """传入一个产品卡片，将该产品添加到购物车"""
    add_cart_button = card_div.locator('css=button.yeahIWantThisProduct[data-offer-id]')
    data_offer_id: str = await add_cart_button.get_attribute('data-offer-id', timeout=MS1000)  # type: ignore
    data_pnk: str = await add_cart_button.get_attribute('data-pnk', timeout=MS1000)  # type: ignore

    # TODO 如何检测购物车已满的情况？
    # TODO 如何检测加购成功
    # BUG 有时会出现

    while True:
        if page.is_closed():
            logger.error('页面关闭')
            break

        # async with page.expect_response(
        #     compile(rf'.*?emag\.ro/newaddtocart.*?X-Product-Id={data_offer_id}.*')
        # ) as response_event:

        try:
            async with page.expect_response(
                lambda r: _add_cart_response_filter(r, data_offer_id)
            ) as response_event:
                await add_cart_button.click(timeout=MS1000)
                # logger.debug(f'等待第 {rank} 个加购请求响应 data-offer-id={data_offer_id}')
        except PlaywrightError as pe:
            logger.warning(f'尝试加购第 {rank} 个产品时出错\n{pe}')
            continue
        else:
            response = await response_event.value
            if response.ok:
                logger.debug(f'加购第 {rank} 个产品成功 pnk="{data_pnk}"')
                break
            if response.status == 511:
                raise CaptchaError(page.url, f'尝试加购第 {rank} 个的产品时遇到验证')


def _add_cart_response_filter(response: Response, data_offer_id: str) -> bool:
    """筛选加购请求的响应"""
    if search(r'.*?emag\.ro/newaddtocart.*', response.url) is None:
        return False

    request = response.request

    if request.method == 'GET' or request.post_data is None:
        return False

    return data_offer_id in request.post_data


async def get_total_product_count(page: Page) -> int:
    """解析该类目共有多少产品"""
    div = page.locator('css=div.control-label.js-listing-pagination')
    count_strong = div.locator('xpath=/strong[2]')
    count = int(await count_strong.inner_text())
    return count


async def handle_products(
    page: Page, category: str, need_clear_cart: bool, logger: Logger
) -> tuple[list[ProductCardItem], bool]:
    """加购一个类目页内的所有产品、统计产品最大可加购数，返回解析结果、解析过程中是否遇到验证"""
    # 非 Promovat、非 Vezi Detalii 的加购按钮的所属产品卡片
    product_card_divs = page.locator(
        'css=div.card-item',
        has_not=page.locator('css=span.card-v2-badge-cmp.bg-light'),
        has=page.locator('css=button.yeahIWantThisProduct'),
    )
    product_card_count = await product_card_divs.count()
    logger.debug(f'在 "{page.url}" 找到 {product_card_count} 个非 Promovat、非 Vezi Detalii 的产品卡片')

    result: list[ProductCardItem] = list()

    ##### 开始加购产品 #####
    handle_dialog_task = create_task(handle_cart_dialog(page, logger))

    # 遇到验证时会终止爬取，并保存已爬取结果
    captcha_flag = False  # 目前还未遇到验证

    # 如果产品卡片不超过 40 个
    if product_card_count <= 40:
        for i in range(product_card_count):
            # 如果已经触发验证就中断
            if captcha_flag:
                break

            logger.debug(f'尝试加购产品 {i+1}/{product_card_count}')
            # 尝试加购，加购成功后往 result 中放入解析到的产品卡片信息
            card_div = product_card_divs.nth(i)
            try:
                await add_cart(page, card_div, i + 1, logger)
            except CaptchaError as ce:
                logger.error(ce)
                captcha_flag = True
                break
            else:
                p = await parse_card(card_div, category, page.url, i + 1, logger)
                p.cart_added = True
                result.append(p)
                logger.debug(f'产品加购成功 {i+1}/{product_card_count}')

    # 如果产品卡片超过 40 个
    else:
        for i in range(product_card_count):
            # 如果已经触发验证就中断
            if captcha_flag:
                break

            # 当加购到 40 个时，打开购物车处理一批产品
            if i == 40:
                try:
                    await handle_added_products(page, result, need_clear_cart, logger)
                except CaptchaError as ce:
                    logger.error(ce)
                    captcha_flag = True
                    break

            logger.debug(f'尝试加购产品 {i+1}/{product_card_count}')
            # 尝试加购，加购成功后往 result 中放入解析到的产品卡片信息
            card_div = product_card_divs.nth(i)
            try:
                await add_cart(page, card_div, i + 1, logger)
            except CaptchaError as ce:
                logger.error(ce)
                captcha_flag = True
                break
            else:
                p = await parse_card(card_div, category, page.url, i + 1, logger)
                p.cart_added = True
                result.append(p)
                logger.debug(f'产品加购成功 {i+1}/{product_card_count}')

    # 解析购物车内的产品信息
    try:
        # 解析所有 max_qty 为 None 的产品
        await handle_added_products(
            page,
            filter(lambda p: p.max_qty is None, result),
            need_clear_cart,
            logger,
        )
    except CaptchaError as ce:
        logger.error(ce)
        captcha_flag = True

    await page.close()
    await handle_dialog_task

    return result, captcha_flag


async def handle_added_products(
    page: Page, products: Iterable[ProductCardItem], need_clear_cart: bool, logger: Logger
) -> None:
    """处理已经加购的产品，解析它们的最大可加购数，按照需要清空购物车"""
    cart_page = await open_cart_page(page.context, logger, 'networkidle')
    for p in products:
        await parse_max_qty(cart_page, p, logger)

    if need_clear_cart:
        await clear_cart(cart_page, logger)

        # 等到所有的 Sterge 按钮都消失再关闭购物车页
        sterge_buttons = page.locator('css=button.remove-product[data-line]').filter(visible=True)
        while await sterge_buttons.count() > 0:
            await cart_page.wait_for_timeout(MS1000)

    logger.info('关闭购物车页')
    await cart_page.close()
