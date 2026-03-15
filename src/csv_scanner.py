"""CSVScanner — CSV ファイルの検出・読み込み・メタデータ抽出"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd


class CSVScanError(Exception):
    """CSV 検出・読み込みエラー"""


@dataclass
class CSVMetadata:
    path: Path
    row_count: int
    columns: list[str]
    dtypes: dict[str, str]
    has_datetime_column: bool
    sample_rows: list[dict] = field(default_factory=list)


class CSVScanner:
    # 試行するエンコーディング（優先順）
    _ENCODINGS = ["utf-8", "shift_jis", "utf-8-sig", "cp932"]

    def scan_csv_files(self, directory: Path) -> list[Path]:
        """ディレクトリ内の CSV を名前順で返す。見つからなければ CSVScanError。"""
        files = sorted(directory.glob("*.csv"))
        if not files:
            raise CSVScanError(
                f"CSVファイルが見つかりません: {directory}\n"
                "  CSVファイルをこのディレクトリに置いてから再実行してください。"
            )
        return files

    def load_csv(self, path: Path) -> tuple[pd.DataFrame, CSVMetadata]:
        """CSV を読み込んでメタデータを返す。読み込み失敗時は CSVScanError。"""
        if not path.exists():
            raise CSVScanError(f"ファイルが見つかりません: {path}")

        df = self._read_with_encoding(path)
        df, skipped = self._filter_numeric_columns(df)
        if skipped:
            print(f"⚠️  文字列列をスキップしました: {', '.join(skipped)}")

        has_datetime = self._detect_datetime_column(df)
        meta = CSVMetadata(
            path=path,
            row_count=len(df),
            columns=df.columns.tolist(),
            dtypes={col: str(dtype) for col, dtype in df.dtypes.items()},
            has_datetime_column=has_datetime,
            sample_rows=df.head(5).to_dict(orient="records"),
        )

        print(f"\n📋 {path.name} を読み込みました")
        print(f"   行数: {meta.row_count} / 列: {', '.join(meta.columns)}")

        return df, meta

    def _read_with_encoding(self, path: Path) -> pd.DataFrame:
        last_error: Exception | None = None
        for enc in self._ENCODINGS:
            try:
                return pd.read_csv(path, encoding=enc)
            except (UnicodeDecodeError, LookupError) as e:
                last_error = e
        raise CSVScanError(
            f"CSV の読み込みに失敗しました: {path}\n"
            f"  対応エンコーディング: {', '.join(self._ENCODINGS)}"
        ) from last_error

    def _filter_numeric_columns(
        self, df: pd.DataFrame
    ) -> tuple[pd.DataFrame, list[str]]:
        """数値列と日付文字列列のみ残す。スキップした列名を返す。"""
        keep: list[str] = []
        skip: list[str] = []

        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                keep.append(col)
            elif self._looks_like_datetime(df[col]):
                keep.append(col)
            else:
                skip.append(col)

        return df[keep], skip

    def _looks_like_datetime(self, series: pd.Series) -> bool:
        """先頭5件を datetime としてパースできれば True。"""
        sample = series.dropna().head(5)
        if sample.empty:
            return False
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                pd.to_datetime(sample)
            return True
        except (ValueError, TypeError):
            return False

    def _detect_datetime_column(self, df: pd.DataFrame) -> bool:
        """DataFrame 内に日付文字列列が存在すれば True。"""
        for col in df.columns:
            if not pd.api.types.is_numeric_dtype(df[col]):
                if self._looks_like_datetime(df[col]):
                    return True
        # 元の列を直接チェック（filter後に文字列が残っていない場合も検出）
        return False
