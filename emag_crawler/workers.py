"""工作协程"""

from __future__ import annotations

from asyncio import create_task
from re import compile as re_compile
from sys import stderr
from typing import TYPE_CHECKING

from scraper_utils.constants.time_constant import MS1000
from scraper_utils.exceptions.browser_exception import PlaywrightError
from scraper_utils.utils.browser_util import abort_resources, stealth, ResourceType

from .models import CategoryPageProduct
from .utils import (
    logger as base_logger,
    block_track,
    hide_cookie_banner,
    build_category_url,
    parse_pnk_from_url,
)

if TYPE_CHECKING:
    from typing import Literal, Optional

    from loguru import Logger
    from playwright.async_api import BrowserContext, Page, Response, Locator


class CategoryPageWorker:
    def __init__(self, context: BrowserContext, category: str):
        self.__context = context
        self.category = category  # 类目
        self.__max_page_num = 1  # 这个类目最多能爬多少页

        self.__continuable = True  # 是否允许继续爬取（没检测到需要验证）时可以继续爬取
        self.__finished: bool = False  # 是否爬取完成

        self.__result: list[CategoryPageProduct] = list()  # 存放爬取结果

        self.logger = get_worker_logger(category)

    @property
    def result(self) -> list[CategoryPageProduct]:
        if not self.is_finished():
            self.logger.warning('在爬取未完成时获取爬取结果')
        return self.__result

    def is_finished(self) -> bool:
        """是否爬取完成"""
        return self.__finished

    def check_response(self, response: Response) -> None:
        if response.status == 511:
            self.__continuable = False
            page = response.frame.page
            self.logger.error(f'在 "{page.url}" 页面的 "{response.url}" 响应检测到需要验证')

    async def open_category_page(
        self,
        url: str,
        wait_until: Literal['commit', 'domcontentloaded', 'load', 'networkidle'] = 'load',
    ) -> Page:
        """创建空页面，打开类目页链接"""
        self.logger.info('创建空页面')

        page = await self.__context.new_page()

        # 隐藏页面
        await stealth(page)
        # 节省加载时间
        await abort_resources(page, (ResourceType.IMAGE, ResourceType.MEDIA, ResourceType.FONT))

        # 屏蔽 eMAG 页面埋点
        await block_track(page)
        # 隐藏 Cookie 提醒
        await hide_cookie_banner(page)
        # 检测验证码
        page.on('response', self.check_response)

        self.logger.info(f'访问链接 "{url}"')
        await page.goto(url, wait_until=wait_until)
        return page

    async def handle_cart_dialog(self, page: Page, interval: int = 1_000) -> None:
        """
        处理类目页面点击加购按钮后可能出现的弹窗

        当页面还未关闭时，每隔 `interval` 毫秒尝试点击一次加购弹窗的关闭按钮
        """
        self.logger.info(f'为 "{page.url}" 页面启动处理加购弹窗任务')
        while not page.is_closed():
            dialog_close_button = page.locator('xpath=//button[@class="close gtm_6046yfqs"]')
            try:
                await dialog_close_button.click(timeout=interval)
            except PlaywrightError:
                pass
        self.logger.info(f'检测到 "{page.url}" 页面关闭，处理加购弹窗任务即将关闭')

    async def parse_one_product_card(self, card_div: Locator, page_url: str, rank: int) -> CategoryPageProduct:
        """传入一个产品卡片，解析该产品卡片的产品信息"""

        # 解析 pnk
        data_url = await card_div.get_attribute('data-url', timeout=MS1000)
        pnk = parse_pnk_from_url(data_url)

        # 解析是否带 Top Favorite 标志
        top_favorite_span = card_div.locator(
            'css=span.card-v2-badge-cmp',
            has_text=re_compile(r'Top Favorite'),
        )
        top_favorite = await top_favorite_span.count() == 1
        if await top_favorite_span.count() > 1:
            self.logger.error(f'在 "{page_url}" 的第 {rank} 个产品卡片找到了多个 top_favorite_span')

        # 解析价格
        price = None
        price_p = card_div.locator('css=p.product-new-price')
        price_p_text = await price_p.inner_text(timeout=MS1000)
        price_text_match = re_compile(r'(\d+),(\d+) Lei').search(price_p_text)
        if price_text_match is not None:
            price = float(f'{price_text_match.group(1)}.{price_text_match.group(2)}')
        else:
            self.logger.error(
                f'在 "{page_url}" 的第 {rank} 个产品卡片，正则表达式从 "{price_p_text}" 匹配不到价格'
            )

        # 解析评分
        average_rating = None
        average_rating_span = card_div.locator('css=span.average-rating')
        if await average_rating_span.count() == 1:
            average_rating_span_text = await average_rating_span.inner_text(timeout=MS1000)
            try:
                average_rating = float(average_rating_span_text)
            except ValueError as ve:
                self.logger.error(
                    f'在 "{page_url}" 的第 {rank} 个产品卡片，无法将 "{average_rating_span_text}" 转为小数形式的评分'
                )

        # 解析评论数
        review_count = None
        review_count_span = card_div.locator('css=span.visible-xs-inline-block')
        if await review_count_span.count() == 1:
            review_count_span_text = await review_count_span.inner_text(timeout=MS1000)
            review_count_text_match = re_compile(r'\((\d+)\)').search(review_count_span_text)
            if review_count_text_match is not None:
                review_count = int(review_count_text_match.group(1))
            else:
                self.logger.error(
                    f'在 "{page_url}" 的第 {rank} 个产品卡片，正则表达式从 "{review_count_span_text}" 匹配不到评论数'
                )

        # 评分和评论数不同时为空或同时非空
        if (average_rating is None and review_count is not None) or (
            average_rating is not None and review_count is None
        ):
            self.logger.error(
                f'在 "{page_url}" 的第 {rank} 个产品卡片，评分和评论数不同时为空或同时非空，评分="{average_rating}"评论数="{review_count}"'
            )

        return CategoryPageProduct(
            pnk=pnk,
            category=self.category,
            source_url=page_url,
            rank=rank,
            is_top_favorite=top_favorite,
            price=price,
            rating=average_rating,
            review_count=review_count,
            cart_added=False,
            max_qty=None,
        )

    async def parse_page(self, page: Page) -> list[CategoryPageProduct]:
        """解析类目页数据"""
        # 启动处理加购弹窗的任务
        handle_cart_dialog_task = create_task(self.handle_cart_dialog(page))

        # 非 Promovat、非 Vezi Detalii 的加购按钮的所属产品卡片
        product_card_divs = page.locator(
            'css=div.card-item',
            has_not=page.locator('css=span.card-v2-badge-cmp.bg-light'),
            has=page.locator('css=button.yeahIWantThisProduct'),
        )
        product_card_count = await product_card_divs.count()
        self.logger.debug(
            f'在 "{page.url}" 找到 {product_card_count} 个非 Promovat、非 Vezi Detalii 的产品卡片'
        )
        # 整个页面内的产品卡片信息
        products: list[CategoryPageProduct] = list()
        for i in range(1, product_card_count + 1):
            products.append(
                await self.parse_one_product_card(
                    card_div=product_card_divs.nth(i - 1), page_url=page.url, rank=i
                )
            )

        # TODO
        await page.close()
        await handle_cart_dialog_task
        return products

    async def start_scrape(self) -> list[CategoryPageProduct]:
        """启动爬取"""
        # TEMP
        result: list[CategoryPageProduct] = list()
        if self.__continuable:
            page = await self.open_category_page(build_category_url(self.category, 1))
            result += await self.parse_page(page)

        if self.__continuable:
            page = await self.open_category_page(build_category_url(self.category, 2))
            result += await self.parse_page(page)
        # TEMP
        # TODO
        return result


##### Worker 用的 logger #####
_worker_logger_inited = False


def get_worker_logger(category: str) -> Logger:
    """加载 Worker 用的日志"""
    global _worker_logger_inited

    if _worker_logger_inited:
        return base_logger
    base_logger.add(
        stderr,
        format=(
            '[<green>{time:HH:mm:ss}</green>] [<level>{level:.3}</level>] '
            '[<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan>] '
            '[<green>{extra[category]}</green>] >>> '
            '<level>{message}</level>'
        ),
        filter=lambda record: 'category' in record['extra'],
    )
    _worker_logger_inited = True
    return base_logger.bind(category=category)
