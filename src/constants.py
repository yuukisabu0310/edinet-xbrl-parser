"""
パイプラインで使用する定数。
ハードコード禁止のため、書類種別のスキップパターン等を集中管理する。
"""

# ── ダウンロード段階（edinet_client.py）──
# EDINET API v2 の docTypeCode によるフィルタ
# formCode="030000" は有価証券報告書だけでなく大量保有報告書なども含むため、
# docTypeCode で厳密に絞り込む
TARGET_DOC_TYPE_CODES = frozenset({
    "120",  # 有価証券報告書
    "130",  # 半期報告書
    "140",  # 四半期報告書
})

# ── パイプライン段階（process_all.py）──
# 処理対象外とするXBRLファイル名に含まれるパターン（小文字で部分一致）
# jplvh = 大量保有報告書（財務データを含まない）
# jpaud = 監査報告書（財務データを含まない）
SKIP_FILENAME_PATTERNS = [
    "jplvh",  # 大量保有報告書
    "jpaud",  # 監査報告書
]
