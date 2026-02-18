"""
JSONExporter
FinancialMaster の出力を financial-dataset へ永続化する。

financial-dataset は「確定決算の財務Factのみ」を保存するデータレイク。
market / valuation セクションは含めない（レイヤー分離原則）。

Schema changes must increment schema_version.
Numeric formatting is applied only at export stage.
data_version represents fiscal period identity, not generation timestamp.

外部データリポジトリ（financial-dataset）に出力する。
DATASET_PATH 環境変数で出力先を指定する。
"""
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src import __version__

logger = logging.getLogger(__name__)

RATIO_KEYS = {
    "roe",
    "roa",
    "operating_margin",
    "net_margin",
    "equity_ratio",
    "de_ratio",
    "sales_growth",
    "profit_growth",
    "eps_growth",
}


class JSONExporter:
    """
    FinancialMaster の出力を JSON ファイルとして保存する。
    出力先: {DATASET_PATH}/{report_type}/{data_version}/{security_code}.json

    financial-dataset には財務Factのみを保存する。
    market / valuation は別レイヤー（market-dataset / valuation-engine）の責務。
    """

    def __init__(self, base_dir: str | None = None) -> None:
        """
        Args:
            base_dir: 出力ベースディレクトリ（プロジェクトルート基準）。
                      None の場合は DATASET_PATH 環境変数を使用。
        """
        if base_dir is None:
            base_dir_str = os.environ.get("DATASET_PATH")
            if not base_dir_str:
                raise EnvironmentError(
                    "DATASET_PATH 環境変数が設定されていません。"
                    ".env ファイルまたは環境変数で DATASET_PATH を設定してください。"
                )
            base_dir = base_dir_str

        self.base_dir = Path(base_dir)

    def _generate_data_version(
        self, fiscal_year_end: str | None, report_type: str | None
    ) -> str:
        """
        決算期から data_version を生成。

        Args:
            fiscal_year_end: 決算日（YYYY-MM-DD形式、例: "2025-12-31"）
            report_type: 書類種別（"annual" | "quarterly" | "unknown"）

        Returns:
            data_version（例: "2025FY", "2025Q3", "UNKNOWN"）
        """
        if not fiscal_year_end:
            logger.warning("fiscal_year_end is None, using UNKNOWN")
            return "UNKNOWN"

        try:
            # 日付をパース
            dt = datetime.strptime(fiscal_year_end, "%Y-%m-%d")
            year = dt.year
            month = dt.month

            if report_type == "annual":
                # Annual: "2025FY" 形式
                return f"{year}FY"
            elif report_type == "quarterly":
                # Quarterly: 月から四半期を判定
                if month == 3:
                    quarter = 1
                elif month == 6:
                    quarter = 2
                elif month == 9:
                    quarter = 3
                elif month == 12:
                    quarter = 4
                else:
                    # その他の月は暫定的にQ4として扱う
                    logger.warning(
                        "Unexpected month for quarterly report: %d, using Q4", month
                    )
                    quarter = 4
                return f"{year}Q{quarter}"
            else:
                # report_type が unknown または None の場合
                # 暫定的に年度形式として扱う
                logger.warning(
                    "report_type is %s, treating as annual", report_type or "None"
                )
                return f"{year}FY"
        except ValueError as e:
            logger.warning("Failed to parse fiscal_year_end: %s, using UNKNOWN", e)
            return "UNKNOWN"

    def _format_numeric_fields(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        再帰的に辞書を走査し、定義されたキーのみ丸める。
        Noneはそのまま。intは触らない。float型のみround適用。

        Args:
            data: 整形対象の辞書。

        Returns:
            整形後の辞書（新しいオブジェクト）。
        """
        if not isinstance(data, dict):
            return data

        result: dict[str, Any] = {}
        for key, value in data.items():
            if value is None:
                result[key] = None
            elif isinstance(value, dict):
                # 再帰的に処理
                result[key] = self._format_numeric_fields(value)
            elif isinstance(value, list):
                # リスト内の辞書も再帰的に処理
                result[key] = [
                    self._format_numeric_fields(item) if isinstance(item, dict) else item
                    for item in value
                ]
            elif isinstance(value, float):
                if key in RATIO_KEYS:
                    result[key] = round(value, 4)
                else:
                    result[key] = value
            else:
                # int, str などはそのまま
                result[key] = value

        return result

    def _extract_metrics_only(self, year_data: dict[str, Any]) -> dict[str, Any]:
        """
        year_data から metrics のみを抽出する。
        market / valuation が混入していても除去する（レイヤー汚染防止）。
        """
        metrics = year_data.get("metrics")
        if metrics is None:
            return {}
        return {"metrics": metrics}

    def export(self, financial_dict: dict[str, Any]) -> str:
        """
        財務Factのみを JSON として書き出し、保存パスを返す。

        Args:
            financial_dict: FinancialMaster.compute() の戻り値。

        Returns:
            保存された JSON ファイルのパス（文字列）。

        Raises:
            ValueError: security_code, report_type, data_version が存在しない場合。
        """
        security_code = financial_dict.get("security_code")
        if not security_code or not str(security_code).strip():
            raise ValueError(
                "security_code が取得できません。"
                "有価証券報告書・四半期報告書以外の書類の可能性があります。"
            )

        fiscal_year_end = financial_dict.get("fiscal_year_end")
        report_type = financial_dict.get("report_type")
        data_version = self._generate_data_version(fiscal_year_end, report_type)

        if report_type not in ["annual", "quarterly"]:
            raise ValueError(
                f"Invalid report_type: {report_type}. "
                "report_type must be 'annual' or 'quarterly'."
            )

        if not data_version or data_version == "UNKNOWN":
            raise ValueError(
                "data_version が生成できませんでした（fiscal_year_end が欠損している可能性があります）。"
                "有価証券報告書・四半期報告書以外の書類は処理対象外です。"
            )

        logger.info(
            "Exporting: security_code=%s, fiscal_year_end=%s, report_type=%s, data_version=%s",
            security_code, fiscal_year_end, report_type, data_version,
        )

        output_dir = self.base_dir / report_type / data_version
        output_dir.mkdir(parents=True, exist_ok=True)

        current_year_raw = financial_dict.get("current_year", {})
        prior_year_raw = financial_dict.get("prior_year", {})

        output_dict: dict[str, Any] = {
            "schema_version": "2.0",
            "engine_version": __version__,
            "data_version": data_version,
            "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "doc_id": financial_dict.get("doc_id", ""),
            "security_code": str(security_code),
            "fiscal_year_end": fiscal_year_end,
            "report_type": report_type,
            "current_year": self._extract_metrics_only(current_year_raw),
            "prior_year": self._extract_metrics_only(prior_year_raw),
        }

        output_dict = self._format_numeric_fields(output_dict)

        output_path = output_dir / f"{security_code}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_dict, f, indent=2, ensure_ascii=False)

        logger.info("JSONExporter: 保存完了 - %s (data_version=%s)", output_path, data_version)

        try:
            from src.output.manifest_generator import DatasetManifestGenerator
            manifest_generator = DatasetManifestGenerator()
            manifest_path = manifest_generator.save()
            logger.info("Dataset manifest generated: %s", manifest_path)
        except Exception as e:
            logger.warning("Failed to generate dataset manifest: %s", e)

        return str(output_path)
