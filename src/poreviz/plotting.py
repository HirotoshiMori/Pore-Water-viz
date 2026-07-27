"""
折れ線グラフ保存。plt.show は禁止。
図サイズ・dpi・フォントは base.yaml の plot_style から取得。
- save_timeseries_chart: 日時を横軸・換算値を縦軸にした1枚（間隙水圧 or レーザー用）
- save_line_chart: 互換用の単純折れ線（先頭2列等）
"""

from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from .fonts import apply_font_config


def save_timeseries_chart(
    df: pd.DataFrame,
    out_path: Path,
    config: dict[str, Any],
    *,
    title: str = "Time series",
    y_label: str = "Value (m)",
    ylim: list[float] | None = None,
    hlines: list[float] | None = None,
) -> None:
    """
    df は DatetimeIndex と複数数値列を持つ想定。横軸=日時、縦軸=値(m)、凡例=列名。
    """
    style = config.get("plot_style", {})
    fig_cfg = style.get("figure", {})
    aspect = fig_cfg.get("aspect", {})
    mode = aspect.get("mode", "width_height")
    if mode == "width_height":
        width_in = aspect.get("width_in", 10.0)
        height_in = aspect.get("height_in", 5.0)
    elif mode == "ratio":
        width_in = aspect.get("width_in", 10.0)
        ratio = aspect.get("ratio", 0.5)
        height_in = width_in * ratio
    else:
        width_in, height_in = 10.0, 5.0
    dpi = fig_cfg.get("dpi", 150)
    constrained = fig_cfg.get("constrained_layout", True)
    fonts = style.get("fonts", {})
    family = apply_font_config(fonts)
    title_pt = fonts.get("title", 14)
    axis_pt = fonts.get("axis_label", 12)
    tick_pt = fonts.get("tick_label", 10)
    save_cfg = style.get("save", {})
    fmt = save_cfg.get("format", "png")

    fig, ax = plt.subplots(figsize=(width_in, height_in), constrained_layout=constrained)
    fig.set_dpi(dpi)

    # 横軸: 実験開始を0とした経過時間（秒）。time_from_start_seconds 以降のみ描画
    if pd.api.types.is_datetime64_any_dtype(df.index):
        t0 = df.index[0]
        t_sec = (df.index - t0).total_seconds()
        offset = style.get("time_from_start_seconds", 0)
        if offset > 0:
            mask = t_sec >= offset
            df = df.loc[mask]
            t_sec = t_sec[mask]
            x = (t_sec - offset).values
        else:
            x = t_sec.values
        x_label_use = "Time (s)"
    else:
        x = df.index
        x_label_use = "Time"

    ax.set_title(title, fontsize=title_pt, fontfamily=family)
    ax.set_xlabel(x_label_use, fontsize=axis_pt, fontfamily=family)
    ax.set_ylabel(y_label, fontsize=axis_pt, fontfamily=family)
    ax.tick_params(axis="both", labelsize=tick_pt)

    for col in df.columns:
        ax.plot(x, df[col].values, label=col)
    legend_pt = fonts.get("legend", 10)
    ax.legend(prop={"family": family, "size": legend_pt})
    ylim_use = ylim if ylim is not None else style.get("ylim", [0.0, 0.2])
    ax.set_ylim(ylim_use[0], ylim_use[1])
    # 縦軸: hlines 指定時は 50/100/150 のみ水平線、それ以外は通常グリッド
    if hlines:
        ax.grid(True, axis="x")
        for y in hlines:
            if ylim_use[0] <= y <= ylim_use[1]:
                ax.axhline(y, color="gray", linestyle="--", linewidth=0.8, zorder=0.5)
    else:
        ax.grid(True)
    xlim_use = style.get("xlim")
    if xlim_use is not None and len(xlim_use) >= 2:
        ax.set_xlim(xlim_use[0], xlim_use[1])

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, format=fmt, transparent=save_cfg.get("transparent", False))
    plt.close(fig)


def save_line_chart(
    df: pd.DataFrame,
    out_path: Path,
    config: dict[str, Any],
) -> None:
    """
    先頭2列（または1列のみのときは index と先頭列）で折れ線を描き、out_path に保存する。
    """
    style = config.get("plot_style", {})
    fig_cfg = style.get("figure", {})
    aspect = fig_cfg.get("aspect", {})
    mode = aspect.get("mode", "width_height")
    if mode == "width_height":
        width_in = aspect.get("width_in", 10.0)
        height_in = aspect.get("height_in", 5.0)
    elif mode == "ratio":
        width_in = aspect.get("width_in", 10.0)
        ratio = aspect.get("ratio", 0.5)
        height_in = width_in * ratio
    else:
        width_in = 10.0
        height_in = 5.0
    dpi = fig_cfg.get("dpi", 150)
    constrained = fig_cfg.get("constrained_layout", True)
    fonts = style.get("fonts", {})
    family = apply_font_config(fonts)
    title_pt = fonts.get("title", 14)
    axis_pt = fonts.get("axis_label", 12)
    tick_pt = fonts.get("tick_label", 10)
    save_cfg = style.get("save", {})
    fmt = save_cfg.get("format", "png")

    labels = style.get("labels", {})
    title = labels.get("title", "Pore pressure")
    x_label = labels.get("x_label", "Time")
    y_label = labels.get("y_label", "Pore pressure (kPa)")
    series_labels = labels.get("series_labels")

    fig, ax = plt.subplots(figsize=(width_in, height_in), constrained_layout=constrained)
    fig.set_dpi(dpi)

    ax.set_title(title, fontsize=title_pt, fontfamily=family)
    ax.set_xlabel(x_label, fontsize=axis_pt, fontfamily=family)
    ax.set_ylabel(y_label, fontsize=axis_pt, fontfamily=family)
    ax.tick_params(axis="both", labelsize=tick_pt)

    numeric = df.select_dtypes(include=["number"])
    if numeric.shape[1] >= 2:
        lbl = series_labels[0] if series_labels else "Pore pressure"
        ax.plot(numeric.iloc[:, 0], numeric.iloc[:, 1], label=lbl)
    elif numeric.shape[1] == 1:
        lbl = series_labels[0] if series_labels else "Value"
        ax.plot(range(len(numeric)), numeric.iloc[:, 0], label=lbl)
    else:
        ax.plot(range(len(df)), df.index, label=series_labels[0] if series_labels else "index")
    legend_pt = fonts.get("legend", 10)
    ax.legend(prop={"family": family, "size": legend_pt})

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, format=fmt, transparent=save_cfg.get("transparent", False))
    plt.close(fig)
