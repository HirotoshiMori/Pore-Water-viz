"""
1D フィルタ: Median と Savitzky-Golay (SG)。
時系列の平滑化に使用。YAML の io.filters で有効化。
"""

from typing import Any

import numpy as np
import pandas as pd
from scipy.signal import savgol_filter


def median_filter_1d(y: np.ndarray, window: int) -> np.ndarray:
    """
    1D メディアンフィルタ。窓内の中央値で置換。スパイク・塩胡椒ノイズに強い。
    window は奇数推奨。偶数なら +1 して使用。
    """
    if window is None or window < 1:
        return y
    win = int(window) if window % 2 == 1 else int(window) + 1
    s = pd.Series(y)
    out = s.rolling(win, center=True, min_periods=1).median()
    return np.asarray(out, dtype=float)


def savgol_filter_1d(y: np.ndarray, window_length: int, polyorder: int) -> np.ndarray:
    """
    1D Savitzky-Golay フィルタ。局所多項式フィットで平滑化。波形を保ちやすい。
    NaN は線形補間してからフィルタし、元が NaN の位置は NaN を返す。
    """
    if window_length is None or window_length < 2 or polyorder is None:
        return y
    w = int(window_length)
    p = int(polyorder)
    if w % 2 == 0:
        w += 1
    p = min(p, w - 1)
    nan_mask = ~np.isfinite(y)
    if nan_mask.all():
        return y
    y_fill = np.copy(y)
    if nan_mask.any():
        ok = np.where(~nan_mask)[0]
        y_fill[nan_mask] = np.interp(
            np.where(nan_mask)[0], ok, y[ok]
        )
    out = savgol_filter(y_fill, w, p, mode="nearest")
    out[nan_mask] = np.nan
    return out


def hampel_lower_1d(y: np.ndarray, window: int, k: float = 2.0) -> np.ndarray:
    """
    Hampel 風の下側のみ外れ値補正。窓内で median と MAD を計算し、
    現在値が median - k*MAD より小さいときだけ local median で置換（DIP 除去用）。
    MAD=0 のときは「現在値 < median」なら median で置換する。
    """
    if window is None or window < 2:
        return y
    win = int(window) if window % 2 == 1 else int(window) + 1
    half = win // 2
    n = len(y)
    out = np.copy(y).astype(float)
    for i in range(n):
        lo = max(0, i - half)
        hi = min(n, i + half + 1)
        w = y[lo:hi]
        valid = np.isfinite(w)
        if not np.any(valid):
            continue
        med = np.nanmedian(w)
        dev = np.abs(w.astype(float) - med)
        dev[~valid] = np.nan
        mad = np.nanmedian(dev)
        if mad < 1e-12:
            mad = 1e-12  # 定数窓では「現在値 < median」なら置換
        thresh = med - float(k) * mad
        if np.isfinite(out[i]) and out[i] < thresh:
            out[i] = med
    return out


def apply_pore_dip_removal(
    df: pd.DataFrame,
    dip_cfg: dict[str, Any] | None,
) -> pd.DataFrame:
    """
    間隙水圧のみ: Hampel 風の下側 DIP 除去。ケース・チャンネル毎に ON にできる。
    - dip_cfg が null/空: 未適用。
    - チャンネル別: { P1: { window: 11, k: 2 }, P3: {...} } → 指定した列だけ適用。
    - 一括: { window: 11, k: 2 }（P1..P4 をキーにした dict でない場合）→ 全列に適用。
    """
    if not dip_cfg:
        return df
    out = df.copy()
    channel_keys = {c for c in out.columns if c in dip_cfg and isinstance(dip_cfg.get(c), dict)}
    if channel_keys:
        for col in out.columns:
            cfg = dip_cfg.get(col) if isinstance(dip_cfg.get(col), dict) else None
            if cfg and (cfg.get("window") or 0) >= 2:
                w, k = int(cfg["window"]), float(cfg.get("k", 2.0))
                out[col] = hampel_lower_1d(out[col].values.astype(float), w, k)
    else:
        window = dip_cfg.get("window")
        if window is not None and int(window) >= 2:
            k = float(dip_cfg.get("k", 2.0))
            for col in out.columns:
                out[col] = hampel_lower_1d(out[col].values.astype(float), int(window), k)
    return out


def apply_filters(df: pd.DataFrame, filter_cfg: dict[str, Any] | None) -> pd.DataFrame:
    """
    filter_cfg に従い、各列に Median → SG の順でフィルタを適用する。
    filter_cfg: { median_window: int or null, sg_window: int or null, sg_polyorder: int or null }
    """
    if not filter_cfg:
        return df
    out = df.copy()
    median_win = filter_cfg.get("median_window")
    sg_win = filter_cfg.get("sg_window")
    sg_poly = filter_cfg.get("sg_polyorder", 3)

    for col in out.columns:
        y = out[col].values.astype(float)
        if median_win is not None and int(median_win) >= 1:
            y = median_filter_1d(y, int(median_win))
        if sg_win is not None and int(sg_win) >= 2:
            y = savgol_filter_1d(y, int(sg_win), int(sg_poly))
        out[col] = y
    return out
