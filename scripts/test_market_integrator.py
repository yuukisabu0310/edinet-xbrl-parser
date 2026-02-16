"""
Phase4 MarketIntegrator 動作確認用スクリプト。
main.py に影響を与えない。プロジェクトルートから実行すること。

使用例:
    python scripts/test_market_integrator.py
"""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from parser.xbrl_parser import XBRLParser
from parser.context_resolver import ContextResolver
from normalizer.fact_normalizer import FactNormalizer
from financial.financial_master import FinancialMaster
from market.market_integrator import MarketIntegrator

if __name__ == "__main__":
    xbrl_path = project_root / "data/edinet/raw_xbrl/2025/S100W67S/jpcrp030000-asr-001_E05325-000_2025-03-31_01_2025-06-25.xbrl"

    if not xbrl_path.exists():
        print("XBRLファイルが見つかりません:", xbrl_path)
        sys.exit(1)

    parser = XBRLParser(xbrl_path)
    parsed_data = parser.parse()
    resolver = ContextResolver(parser.root)
    context_map = resolver.build_context_map()
    normalizer = FactNormalizer(parsed_data, context_map)
    normalized_data = normalizer.normalize()
    master = FinancialMaster(normalized_data)
    financial_data = master.compute()

    market_data = {
        "stock_price": 2500.0,
        "shares_outstanding": 5000000,
        "dividend_per_share": 50.0,
    }

    integrator = MarketIntegrator(financial_data, market_data)
    result = integrator.integrate()

    print("=" * 60)
    print("MarketIntegrator 出力")
    print("=" * 60)
    print("doc_id:", result["doc_id"])

    m = result["current_year"].get("market") or {}
    print("\n--- Market (current_year) ---")
    print("Stock Price:", m.get("stock_price"))
    print("Shares:", m.get("shares_outstanding"))
    print("Market Cap:", m.get("market_cap"))
    print("Dividend:", m.get("dividend_per_share"))

    print("\n--- metrics が維持されているか ---")
    metrics = result["current_year"].get("metrics") or {}
    print("ROE:", metrics.get("roe"))
    print("prior_year に market は無い:", "market" not in (result.get("prior_year") or {}))
