"""测试 CategoryPageWorker"""

from asyncio import run

from scraper_utils.utils.browser_util import BrowserManager, ResourceType, MS1000
from scraper_utils.utils.json_util import write_json

from emag_crawler.utils import logger
from emag_crawler.workers.category_page import CategoryPageWorker

# TODO 未完成
"""
类目页的下一页按钮 //a[@aria-label="Next" and @data-page]
data-page 为下一页的页码
"""


async def main():
    async with BrowserManager(
        'C:/Program Files/Google/Chrome/Application/chrome.exe',
        'chrome',
        headless=False,
        args=['--start-maximized'],
    ) as bm:
        context = await bm.new_context(
            abort_res_types=(ResourceType.IMAGE, ResourceType.MEDIA, ResourceType.FONT),
            default_navigation_timeout=60 * MS1000,
            default_timeout=60 * MS1000,
            need_stealth=True,
        )
        w = CategoryPageWorker(context, 'bare-transversale')
        resuls = await w.start_scrape()
        resuls.sort(key=lambda r: (r.source_url, r.rank))

        write_json('temp.json', list(r.model_dump() for r in resuls), indent=4, async_mode=False)


if __name__ == '__main__':
    logger.info('程序启动')
    run(main())
    logger.info('程序结束')
