"""
CSV 読取後の加工: 日時・間隙水圧計・レーザー距離計に分割し、ref に合わせて初期値差分を m に換算。
"""

from typing import Any

import numpy as np
import pandas as pd

from . import filters as flt


def prepare_pore_laser(
    df: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    生 DataFrame を、日時インデックス・間隙水圧(m)・レーザー変位(m) の2つに変換する。
    - 1列目: 日時（0-based index 0）
    - 2〜5列目: 間隙水圧計 → (value - initial) / 10 → mm → /1000 → m
    - 6〜9列目: レーザー距離計 → mask >= 5.4 を nan、28*(value - initial) → mm → /1000 → m
    列インデックスは config["io"]["columns"] で上書き可能。
    """
    io_cfg = config.get("io", {})
    cols = io_cfg.get("columns", {})
    # channel_mapping は io 直下 or トップレベル（case で io: を省略したとき）
    ch_map = io_cfg.get("channel_mapping") or config.get("channel_mapping") or {}
    dt_col = cols.get("datetime", 0)

    # チャンネル⇔列の対応: channel_mapping があればそちらを優先（P1→列番号 等）
    if ch_map.get("pore"):
        pore_order = [f"P{i+1}" for i in range(4)]
        pore_cols = [ch_map["pore"][k] for k in pore_order if k in ch_map["pore"]]
    else:
        pore_cols = cols.get("pore", [7, 8, 9, 10])

    if ch_map.get("laser"):
        laser_order = [f"L{i+1}" for i in range(4)]
        laser_cols = [ch_map["laser"][k] for k in laser_order if k in ch_map["laser"]]
    else:
        laser_list = cols.get("laser", [2, 3, 4, 5])
        laser_count = int(io_cfg.get("laser_count", 2))
        laser_cols = laser_list[:laser_count]
    baseline_n = int(io_cfg.get("baseline_seconds", 60))  # 計測開始からこの秒後（1 sample/s 想定）の1点を基準値に使用

    # 日時: 0列目をパース
    try:
        dt_full = pd.to_datetime(df.iloc[:, dt_col], errors="coerce")
    except (TypeError, ValueError):
        # 古い pandas では errors が 'raise'|'ignore' のみのことがある
        dt_full = pd.to_datetime(df.iloc[:, dt_col], errors="ignore")
    # errors="ignore" のときは非 datetime を NaT に
    if not pd.api.types.is_datetime64_any_dtype(dt_full):
        dt_full = dt_full.apply(lambda x: x if isinstance(x, pd.Timestamp) else pd.NaT)
    if dt_full.isna().all():
        raise ValueError("日時列（1列目）を datetime に変換できませんでした")

    # 間隙水圧計: 生データを「60s との差」の m に換算（50mm オフセットは再基準化で付与）。処理順: 生 → ドリフト → DIP → フィルタ → 再基準化(60s=50mm)
    pore = df.iloc[:, pore_cols].apply(lambda s: pd.to_numeric(s, errors="coerce"))
    idx_baseline = min(baseline_n, len(pore) - 1)
    initial_pore = pore.iloc[idx_baseline]
    pore_mm_from_baseline = (pore - initial_pore) / 10.0  # mm（60s からの偏差）
    pore_m = pore_mm_from_baseline / 1000.0  # m（60s で 0。再基準化後に 60s=0.05m=50mm）
    pore_m.index = pd.DatetimeIndex(dt_full)
    pore_m.columns = [f"P{i+1}" for i in range(len(pore_cols))]
    pore_m = pore_m.loc[pore_m.index.notna()]

    # ドリフト補正: 指定区間で真値は一定とみなし、その区間の線形トレンドをドリフトとして除去
    if io_cfg.get("pore_drift_correction") == "linear_baseline":
        t_sec = (pore_m.index - pore_m.index[0]).total_seconds().values.astype(float)
        drift_start = float(io_cfg.get("pore_drift_baseline_start", 0))
        drift_seconds = float(io_cfg.get("pore_drift_baseline_seconds", 60))
        drift_end = drift_start + drift_seconds
        mask_b = (t_sec >= drift_start) & (t_sec < drift_end)
        for col in pore_m.columns:
            t_b = t_sec[mask_b]
            y_b = pore_m[col].values[mask_b]
            valid = np.isfinite(y_b)
            if np.sum(valid) >= 2:
                (slope, _) = np.polyfit(t_b[valid], y_b[valid], 1)
                pore_m[col] = pore_m[col].values - slope * t_sec

    # 間隙水圧のみ: 下向き DIP 除去（Hampel 風・下側のみ）。ケース/チャンネル毎に ON（デフォルト OFF）。
    pore_dip_cfg = io_cfg.get("pore_dip_removal")
    if pore_dip_cfg:
        pore_m = flt.apply_pore_dip_removal(pore_m, pore_dip_cfg)

    # フィルタ: Median → SG の順で適用（io.filters.pore / io.filters.laser）
    pore_filter_cfg = io_cfg.get("filters", {}).get("pore")
    if pore_filter_cfg:
        pore_m = flt.apply_filters(pore_m, pore_filter_cfg)

    # フィルタ後: baseline_seconds 時点の値を 50mm (0.05 m) に合わせる（グラフ・動水勾配の基準を統一）
    if io_cfg.get("pore_rebaseline_50mm_after_filter", True):
        t_sec = (pore_m.index - pore_m.index[0]).total_seconds().values.astype(float)
        idx_ref = int(np.argmin(np.abs(t_sec - baseline_n)))
        ref_m = 0.05  # 50 mm in m
        for col in pore_m.columns:
            v_ref = pore_m[col].iloc[idx_ref]
            if np.isfinite(v_ref):
                pore_m[col] = pore_m[col].values - float(v_ref) + ref_m

    # レーザー距離計: >= 5.4 を nan、基準値は計測開始 baseline_n 秒後の1点、28*(value - baseline) → mm → /1000 = m
    laser = df.iloc[:, laser_cols].apply(lambda s: pd.to_numeric(s, errors="coerce"))
    laser = laser.mask(laser >= 5.4, np.nan)
    initial_laser = laser.iloc[idx_baseline]
    laser_m = 28.0 * (laser - initial_laser) / 1000.0  # m
    laser_m.index = pd.DatetimeIndex(dt_full)
    laser_m.columns = [f"L{i+1}" for i in range(len(laser_cols))]
    laser_m = laser_m.loc[laser_m.index.notna()]

    laser_filter_cfg = io_cfg.get("filters", {}).get("laser")
    if laser_filter_cfg:
        laser_m = flt.apply_filters(laser_m, laser_filter_cfg)

    return pore_m, laser_m
