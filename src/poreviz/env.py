"""実行環境の判定（local / colab）とデフォルトパス。"""

from pathlib import Path


def get_environment(silent: bool = False) -> str:
    """
    local または colab を判定する。
    優先: 環境変数 COLAB_GPU → google.colab の import → local。
    silent=True のときは print しない（ログ用）。
    """
    import os
    if os.environ.get("COLAB_GPU") is not None:
        e = "colab"
    else:
        try:
            import google.colab  # noqa: F401
            e = "colab"
        except ImportError:
            e = "local"
    if not silent:
        print(f"[env] ENV: {e}")
    return e


def get_paths(env: str | None = None) -> dict[str, Path]:
    """
    環境に応じたデフォルトパスを返す（絶対パス）。
    config.load_base 内で base.yaml の project.paths で上書きする。
    環境変数 POREVIZ_WORK が設定されているときは、そのパスを「作業フォルダ」の root とする
    （ノート・モジュールがあるフォルダと data/params/output を別にしたいときに使う）。
    """
    import os
    work = os.environ.get("POREVIZ_WORK")
    if work:
        root = Path(work).resolve()
    else:
        # 未設定ならカレントディレクトリを root とする（Colab ではノート側で chdir(作業フォルダ) している想定）
        root = Path.cwd().resolve()
    return {
        "root": root,
        "data_dir": (root / "data").resolve(),
        "params_dir": (root / "params").resolve(),
        "output_dir": (root / "output").resolve(),
    }


def print_startup(paths: dict[str, Path]) -> None:
    """起動時に ROOT / DATA / OUTPUT を print する。ENV は get_environment() で既に出力済み。"""
    print(f"[env] ROOT: {paths['root']}")
    print(f"[env] DATA: {paths['data_dir']}")
    print(f"[env] OUTPUT: {paths['output_dir']}")
