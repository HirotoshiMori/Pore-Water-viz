"""
run_case / run_all のオーケストレーション。
Phase 3: dry_run, overwrite, run.log, 入力検査、エラー文脈。
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import config, env, io, process, plotting


def _error_context(
    case_id: str,
    csv_path: Path,
    base_path: Path,
    case_yaml_path: Path | None,
    output_dir: Path,
) -> str:
    """例外メッセージ用の文脈文字列。"""
    parts = [
        f"case_id={case_id}",
        f"入力={csv_path}",
        f"base.yaml={base_path}",
        f"出力先={output_dir}",
    ]
    if case_yaml_path:
        parts.insert(3, f"case.yaml={case_yaml_path}")
    return " | ".join(parts)


def _setup_case_logger(log_path: Path) -> logging.Logger:
    """output/{case_id}/logs/run.log に書き出す Logger。コンソールは print で出す。"""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(f"poreviz.run.{log_path.parent.parent.name}")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fmt = logging.Formatter("%(message)s")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger


def discover_cases(data_dir: Path, glob_pattern: str = "*.csv") -> list[str]:
    """data_dir 直下の CSV（.csv / .CSV どちらも可）から case_id 一覧（拡張子除く）を返す。"""
    data_dir = Path(data_dir)
    if not data_dir.exists():
        return []
    stems = set()
    for p in data_dir.iterdir():
        if p.is_file() and p.suffix.lower() == ".csv":
            stems.add(p.stem)
    return sorted(stems)


def run_case(
    case_id: str,
    base_path: str | Path | None = None,
    base_config: dict[str, Any] | None = None,
    paths: dict[str, Path] | None = None,
    *,
    dry_run: bool = False,
    overwrite: bool = True,
    cases_dir_override: Path | None = None,
    verbose: bool = True,
) -> list[Path]:
    """
    1ケースを実行。CSV 読取 → 図保存 → config_used / run.log 保存。
    overwrite が False（--no-overwrite）のとき、主要成果物が既にあればスキップする。
    """
    if base_config is None or paths is None:
        base_config, paths = config.load_base(base_path, cases_dir_override)
        env.print_startup(paths)

    cases_dir = paths.get("cases_dir") or (paths["params_dir"] / "cases")
    case_yaml_path = cases_dir / f"{case_id}.yaml"
    case_dir = paths["output_dir"] / case_id
    figures_dir = case_dir / "figures"
    logs_dir = case_dir / "logs"
    base_path_resolved = paths["params_dir"] / "base.yaml"
    try:
        csv_path = io.resolve_csv_path(paths["data_dir"], case_id)
    except FileNotFoundError as e:
        ctx = _error_context(case_id, paths["data_dir"] / f"{case_id}.csv", base_path_resolved, case_yaml_path if case_yaml_path.exists() else None, case_dir)
        raise FileNotFoundError(f"{e} ({ctx})") from e

    if dry_run:
        has_case_yaml = case_yaml_path.exists()
        if verbose:
            print(f"[dry-run] case_id={case_id} | 入力={csv_path} | 出力={case_dir} | case.yaml={'あり' if has_case_yaml else 'なし'}")
        return []

    # overwrite が無い場合: 主要成果物（figures の3枚 + logs/config_used.yml）が揃っていればスキップ
    ext = (base_config.get("plot_style") or {}).get("save") or {}
    ext = ext.get("format", "png")
    fig_pore = figures_dir / f"pore_pressure.{ext}"
    fig_laser = figures_dir / f"laser_displacement.{ext}"
    fig_hydraulic = figures_dir / f"hydraulic_gradient.{ext}"
    config_used = logs_dir / "config_used.yml"
    if not overwrite and case_dir.exists():
        if fig_pore.exists() and fig_laser.exists() and fig_hydraulic.exists() and config_used.exists():
            if verbose:
                print(f"[pipeline] スキップ（既存成果物あり）: case_id={case_id}")
            return []

    if verbose:
        print(f"[pipeline] 対象ケース数: 1")
        print(f"[pipeline] case.yaml: {'あり' if case_yaml_path.exists() else 'なし'}")
        print(f"[pipeline] 開始: case_id = {case_id}")
        print(f"[pipeline] 入力CSV: {csv_path}")
        print(f"[pipeline] 出力ディレクトリ: {case_dir}")

    case_cfg = config.load_case(case_yaml_path)
    config.validate_case(case_cfg) if case_cfg else None
    merged = config.merge(base_config, case_cfg)
    config.validate(merged, paths)

    figures_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    env_type = env.get_environment(silent=True)
    run_log_path = logs_dir / "run.log"
    log = _setup_case_logger(run_log_path)

    started = datetime.now(timezone.utc).isoformat()
    log.info(f"開始: {started}")
    log.info(f"ENV: {env_type}")
    log.info(f"base.yaml: {base_path_resolved}")
    log.info(f"case.yaml: {case_yaml_path} (存在={case_yaml_path.exists()})")

    config_used_path = logs_dir / "config_used.yml"
    config.save_config_used(merged, config_used_path)

    df = io.read_case_csv(case_id, paths, merged, verbose=verbose)
    pore_m, laser_m = process.prepare_pore_laser(df, merged)
    # channel_mapping 指定時は、マッピングに含まれる系列だけ描画する（io 直下 or トップレベル）
    ch_map = (merged.get("io") or {}).get("channel_mapping") or merged.get("channel_mapping") or {}
    if ch_map.get("pore"):
        pore_cols = [k for k in ch_map["pore"] if k in pore_m.columns]
        if pore_cols:
            pore_m = pore_m[pore_cols].copy()
    if ch_map.get("laser"):
        laser_cols = [k for k in ch_map["laser"] if k in laser_m.columns]
        if laser_cols:
            laser_m = laser_m[laser_cols].copy()
    # 間隙水圧: mm 単位で 0–160 mm、50/100/150 mm に補助線
    pore_mm = pore_m * 1000.0
    plotting.save_timeseries_chart(
        pore_mm, fig_pore, merged,
        title=case_id,
        y_label="Pressure head (mm)",
        ylim=[0, 160],
        hlines=[50, 100, 150],
    )
    plotting.save_timeseries_chart(
        laser_m, fig_laser, merged,
        title=case_id,
        y_label="Displacement (m)",
        ylim=[-0.15, 0.05],
    )
    # 動水勾配: (換算値(m) - 0.05) / 距離(m)。pore_m はドリフト補正・フィルタ適用済み（process でその順に処理済み）
    lengths = (merged.get("io") or {}).get("hydraulic_gradient_lengths") or {"P1": 0.005, "P2": 0.05, "P3": 0.1, "P4": 0.2}
    gradient = pore_m.copy()
    for col in gradient.columns:
        if col in lengths:
            gradient[col] = (pore_m[col] - 0.05) / lengths[col]
    plotting.save_timeseries_chart(
        gradient, fig_hydraulic, merged,
        title=case_id,
        y_label="Hydraulic gradient",
        ylim=[-20, 20],
    )

    generated = [fig_pore, fig_laser, fig_hydraulic, config_used_path]
    log.info(f"生成ファイル: {[str(p) for p in generated]}")
    finished = datetime.now(timezone.utc).isoformat()
    log.info(f"終了: {finished}")
    if verbose:
        print(f"[pipeline] 生成したファイル: {[str(p) for p in generated]}")
        print(f"[pipeline] 終了: case_id = {case_id}")
    return generated


def run_all(
    base_path: str | Path | None = None,
    glob_pattern: str | None = None,
    *,
    base_config: dict[str, Any] | None = None,
    paths: dict[str, Path] | None = None,
    dry_run: bool = False,
    overwrite: bool = True,
    cases_dir_override: Path | None = None,
) -> list[str]:
    """
    case 指定なしで data_dir 内の全 CSV を処理。
    base_config/paths を渡すと load_base を省略（Notebook 等で利用）。
    対象 CSV が 0 件の場合は FileNotFoundError（終了コード 3 想定）。
    """
    if base_config is None or paths is None:
        base_config, paths = config.load_base(base_path, cases_dir_override)
        env.print_startup(paths)
    pattern = glob_pattern or (base_config.get("io") or {}).get("discover", "*.csv")
    case_ids = discover_cases(paths["data_dir"], pattern)
    data_dir = paths["data_dir"]
    cases_dir = paths.get("cases_dir") or (paths["params_dir"] / "cases")

    if not case_ids:
        raise FileNotFoundError(
            f"処理対象の CSV がありません: data_dir={data_dir} | glob={pattern} | "
            "data/ に該当ファイルを置くか --case で1件指定してください"
        )

    if dry_run:
        for cid in case_ids:
            csv_p = data_dir / f"{cid}.csv"
            out_d = paths["output_dir"] / cid
            case_yml = cases_dir / f"{cid}.yaml"
            print(f"[dry-run] case_id={cid} | 入力={csv_p} | 出力={out_d} | case.yaml={'あり' if case_yml.exists() else 'なし'}")
        return case_ids

    n = len(case_ids)
    for i, cid in enumerate(case_ids, 1):
        run_case(cid, base_config=base_config, paths=paths, overwrite=overwrite, verbose=False)
        print(f"ケース {cid} 終了（{i}/{n}）")
    return case_ids
