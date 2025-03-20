"""处理产品类目页"""

from __future__ import annotations

from asyncio.tasks import create_task
from math import ceil
from re import compile
from typing import TYPE_CHECKING

from scraper_utils.constants.time_constant import MS1000
from scraper_utils.exceptions.browser_exception import PlaywrightError
from scraper_utils.utils.emag_util import parse_pnk

from .exceptions import ParsePNKError, NoProductCardError
from .models import CategoryPageProduct
from .utils import cwd, logger, block_track, hide_cookie_banner, wait_for_element

if TYPE_CHECKING:
    from typing import Literal

    from playwright.async_api import BrowserContext, Page, Locator


async def handle_cart_dialog(page: Page, interval: int = 1000) -> None:
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


async def goto_category_page(
    context: BrowserContext,
    url: str,
    wait_until: Literal['commit', 'domcontentloaded', 'load', 'networkidle'] = 'load',
) -> Page:
    """打开类目页，检查页面有无产品卡片"""
    page = await context.new_page()

    # 隐藏 cookie 提示
    await hide_cookie_banner(page, js_path=cwd / 'js/hide-cookie-banner.js')
    # 屏蔽 eMAG 埋点
    await block_track(page)

    logger.info(f'正在访问 "{page.url}"')
    # 打开链接
    # 要等页面加载到什么程度才好？
    await page.goto(url, wait_until=wait_until)

    # 检查页面有无产品卡片
    if not await wait_for_element(
        page.locator(
            'css=div.card-item',
            has_not=page.locator('css=span.card-v2-badge-cmp.bg-light'),
            has=page.locator('css=button.yeahIWantThisProduct'),
        )
    ):
        logger.error(f'类目页 "{page.url}" 无产品卡片')
        raise NoProductCardError(page.url)
    logger.debug(f'访问成功 "{page.url}"')

    return page


async def handle_first_page(context: BrowserContext, url: str, category: str):
    """打开和解析类目页的第 1 页"""
    # TODO

    # 访问链接
    page = await goto_category_page(context, url, 'load')

    # 启动处理加购弹窗的任务
    handle_cart_dialog_task = create_task(handle_cart_dialog(page))

    # 获取这个类目下的产品总数
    control_label_div = page.locator('css=div.control-label.js-listing-pagination')
    total_product_count_strong = control_label_div.locator('xpath=/strong[2]')
    total_product_count = int(await total_product_count_strong.inner_text())
    # 计算这个类目有多少页
    max_page_num = ceil(total_product_count / 60)
    logger.debug(f'"{category}" 共有 {total_product_count} 个产品')

    # 非 Promovat、非 Vezi Detalii 的加购按钮的所属产品卡片
    product_card_divs = page.locator(
        'css=div.card-item',
        has_not=page.locator('css=span.card-v2-badge-cmp.bg-light'),
        has=page.locator('css=button.yeahIWantThisProduct'),
    )
    product_card_count = await product_card_divs.count()
    logger.debug(f'在 "{page.url}" 找到 {product_card_count} 个非 Promovat、非 Vezi Detalii 的产品卡片')

    # 整个页面内的产品卡片信息
    products: list[CategoryPageProduct] = list()
    for i in range(1, product_card_count + 1):
        products.append(
            await parse_product_card(
                card_div=product_card_divs.nth(i - 1),
                category=category,
                category_url=page.url,
                rank=i,
            )
        )

    ##### 加购产品 #####
    cur = 1

    # 如果产品卡片不超过 40 个
    if product_card_count <= 40:
        while cur <= product_card_count:
            try:
                logger.debug(f'"{page.url}" 的第 {cur} 个产品尝试加购')
                await add_one_product_to_cart(product_card_divs.nth(cur - 1))

            # 加购失败就重试
            except PlaywrightError:
                continue

            # 加购成功
            else:
                products[cur - 1].cart_added = True
                logger.debug(f'"{page.url}" 的第 {cur} 个产品加购成功')

    # 如果产品卡片超过 40 个
    else:
        while cur <= product_card_count:
            # 当加购到 40 个时，打开购物车处理一批产品
            if cur == 40:
                pass  # TODO

        pass  # TODO

    # 处理购物车内的产品
    # TODO

    await handle_cart_dialog_task


async def handle_other_page(context: BrowserContext, url: str, category: str):
    """解析类目页的 2-5 页"""
    # TODO


_top_favorite_pattern = compile(r'Top Favorite')
_price_pattern = compile(r'(\d+),(\d+) Lei')
_review_count_pattern = compile(r'\((\d+)\)')


async def parse_product_card(
    card_div: Locator, category: str, category_url: str, rank: int
) -> CategoryPageProduct:
    """传入一个产品卡片，解析该产品卡片的产品信息"""
    # 解析 pnk
    data_url = await card_div.get_attribute('data-url', timeout=MS1000)
    if data_url is None:
        raise ParsePNKError('')
    pnk = parse_pnk(data_url)
    if pnk is None:
        raise ParsePNKError(data_url)

    # 解析是否带 Top Favorite 标志
    top_favorite_span = card_div.locator(
        'css=span.card-v2-badge-cmp',
        has_text=_top_favorite_pattern,
    )
    top_favorite = await top_favorite_span.count() == 1
    if await top_favorite_span.count() > 1:
        logger.error(f'在 "{category_url}" 的第 {rank} 个产品卡片找到了多个 top_favorite_span')

    # 解析价格
    price = None
    price_p = card_div.locator('css=p.product-new-price')
    price_p_text = await price_p.inner_text(timeout=MS1000)
    price_text_match = _price_pattern.search(price_p_text)
    if price_text_match is not None:
        price = float(f'{price_text_match.group(1)}.{price_text_match.group(2)}')
    else:
        logger.error(
            f'在 "{category_url}" 的第 {rank} 个产品卡片，正则表达式从 "{price_p_text}" 匹配不到价格'
        )

    # 解析评分
    average_rating = None
    average_rating_span = card_div.locator('css=span.average-rating')
    if await average_rating_span.count() == 1:
        average_rating_span_text = await average_rating_span.inner_text(timeout=MS1000)
        try:
            average_rating = float(average_rating_span_text)
        except ValueError as ve:
            logger.error(
                f'在 "{category_url}" 的第 {rank} 个产品卡片，'
                f'无法将 "{average_rating_span_text}" 转为小数形式的评分'
            )

    # 解析评论数
    review_count = None
    review_count_span = card_div.locator('css=span.visible-xs-inline-block')
    if await review_count_span.count() == 1:
        review_count_span_text = await review_count_span.inner_text(timeout=MS1000)
        review_count_text_match = _review_count_pattern.search(review_count_span_text)
        if review_count_text_match is not None:
            review_count = int(review_count_text_match.group(1))
        else:
            logger.error(
                f'在 "{category_url}" 的第 {rank} 个产品卡片，'
                f'正则表达式从 "{review_count_span_text}" 匹配不到评论数'
            )

    # 评分和评论数不同时为空或同时非空
    if (average_rating is None and review_count is not None) or (
        average_rating is not None and review_count is None
    ):
        logger.error(
            f'在 "{category_url}" 的第 {rank} 个产品卡片，评分和评论数不同时为空或同时非空，'
            f'评分="{average_rating}"评论数="{review_count}"'
        )

    return CategoryPageProduct(
        pnk=pnk,
        category=category,
        source_url=category_url,
        rank=rank,
        is_top_favorite=top_favorite,
        price=price,
        rating=average_rating,
        review_count=review_count,
        cart_added=False,
        max_qty=None,
    )


async def add_one_product_to_cart(product_card: Locator) -> None:
    """传入一个产品卡片，加购该产品"""
    add_cart_button = product_card.locator('css=button.yeahIWantThisProduct')
    await add_cart_button.click(timeout=5 * MS1000)
