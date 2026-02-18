"""
JSONExporter 動作確認用スクリプト。
FinancialMaster の出力形式で財務Factのみが保存されることを検証する。

使用例:
    python scripts/test_json_export.py
"""
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)

if "DATASET_PATH" not in os.environ:
    os.environ["DATASET_PATH"] = "./financial-dataset"

from output.json_exporter import JSONExporter

if __name__ == "__main__":
    dummy_financial_dict = {
        "doc_id": "S100W67S",
        "security_code": "4827",
        "fiscal_year_end": "2025-03-31",
        "report_type": "annual",
        "current_year": {
            "metrics": {
                "equity": 5805695000.0,
                "interest_bearing_debt": None,
                "total_assets": 30554571000.0,
                "net_sales": 16094118000.0,
                "operating_income": 1461488000.0,
                "profit_loss": 828459000.0,
                "earnings_per_share": 199.68,
                "free_cash_flow": 981206000.0,
                "roe": 0.1426976,
                "roa": 0.02711234,
                "operating_margin": 0.09078123,
                "net_margin": 0.05148765,
                "equity_ratio": 0.19001234,
                "de_ratio": None,
                "sales_growth": 0.20021234,
                "profit_growth": 0.11481234,
                "eps_growth": 0.11481234,
            },
        },
        "prior_year": {
            "metrics": {
                "equity": 5018725000.0,
                "interest_bearing_debt": None,
                "total_assets": 28546264000.0,
                "net_sales": 13409224000.0,
                "operating_income": 1331316000.0,
                "profit_loss": 743129000.0,
                "earnings_per_share": 179.11,
                "free_cash_flow": 267089000.0,
                "roe": 0.1481234,
                "roa": 0.02603456,
                "operating_margin": 0.09928765,
                "net_margin": 0.05541234,
                "equity_ratio": 0.17581234,
                "de_ratio": None,
            },
        },
    }

    exporter = JSONExporter()
    output_path = exporter.export(dummy_financial_dict)

    print("=" * 60)
    print("JSONExporter テスト結果")
    print("=" * 60)
    print(f"保存パス: {output_path}")

    path_obj = Path(output_path)
    if path_obj.exists():
        print("[OK] ファイルが存在します")
    else:
        print("[NG] ファイルが存在しません")
        sys.exit(1)

    with open(path_obj, "r", encoding="utf-8") as f:
        loaded = json.load(f)

    print("\n--- JSON 構造確認 ---")
    print(f"schema_version: {loaded.get('schema_version')}")
    print(f"engine_version: {loaded.get('engine_version')}")
    print(f"data_version: {loaded.get('data_version')}")
    print(f"security_code: {loaded.get('security_code')}")

    current_year = loaded.get("current_year", {})
    prior_year = loaded.get("prior_year", {})
    current_metrics = current_year.get("metrics", {})

    checks = []
    checks.append(("schema_version == 2.0", loaded.get("schema_version") == "2.0"))
    checks.append(("engine_version 存在", loaded.get("engine_version") is not None))
    checks.append(("data_version 存在", loaded.get("data_version") is not None))
    checks.append(("generated_at 存在", loaded.get("generated_at") is not None))
    checks.append(("current_year.metrics 存在", "metrics" in current_year))
    checks.append(("prior_year.metrics 存在", "metrics" in prior_year))

    checks.append(("market セクション不在", "market" not in current_year))
    checks.append(("valuation セクション不在", "valuation" not in current_year))

    prohibited_keys = {"stock_price", "shares_outstanding", "dividend_per_share",
                       "market_cap", "per", "pbr", "psr", "peg", "dividend_yield"}
    all_metric_keys = set(current_metrics.keys())
    leaked = all_metric_keys & prohibited_keys
    checks.append(("禁止キー混入なし", len(leaked) == 0))

    roe = current_metrics.get("roe")
    if roe is not None:
        checks.append(("roe が小数4桁に丸められている", abs(roe - 0.1427) < 0.0001))

    print("\n--- 検証結果 ---")
    all_ok = True
    for name, result in checks:
        status = "[OK]" if result else "[NG]"
        print(f"{status} {name}")
        if not result:
            all_ok = False

    if all_ok:
        print("\n[OK] すべての検証が成功しました（レイヤー汚染なし）")
    else:
        print("\n[NG] 一部の検証が失敗しました")
        if leaked:
            print(f"  禁止キー検出: {leaked}")
        sys.exit(1)
