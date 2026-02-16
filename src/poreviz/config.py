"""
base.yaml / case.yaml の読み込み、deep-merge、検証、config_used 保存。
Phase 3: validate_base / validate_case 強化、cases_dir 対応。
"""

from pathlib import Path
from typing import Any

import yaml

from . import env

_REQUIRED_PATH_KEYS = ("root", "data_dir", "params_dir", "output_dir")


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """base の上に override を再帰的にマージ。リストは置換。"""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def validate_base(base: dict[str, Any]) -> None:
    """
    base.yaml の必須キーを検査。
    - project.paths.local / colab の各必須パス
    - io（encoding または read_csv の最低限）
    - plot_style.figure.dpi, aspect, fonts(title, axis_label, legend)
    """
    if not base or "project" not in base or "paths" not in base["project"]:
        raise ValueError("base.yaml に project.paths がありません")
    paths = base["project"]["paths"]
    for env_name in ("local", "colab"):
        if env_name not in paths:
            raise ValueError(f"base.yaml に project.paths.{env_name} がありません")
        for key in _REQUIRED_PATH_KEYS:
            if key not in paths[env_name]:
                raise ValueError(f"base.yaml の project.paths.{env_name} に {key} がありません")
    if "io" not in base:
        raise ValueError("base.yaml に io がありません")
    io_cfg = base["io"]
    if "encoding" not in io_cfg and "read_csv" not in io_cfg:
        raise ValueError("base.yaml の io に encoding または read_csv がありません")
    if "plot_style" not in base:
        raise ValueError("base.yaml に plot_style がありません")
    ps = base["plot_style"]
    if "figure" not in ps:
        raise ValueError("base.yaml の plot_style に figure がありません")
    fig = ps["figure"]
    if "dpi" not in fig:
        raise ValueError("base.yaml の plot_style.figure に dpi がありません")
    if "aspect" not in fig:
        raise ValueError("base.yaml の plot_style.figure に aspect がありません")
    asp = fig["aspect"]
    if "mode" not in asp:
        raise ValueError("base.yaml の plot_style.figure.aspect に mode がありません")
    if asp["mode"] == "width_height":
        if "width_in" not in asp or "height_in" not in asp:
            raise ValueError("plot_style.figure.aspect に width_in/height_in がありません")
    elif asp["mode"] == "ratio":
        if "width_in" not in asp or "ratio" not in asp:
            raise ValueError("plot_style.figure.aspect に width_in/ratio がありません")
    if "fonts" not in ps:
        raise ValueError("base.yaml の plot_style に fonts がありません")
    fonts = ps["fonts"]
    for key in ("title", "axis_label", "legend"):
        if key not in fonts:
            raise ValueError(f"base.yaml の plot_style.fonts に {key} がありません")


def validate_case(case: dict[str, Any]) -> None:
    """
    case.yaml（存在する場合）の型チェック。
    channels / geometry / time / processing がある場合は dict または list であること。
    """
    if not case:
        return
    for key in ("channels", "geometry", "time", "processing"):
        if key not in case:
            continue
        val = case[key]
        if key == "channels" and isinstance(val, list):
            continue
        if not isinstance(val, dict):
            raise ValueError(f"case.yaml の {key} は dict または list である必要があります: {type(val)}")


def load_base(
    base_path: str | Path | None = None,
    cases_dir: str | Path | None = None,
) -> tuple[dict[str, Any], dict[str, Path]]:
    """
    base.yaml を読み込み、解決済みパスと合わせて返す。
    cases_dir を指定すると params/cases の代わりにそのパスを cases 用に使う。
    Returns: (base_config, resolved_paths)
    """
    env_type = env.get_environment()
    default_paths = env.get_paths(env_type)

    if base_path is None:
        base_path = default_paths["params_dir"] / "base.yaml"
    else:
        base_path = Path(base_path)

    if not base_path.exists():
        raise FileNotFoundError(f"base.yaml が見つかりません: {base_path}")

    with open(base_path, encoding="utf-8") as f:
        base = yaml.safe_load(f)

    validate_base(base)

    path_spec = base["project"]["paths"].get(env_type) or base["project"]["paths"].get("local", {})

    root = Path(path_spec.get("root", "."))
    if not root.is_absolute():
        root = (default_paths["root"] / root).resolve()

    def resolve_key(key: str) -> Path:
        raw = path_spec.get(key, "")
        p = Path(raw)
        if not p.is_absolute():
            p = (root / p).resolve()
        else:
            p = p.resolve()
        return p

    resolved = {
        "root": root,
        "data_dir": resolve_key("data_dir"),
        "params_dir": resolve_key("params_dir"),
        "output_dir": resolve_key("output_dir"),
    }
    if cases_dir is not None:
        resolved["cases_dir"] = Path(cases_dir).resolve()
    else:
        resolved["cases_dir"] = (resolved["params_dir"] / "cases").resolve()
    return base, resolved


def load_case(case_path: str | Path | None) -> dict[str, Any] | None:
    """case.yaml を読み込む。存在しなければ None。"""
    if case_path is None:
        return None
    p = Path(case_path)
    if not p.exists():
        return None
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def merge(base: dict[str, Any], case: dict[str, Any] | None) -> dict[str, Any]:
    """base の上に case を deep-merge。case が None または空なら base をそのまま返す。"""
    if not case:
        return dict(base)
    return _deep_merge(base, case)


def validate(merged: dict[str, Any], paths: dict[str, Path]) -> None:
    """paths と merged の整合（data_dir/output_dir、plot_style）を検査。"""
    if "data_dir" not in paths or "output_dir" not in paths:
        raise ValueError("paths に data_dir または output_dir がありません")
    ps = merged.get("plot_style") or {}
    fig = ps.get("figure") or {}
    if "dpi" not in fig:
        raise ValueError("plot_style.figure.dpi が設定にありません")
    if "fonts" not in ps:
        raise ValueError("plot_style.fonts が設定にありません")


def save_config_used(merged: dict[str, Any], out_path: Path) -> None:
    """マージ済み設定を output/{case_id}/logs/config_used.yml に保存。"""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(merged, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
