"""CSV 読取（config の io 設定を参照）。.csv / .CSV どちらも可。"""

from pathlib import Path
from typing import Any

import pandas as pd


def resolve_csv_path(data_dir: Path, case_id: str) -> Path:
    """data_dir 内で case_id に対応する CSV を探す（拡張子は .csv / .CSV 不問）。"""
    data_dir = Path(data_dir)
    for p in data_dir.iterdir():
        if p.is_file() and p.stem == case_id and p.suffix.lower() == ".csv":
            return p
    raise FileNotFoundError(f"データファイルが見つかりません: {data_dir / f'{case_id}.csv'} (.csv / .CSV を確認)")


def read_case_csv(
    case_id: str, paths: dict[str, Path], config: dict[str, Any], *, verbose: bool = True
) -> pd.DataFrame:
    """
    data/{case_id}.csv を読み込む（.csv / .CSV どちらも可）。
    verbose=True のときのみ shape を print する。
    """
    csv_path = resolve_csv_path(paths["data_dir"], case_id)

    io_cfg = config.get("io", {})
    encoding = io_cfg.get("encoding", "utf-8")
    read_opts = io_cfg.get("read_csv") or {}

    df = pd.read_csv(csv_path, encoding=encoding, **read_opts)
    if verbose:
        print(f"[io] 読み込み完了: shape = {df.shape}")
    return df
