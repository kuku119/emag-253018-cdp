"""类目页"""

from __future__ import annotations

from math import ceil
from typing import TYPE_CHECKING

from scraper_utils.exceptions.browser_exception import PlaywrightError

from ..exceptions import CaptchaError
from ..handlers.category_page import (
    handle_products,
    open_url as open_category_page,
    get_total_product_count,
)

from ..logger import logger
from ..models import ProductCardItem
from ..utils import build_category_url

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext


class CategoryPageWorker:
    # TODO 发生异常时保存已经爬取的数据

    def __init__(self, context: BrowserContext, category: str):
        self.context = context

        self.category = category
        self.max_crawlable_page: int = 1  # 这个类目最多能爬多少页

        self.continuable: bool = True  # 是否允许继续爬取（没检测到需要验证）时可以继续爬取

        self.result: list[ProductCardItem] = list()

        self.logger = logger.bind(category=category)

    async def start_scrape(self) -> list[ProductCardItem]:
        """开始爬取"""
        logger.info(f'开始爬取 "{self.category}"')

        # BUG 抓不到 PlaywrightError
        # TODO 在 KeyboardInterrupt 时能中止爬取并保存已爬取结果

        # 处理第一页
        self.logger.info(f'开始爬取 "{self.category}" 第 1 页')
        try:
            first_page = await open_category_page(
                self.context,
                build_category_url(self.category),
                self.logger,
                'networkidle',
            )
        except CaptchaError as ce:
            logger.error(f'爬取第 1 页时触发验证\n{ce}')
        except PlaywrightError as pe:
            logger.error(f'爬取第 1 页时出错\n{pe}')
        except BaseException as be:
            logger.error(be)

        else:
            # 这个类目能爬取多少页
            total_product_count = await get_total_product_count(first_page)
            self.max_crawlable_page = min(ceil(total_product_count / 60), 5)
            self.logger.debug(f'"{self.category}" 最大爬取页码 {self.max_crawlable_page}')

            # 第一页的解析结果和是否触发验证
            result, first_captcha_flag = await handle_products(
                first_page,
                self.category,
                True,
                self.logger,
            )

            # 触发验证
            if first_captcha_flag:
                return result

            # # 爬取 2-5 页
            # for i in range(2, self.max_crawlable_page + 1):
            #     self.logger.info(f'开始爬取 "{self.category}" 第 {i} 页')

            #     url = build_category_url(self.category, i)
            #     try:
            #         page = await open_category_page(
            #             self.context,
            #             url,
            #             self.logger,
            #             'networkidle',
            #         )
            #     except CaptchaError as ce:
            #         logger.error(f'爬取第 {i} 页时触发验证\n{ce}')
            #         break
            #     except PlaywrightError as pe:
            #         logger.error(f'爬取第 {i} 页时出错\n{pe}')
            #         break
            #     except BaseException as be:
            #         logger.error(be)
            #         break

            #     else:
            #         res, flag = await handle_products(page, self.category, True, self.logger)
            #         result.extend(res)

            #         # 爬取 2-5 页时触发了验证
            #         if flag:
            #             break

            self.result = result

        self.logger.info(f'爬取结束 "{self.category}"')
        return self.result
