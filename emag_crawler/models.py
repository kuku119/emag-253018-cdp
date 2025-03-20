"""数据模型"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator
from scraper_utils.utils.emag_util import validate_pnk

if TYPE_CHECKING:
    from typing import Optional


class CategoryPageProduct(BaseModel):
    """
    类目页能爬出的产品数据

    ---

    1. pnk，str，必须通过 validate_pnk(pnk: str) -> bool 的验证
    2. 类目，str
    3. 来源链接，str
    4. 在来源链接的排行，None 或正整数，默认为 None
    5. 是否带 Genius 标志，None 或 bool，默认为 None
    6. 是否带 Top Favorite 标志，None 或 bool，默认为 None
    7. 价格，None 或正小数，默认为 None
    8. 评分，None 或 [0, 5.0] 的小数，默认为 None
    9. 评论数，None 或非负整数，默认为 None
    """

    pnk: str = Field(..., description='产品编号')
    category: str = Field(..., description='产品类目')
    source_url: str = Field(..., description='来源链接')
    rank: Optional[int] = Field(None, description='在来源链接的排行', ge=1)
    is_genius: Optional[bool] = Field(None, description='是否带 Genius 标志')
    is_top_favorite: Optional[bool] = Field(None, description='是否带 Top Favorite 标志')
    price: Optional[float] = Field(None, description='价格', gt=0)
    rating: Optional[float] = Field(None, description='评分', ge=0, le=5.0)
    review_count: Optional[int] = Field(None, description='评论数', ge=0)

    @field_validator('pnk')
    @classmethod
    def validate_pnk(cls, v: str) -> str:
        if not validate_pnk(v):
            raise ValueError(f'"{v}" 不符合 pnk 规范')
        return v


class DetailPageProduct:
    """详情页能爬出的产品数据"""

    # TODO
