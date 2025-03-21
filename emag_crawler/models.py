"""数据模型"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, Field, field_validator
from scraper_utils.utils.emag_util import validate_pnk

from .exceptions import ParsePNKError

if TYPE_CHECKING:
    pass


class CategoryPageProduct(BaseModel):
    """
    类目页能爬出的产品数据

    ---

    1. pnk，str，必须通过 validate_pnk(pnk: str) -> bool 的验证
    2. 类目，str
    3. 来源链接，str
    4. 在来源链接的排行，正整数
    5. 是否带 Top Favorite 标志，None 或 bool，默认为 None
    6. 价格，None 或正小数，默认为 None
    7. 评分，None 或 [0, 5.0] 的小数，默认为 None
    8. 评论数，None 或非负整数，默认为 None
    9. 最大可加购数，None 或非负整数，默认为 None
    """

    pnk: str = Field(..., description='产品编号')
    category: str = Field(..., description='产品类目')
    source_url: str = Field(..., description='来源链接')
    rank: int = Field(..., ge=1, description='在来源链接的排行')
    is_top_favorite: Optional[bool] = Field(None, description='是否带 Top Favorite 标志')
    price: Optional[float] = Field(None, gt=0, description='价格')
    rating: Optional[float] = Field(None, ge=0, le=5.0, description='评分')
    review_count: Optional[int] = Field(None, ge=0, description='评论数')
    cart_added: Optional[bool] = Field(None, description='是否已加购')

    # TODO 对于在购物车里不显示 qty 的产品要怎么办
    max_qty: Optional[int] = Field(None, ge=0, description='最大可加购数')

    @field_validator('pnk')
    @classmethod
    def validate_pnk(cls, v: str) -> str:
        if not validate_pnk(v):
            raise ParsePNKError(v)
        return v


class DetailPageProduct:
    """详情页能爬出的产品数据"""

    # TODO
