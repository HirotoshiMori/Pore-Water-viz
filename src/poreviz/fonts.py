"""Matplotlib font setup for CJK text in plot titles."""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
from matplotlib import font_manager

_CJK_CANDIDATES = [
    "Hiragino Sans",
    "Hiragino Kaku Gothic ProN",
    "Hiragino Kaku Gothic Pro",
    "Yu Gothic",
    "YuGothic",
    "Meiryo",
    "MS Gothic",
    "Noto Sans CJK JP",
    "Noto Sans JP",
    "IPAPGothic",
    "IPAexGothic",
    "BIZ UDPGothic",
    "BIZ UDGothic",
]


def _available_font_names() -> set[str]:
    return {f.name for f in font_manager.fontManager.ttflist}


def resolve_cjk_font(explicit: str | None = None) -> str | None:
    """Return a CJK-capable font name; auto-detect when explicit is auto/empty."""
    if explicit and str(explicit).lower() not in {"auto", "none", ""}:
        name = str(explicit)
        try:
            font_manager.findfont(name, fallback_to_default=False)
            return name
        except (ValueError, OSError):
            pass

    available = _available_font_names()
    for candidate in _CJK_CANDIDATES:
        if candidate in available:
            return candidate
        for name in available:
            if candidate in name:
                return name
    return None


def apply_font_config(fonts: dict[str, Any] | None) -> str:
    """
    Apply plot_style.fonts to matplotlib rcParams.
    Prefer CJK font with Latin fallback from fonts.family.
    """
    fonts = fonts or {}
    latin = fonts.get("family", "DejaVu Sans")
    cjk = resolve_cjk_font(fonts.get("cjk_family"))

    if cjk:
        plt.rcParams["font.family"] = [cjk, latin, "sans-serif"]
        primary = cjk
    else:
        plt.rcParams["font.family"] = [latin, "sans-serif"]
        primary = latin

    plt.rcParams["axes.unicode_minus"] = False
    return primary
