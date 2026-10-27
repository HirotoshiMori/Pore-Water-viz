"""CSV 読取（config の io 設定を参照）。.csv / .CSV どちらも可。"""

from pathlib import Path
from typing import Any

import pandas as pd


def resolve_nr600_skiprows(csv_path: Path, encoding: str, fallback: int | None) -> int | None:
    """
    NR-600 の先頭行 ``#BeginHeader,<行数>`` があれば、その行数を使う。
    行数は #EndHeader の列名行までを含む。列名行をヘッダにするため、返す skiprows は行数-1。
    マーカーが無いファイルは fallback（base.yaml の skiprows）のまま。
    """
    try:
        with Path(csv_path).open(encoding=encoding, errors="replace", newline="") as f:
            first = f.readline().lstrip("\ufeff").strip()
    except OSError:
        return fallback
    if not first.startswith("#BeginHeader"):
        return fallback
    parts = first.split(",")
    if len(parts) < 2:
        return fallback
    count_text = parts[1].strip()
    if not count_text.isdigit():
        return fallback
    # 1行目が #BeginHeader なので、列名行の直前までを読み飛ばす。
    return max(int(count_text) - 1, 0)


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
    read_opts = dict(io_cfg.get("read_csv") or {})
    read_opts["skiprows"] = resolve_nr600_skiprows(
        csv_path, encoding, read_opts.get("skiprows")
    )

    df = pd.read_csv(csv_path, encoding=encoding, **read_opts)
    if verbose:
        print(f"[io] 読み込み完了: shape = {df.shape}")
    return df
