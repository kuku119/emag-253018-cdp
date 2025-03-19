"""工作协程"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext


async def category_first_page_worker(context: BrowserContext):
    """爬取类目页第 1 页的 worker"""
    # TODO


async def category_other_page_worker(context: BrowserContext):
    """爬取类目页 2-5 页的 worker"""
    # TODO
