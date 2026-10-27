"""NR-600 の #BeginHeader 行数で skiprows を決める。"""

from pathlib import Path

import pandas as pd
import pytest

from poreviz.io import read_case_csv, resolve_nr600_skiprows
from poreviz.process import prepare_pore_laser


def _write_logger(path: Path, header_lines: int) -> None:
    """header_lines 行目（1始まり）を #EndHeader にし、その直後からデータ行を書く。"""
    lines = [f"#BeginHeader,{header_lines}"]
    while len(lines) < header_lines - 1:
        # 69行固定だと、この短い行がヘッダになり列が2列に潰れる。
        lines.append("チャンネル条件,")
    names = ["#EndHeader", "日時(μs)"] + [f"CH{i}" for i in range(9)]
    lines.append(",".join(names))
    assert len(lines) == header_lines
    for sec in range(3):
        row = [f"2026/01/01 00:00:{sec:02d}", "0"] + [str(1.0 + sec) for _ in range(9)]
        lines.append(",".join(row))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_begin_header_overrides_fixed_skiprows(tmp_path: Path) -> None:
    csv_path = tmp_path / "wide.csv"
    _write_logger(csv_path, header_lines=80)
    assert resolve_nr600_skiprows(csv_path, "utf-8", 69) == 79

    # 69行固定だと、2列のヘッダ行を列名にしてしまう。pandas の版により
    # 列が潰れるか、途中の行で ParserError になる。
    try:
        fixed = pd.read_csv(csv_path, skiprows=69, engine="python")
    except pd.errors.ParserError:
        fixed = None
    if fixed is not None:
        assert fixed.shape[1] < 11

    resolved = pd.read_csv(csv_path, skiprows=79, engine="python")
    assert resolved.shape[1] == 11
    assert str(resolved.iloc[0, 0]).startswith("2026/01/01")


def test_read_case_csv_uses_begin_header(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    _write_logger(data / "wide.csv", header_lines=80)
    df = read_case_csv(
        "wide",
        {"data_dir": data},
        {"io": {"encoding": "utf-8", "read_csv": {"skiprows": 69, "engine": "python"}}},
        verbose=False,
    )
    assert df.shape == (3, 11)
    pore, laser = prepare_pore_laser(
        df,
        {
            "io": {
                "columns": {"datetime": 0, "pore": [7, 8, 9, 10], "laser": [2, 3]},
                "laser_count": 2,
                "baseline_seconds": 0,
                "pore_drift_correction": False,
                "pore_rebaseline_50mm_after_filter": False,
            }
        },
    )
    assert list(pore.columns) == ["P1", "P2", "P3", "P4"]
    assert list(laser.columns) == ["L1", "L2"]


def test_missing_columns_raise_value_error_not_index_error() -> None:
    df = pd.DataFrame({"a": ["2026/01/01 00:00:00"], "b": [1.0]})
    with pytest.raises(ValueError, match="間隙水圧の列番号"):
        prepare_pore_laser(
            df,
            {"io": {"columns": {"datetime": 0, "pore": [7, 8, 9, 10], "laser": [1]}, "laser_count": 1}},
        )


def test_without_marker_keeps_fallback(tmp_path: Path) -> None:
    csv_path = tmp_path / "plain.csv"
    csv_path.write_text("x\n1\n", encoding="utf-8")
    assert resolve_nr600_skiprows(csv_path, "utf-8", 69) == 69
