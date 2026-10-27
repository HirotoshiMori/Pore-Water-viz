"""
Phase 3 CLI: run / list / validate / doctor
終了コード: 0 成功, 1 用法, 2 config, 3 io, 4 processing
"""

import sys
from pathlib import Path

import typer

from . import config, env, pipeline

app = typer.Typer(help="間隙水圧計図化（Phase 3）")


def _resolve_base_path(base_path: str | None) -> Path:
    if base_path:
        return Path(base_path).resolve()
    paths = env.get_paths(env.get_environment(silent=True))
    return paths["params_dir"] / "base.yaml"


def _resolve_cases_dir(cases_dir: str | None, base_path: str | None) -> Path | None:
    if cases_dir:
        return Path(cases_dir).resolve()
    return None


@app.command()
def run(
    case_id: str | None = typer.Option(None, "--case", "-c", help="ケースID（省略時は全CSV）"),
    base_path: str | None = typer.Option(None, "--base", "-b", help="base.yaml のパス"),
    cases_dir: str | None = typer.Option(None, "--cases-dir", help="cases 用ディレクトリ"),
    dry_run: bool = typer.Option(False, "--dry-run", help="処理せず対象のみ表示"),
    overwrite: bool = typer.Option(True, "--overwrite/--no-overwrite", help="既存出力を上書き（既定: 上書き）。--no-overwrite でスキップ"),
) -> None:
    """図化を実行（1ケースまたは全件）。"""
    cases_dir_path = _resolve_cases_dir(cases_dir, base_path)
    try:
        if case_id:
            pipeline.run_case(
                case_id,
                base_path,
                dry_run=dry_run,
                overwrite=overwrite,
                cases_dir_override=cases_dir_path,
            )
        else:
            pipeline.run_all(
                base_path,
                dry_run=dry_run,
                overwrite=overwrite,
                cases_dir_override=cases_dir_path,
            )
    except ValueError as e:
        msg = str(e)
        if "tokenizing" in msg or "Expected" in msg or "saw " in msg:
            typer.echo(f"エラー(processing): {e}", err=True)
            raise typer.Exit(4)
        typer.echo(f"エラー(config): {e}", err=True)
        raise typer.Exit(2)
    except FileNotFoundError as e:
        msg = str(e)
        if "base.yaml" in msg or "yaml" in msg:
            typer.echo(f"エラー(config): {e}", err=True)
            raise typer.Exit(2)
        typer.echo(f"エラー(io): {e}", err=True)
        raise typer.Exit(3)
    except Exception as e:
        typer.echo(f"エラー(processing): {e}", err=True)
        raise typer.Exit(4)


@app.command("list")
def list_cmd(
    data_dir: str | None = typer.Option(None, "--data-dir", "-d", help="data ディレクトリ"),
    glob: str = typer.Option("*.csv", "--glob", "-g", help="CSV の glob パターン"),
) -> None:
    """data_dir 内の CSV から case_id 一覧を表示。"""
    if data_dir:
        data_path = Path(data_dir).resolve()
    else:
        env_type = env.get_environment(silent=True)
        paths = env.get_paths(env_type)
        data_path = paths["data_dir"]
    if not data_path.exists():
        typer.echo(f"data_dir が存在しません: {data_path}", err=True)
        raise typer.Exit(3)
    case_ids = pipeline.discover_cases(data_path, glob)
    typer.echo(f"data_dir={data_path} | glob={glob} | 件数={len(case_ids)}")
    for cid in case_ids:
        typer.echo(cid)


@app.command()
def validate(
    case_id: str | None = typer.Option(None, "--case", "-c", help="検証するケース（省略時は全ケース）"),
    base_path: str | None = typer.Option(None, "--base", "-b", help="base.yaml のパス"),
    cases_dir: str | None = typer.Option(None, "--cases-dir", help="cases 用ディレクトリ"),
) -> None:
    """設定とファイル存在を検査（実行しない）。"""
    cases_dir_path = _resolve_cases_dir(cases_dir, base_path)
    try:
        base_cfg, paths = config.load_base(base_path, cases_dir_path)
        base_resolved = _resolve_base_path(base_path)
        cases_d = paths.get("cases_dir") or (paths["params_dir"] / "cases")
        pattern = (base_cfg.get("io") or {}).get("discover", "*.csv")
        if case_id:
            case_ids = [case_id]
        else:
            case_ids = pipeline.discover_cases(paths["data_dir"], pattern)
        typer.echo(f"base.yaml: {base_resolved} OK")
        for cid in case_ids:
            csv_p = paths["data_dir"] / f"{cid}.csv"
            case_yml = config.resolve_case_yaml(paths["params_dir"], cid, cases_d)
            if not csv_p.exists():
                typer.echo(f"  {cid}: 入力CSV なし {csv_p}", err=True)
                raise typer.Exit(3)
            case_cfg = config.load_case(case_yml)
            if case_cfg:
                config.validate_case(case_cfg)
            merged = config.merge(base_cfg, case_cfg)
            config.validate(merged, paths)
            typer.echo(f"  {cid}: OK (case.yaml={'あり' if case_yml.exists() else 'なし'})")
    except ValueError as e:
        typer.echo(f"エラー(config): {e}", err=True)
        raise typer.Exit(2)
    except FileNotFoundError as e:
        typer.echo(f"エラー(io): {e}", err=True)
        raise typer.Exit(3)


@app.command()
def doctor() -> None:
    """環境判定・主要パス・依存バージョンを表示。"""
    env_type = env.get_environment(silent=True)
    paths = env.get_paths(env_type)
    typer.echo(f"ENV: {env_type}")
    typer.echo(f"ROOT: {paths['root']}")
    typer.echo(f"DATA: {paths['data_dir']}")
    typer.echo(f"YAML: {paths['params_dir']}")
    typer.echo(f"OUTPUT: {paths['output_dir']}")
    try:
        import pandas as pd
        typer.echo(f"pandas: {pd.__version__}")
    except Exception:
        typer.echo("pandas: (未インストール)")
    try:
        import matplotlib
        typer.echo(f"matplotlib: {matplotlib.__version__}")
    except Exception:
        typer.echo("matplotlib: (未インストール)")
    try:
        import yaml
        typer.echo(f"PyYAML: {getattr(yaml, '__version__', '?')}")
    except Exception:
        typer.echo("PyYAML: (未インストール)")


def main() -> None:
    app()


if __name__ == "__main__":
    app()
