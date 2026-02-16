"""
MarketIntegrator（Phase4）
FinancialMaster出力にマーケットデータを付与する。財務指標は変更しない。
"""
import copy
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _safe_float(value: Any) -> float | None:
    """None安全にfloatへ変換。"""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    """None安全にintへ変換。"""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _compute_market_cap(stock_price: float | None, shares_outstanding: int | None) -> float | None:
    """時価総額 = stock_price * shares_outstanding。どちらかがNoneならNone。"""
    if stock_price is None or shares_outstanding is None:
        return None
    try:
        return float(stock_price) * int(shares_outstanding)
    except (TypeError, ValueError):
        return None


class MarketIntegrator:
    """
    FinancialMaster出力とマーケットデータを統合する。
    財務指標は変更せず、current_year に market ブロックを付与する。
    """

    def __init__(self, financial_data: dict[str, Any], market_data: dict[str, Any]) -> None:
        """
        Args:
            financial_data: FinancialMaster.compute() の戻り値。
            market_data: stock_price, shares_outstanding, dividend_per_share を持つ辞書。
        """
        self._financial_data = financial_data
        self._market_data = market_data

    def integrate(self) -> dict[str, Any]:
        """
        financial_data をベースに、current_year に market を付与した辞書を返す。
        financial_data の内容は変更しない（コピーしてから付与）。
        """
        result = copy.deepcopy(self._financial_data)

        stock_price = _safe_float(self._market_data.get("stock_price"))
        shares_outstanding = _safe_int(self._market_data.get("shares_outstanding"))
        dividend_per_share = _safe_float(self._market_data.get("dividend_per_share"))
        market_cap = _compute_market_cap(stock_price, shares_outstanding)

        market_block = {
            "stock_price": stock_price,
            "shares_outstanding": shares_outstanding,
            "dividend_per_share": dividend_per_share,
            "market_cap": market_cap,
        }

        current_year = result.get("current_year")
        if current_year is None:
            result["current_year"] = {"market": market_block}
        else:
            current_year["market"] = market_block

        logger.info(
            "MarketIntegrator: doc_id=%s, market_cap=%s",
            result.get("doc_id"),
            market_cap,
        )
        return result
