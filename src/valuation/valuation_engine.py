"""
ValuationEngine（Phase5）
MarketIntegrator出力からバリュエーション指標を計算する。入力は書き換えない。
"""
import copy
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _safe_div(num: Any, denom: Any) -> float | None:
    """0除算回避。分母がNoneまたは0ならNone。"""
    if num is None or denom is None:
        return None
    try:
        n, d = float(num), float(denom)
    except (TypeError, ValueError):
        return None
    if d == 0:
        return None
    return n / d


def _compute_valuation(
    metrics: dict[str, Any],
    market: dict[str, Any],
) -> dict[str, float | None]:
    """metrics と market からバリュエーション指標を計算。"""
    stock_price = market.get("stock_price")
    shares_outstanding = market.get("shares_outstanding")
    dividend_per_share = market.get("dividend_per_share")
    market_cap = market.get("market_cap")
    equity = metrics.get("equity")
    net_sales = metrics.get("net_sales")
    eps = metrics.get("earnings_per_share")
    eps_growth = metrics.get("eps_growth")

    # float 化（None はそのまま）
    try:
        stock_price = float(stock_price) if stock_price is not None else None
    except (TypeError, ValueError):
        stock_price = None
    try:
        shares_outstanding = int(shares_outstanding) if shares_outstanding is not None else None
    except (TypeError, ValueError):
        shares_outstanding = None
    try:
        dividend_per_share = float(dividend_per_share) if dividend_per_share is not None else None
    except (TypeError, ValueError):
        dividend_per_share = None
    try:
        market_cap = float(market_cap) if market_cap is not None else None
    except (TypeError, ValueError):
        market_cap = None
    try:
        equity = float(equity) if equity is not None else None
    except (TypeError, ValueError):
        equity = None
    try:
        net_sales = float(net_sales) if net_sales is not None else None
    except (TypeError, ValueError):
        net_sales = None
    try:
        eps = float(eps) if eps is not None else None
    except (TypeError, ValueError):
        eps = None
    try:
        eps_growth = float(eps_growth) if eps_growth is not None else None
    except (TypeError, ValueError):
        eps_growth = None

    # PER = stock_price / eps（eps > 0、負なら None）
    per: float | None = None
    if stock_price is not None and eps is not None and eps > 0:
        per = stock_price / eps

    # BPS = equity / shares_outstanding, PBR = stock_price / bps（bps > 0）
    bps: float | None = None
    if equity is not None and shares_outstanding is not None and shares_outstanding > 0:
        bps = equity / shares_outstanding
    pbr: float | None = None
    if stock_price is not None and bps is not None and bps > 0:
        pbr = stock_price / bps

    # PSR = market_cap / net_sales（net_sales > 0）
    psr: float | None = None
    if market_cap is not None and net_sales is not None and net_sales > 0:
        psr = market_cap / net_sales

    # Dividend Yield = dividend_per_share / stock_price（stock_price > 0）
    dividend_yield: float | None = None
    if dividend_per_share is not None and stock_price is not None and stock_price > 0:
        dividend_yield = dividend_per_share / stock_price

    # PEG = per / (eps_growth * 100)（eps_growth は小数で保持、市場慣習で100倍してから割る）
    peg: float | None = None
    if per is not None and eps_growth is not None and eps_growth > 0:
        peg = per / (eps_growth * 100)

    return {
        "per": per,
        "pbr": pbr,
        "psr": psr,
        "peg": peg,
        "dividend_yield": dividend_yield,
    }


class ValuationEngine:
    """
    MarketIntegrator出力からバリュエーション指標を計算する。
    入力は書き換えず、コピーに valuation を付与して返す。
    """

    def __init__(self, integrated_data: dict[str, Any]) -> None:
        """
        Args:
            integrated_data: MarketIntegrator.integrate() の戻り値。
        """
        self._data = integrated_data

    def evaluate(self) -> dict[str, Any]:
        """
        integrated_data をベースに、current_year に valuation を付与した辞書を返す。
        入力の integrated_data は変更しない。
        """
        result = copy.deepcopy(self._data)
        current_year = result.get("current_year")
        if current_year is None:
            logger.warning("ValuationEngine: current_year が存在しません")
            return result

        metrics = current_year.get("metrics") or {}
        market = current_year.get("market") or {}
        valuation = _compute_valuation(metrics, market)
        current_year["valuation"] = valuation

        logger.info(
            "ValuationEngine: doc_id=%s, per=%s",
            result.get("doc_id"),
            valuation.get("per"),
        )
        return result
