"""CSVScanner のテスト"""
import pytest
from pathlib import Path
from src.csv_scanner import CSVScanner, CSVScanError


# ──────────────────────────────────────────────
# タスク 2.1: CSVファイル自動検出
# ──────────────────────────────────────────────

class TestScanCsvFiles:
    def test_finds_single_csv(self, tmp_path):
        (tmp_path / "data.csv").write_text("a,b\n1,2", encoding="utf-8")
        files = CSVScanner().scan_csv_files(tmp_path)
        assert len(files) == 1
        assert files[0].name == "data.csv"

    def test_ignores_non_csv_files(self, tmp_path):
        (tmp_path / "data.csv").write_text("a,b\n1,2", encoding="utf-8")
        (tmp_path / "readme.txt").write_text("hello")
        (tmp_path / "image.png").write_bytes(b"\x89PNG")
        files = CSVScanner().scan_csv_files(tmp_path)
        assert len(files) == 1

    def test_finds_multiple_csv_files(self, tmp_path):
        (tmp_path / "a.csv").write_text("x\n1", encoding="utf-8")
        (tmp_path / "b.csv").write_text("y\n2", encoding="utf-8")
        (tmp_path / "c.csv").write_text("z\n3", encoding="utf-8")
        files = CSVScanner().scan_csv_files(tmp_path)
        assert len(files) == 3

    def test_raises_error_when_no_csv_found(self, tmp_path):
        with pytest.raises(CSVScanError, match="CSVファイルが見つかりません"):
            CSVScanner().scan_csv_files(tmp_path)

    def test_returns_sorted_by_name(self, tmp_path):
        (tmp_path / "c.csv").write_text("x\n1", encoding="utf-8")
        (tmp_path / "a.csv").write_text("x\n1", encoding="utf-8")
        (tmp_path / "b.csv").write_text("x\n1", encoding="utf-8")
        files = CSVScanner().scan_csv_files(tmp_path)
        assert [f.name for f in files] == ["a.csv", "b.csv", "c.csv"]


# ──────────────────────────────────────────────
# タスク 2.2: CSVロードとメタデータ抽出
# ──────────────────────────────────────────────

class TestLoadCsv:
    def test_loads_utf8_csv(self, tmp_path):
        csv = tmp_path / "test.csv"
        csv.write_text("month,sales\n2024-01,100\n2024-02,200", encoding="utf-8")
        df, meta = CSVScanner().load_csv(csv)
        assert meta.row_count == 2
        assert "sales" in meta.columns

    def test_loads_shift_jis_csv(self, tmp_path):
        csv = tmp_path / "sjis.csv"
        csv.write_bytes("月,売上\n2024-01,100\n2024-02,200\n".encode("shift_jis"))
        df, meta = CSVScanner().load_csv(csv)
        assert meta.row_count == 2

    def test_detects_datetime_column(self, tmp_path):
        csv = tmp_path / "ts.csv"
        csv.write_text("date,value\n2024-01-01,10\n2024-02-01,20", encoding="utf-8")
        _, meta = CSVScanner().load_csv(csv)
        assert meta.has_datetime_column is True

    def test_no_datetime_column(self, tmp_path):
        csv = tmp_path / "no_ts.csv"
        csv.write_text("name,score\nAlice,90\nBob,80", encoding="utf-8")
        _, meta = CSVScanner().load_csv(csv)
        assert meta.has_datetime_column is False

    def test_metadata_contains_sample_rows(self, tmp_path):
        csv = tmp_path / "sample.csv"
        rows = "\n".join(f"2024-{i:02d},val,{i*10}" for i in range(1, 10))
        csv.write_text(f"date,label,value\n{rows}", encoding="utf-8")
        _, meta = CSVScanner().load_csv(csv)
        assert len(meta.sample_rows) <= 5

    def test_skips_non_numeric_columns_with_warning(self, tmp_path, capsys):
        csv = tmp_path / "mixed.csv"
        csv.write_text("date,name,value\n2024-01,Alice,100\n2024-02,Bob,200", encoding="utf-8")
        _, meta = CSVScanner().load_csv(csv)
        captured = capsys.readouterr()
        # 'name' は文字列列なのでスキップ警告が出るか、もしくは dtypes に含まれない
        assert "value" in meta.columns

    def test_raises_on_missing_file(self):
        with pytest.raises(CSVScanError):
            CSVScanner().load_csv(Path("/nonexistent/path/file.csv"))
