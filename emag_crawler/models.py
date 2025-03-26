"""数据模型"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, Field, field_validator
from scraper_utils.utils.emag_util import validate_pnk


if TYPE_CHECKING:
    pass


class ProductCardData(BaseModel):
    """
    类目页的产品卡片所包含的产品数据

    ---

    * pnk，str
    * 产品编号，str
    * 类目，str
    * 来源链接，str
    * 在来源链接的排行，正整数
    * 在类目内的排行，正整数
    * 是否带 Top Favorite 标志，None 或 bool，默认为 None
    * 价格，None 或正小数，默认为 None
    * 评分，None 或 [0, 5.0] 的小数，默认为 None
    * 评论数，None 或非负整数，默认为 None
    * 最大可加购数，None 或非负整数，默认为 None
    """

    pnk: str = Field(..., description='产品编号')
    product_id: str = Field(..., description='类目页和详情页的 data-offer-id、购物车页的 data-id')
    category: str = Field(..., description='产品类目')
    source_url: str = Field(..., description='来源链接')
    rank_in_page: int = Field(..., gt=0, description='在来源链接（一页）的排行')
    rank_in_category: int = Field(..., gt=0, description='在类目内的排行')
    is_top_favorite: bool = Field(..., description='是否带 Top Favorite 标志')
    price: float = Field(..., gt=0, description='价格')
    rating: Optional[float] = Field(None, ge=0, le=5.0, description='评分，可能没有评分')
    review_count: Optional[int] = Field(None, ge=0, description='评论数，可能没有评论数')

    cart_added: bool = Field(False, description='是否已加购，加购按钮是否点击成功')
    max_qty: Optional[int] = Field(None, ge=0, description='从购物车页解析的最大可加购数')


class ProductCartDataList(BaseModel):
    """产品卡片的产品数据的列表"""

    products: list[ProductCardData] = Field(default_factory=list, description='产品数据的列表')
