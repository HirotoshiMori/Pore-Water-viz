"""CLI スモーク: subprocess で終了コードと dry-run の挙動。"""

import subprocess
import sys
from pathlib import Path

import pytest


def test_cli_run_case_exit_zero(test_root: Path) -> None:
    """poreviz run --case minimal が終了コード 0 になる。"""
    result = subprocess.run(
        [sys.executable, "-m", "poreviz", "run", "--case", "minimal", "--base", "params/base_test.yaml"],
        cwd=test_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (result.stdout, result.stderr)


def test_cli_dry_run_creates_no_output_files(test_root: Path) -> None:
    """--dry-run では output 配下にファイルが生成されない。"""
    out_before = list((test_root / "output").iterdir()) if (test_root / "output").exists() else []
    result = subprocess.run(
        [sys.executable, "-m", "poreviz", "run", "--case", "minimal", "--base", "params/base_test.yaml", "--dry-run"],
        cwd=test_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    out_after = list((test_root / "output").iterdir()) if (test_root / "output").exists() else []
    assert len(out_after) == len(out_before), "dry-run で output が増えていないこと"
