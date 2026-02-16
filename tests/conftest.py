"""共通フィクスチャ: テスト用ディレクトリと env モック。"""

from pathlib import Path

import pytest


@pytest.fixture
def test_root(tmp_path: Path) -> Path:
    """tmp_path に data/params/output と minimal.csv, base_test.yaml を用意する。"""
    data_dir = tmp_path / "data"
    params_dir = tmp_path / "params"
    output_dir = tmp_path / "output"
    data_dir.mkdir()
    params_dir.mkdir()
    output_dir.mkdir()
    # 最小CSV
    src_csv = Path(__file__).parent / "data" / "minimal.csv"
    (data_dir / "minimal.csv").write_text(src_csv.read_text(encoding="utf-8"), encoding="utf-8")
    # テスト用 base
    src_base = Path(__file__).parent / "params" / "base_test.yaml"
    (params_dir / "base_test.yaml").write_text(src_base.read_text(encoding="utf-8"), encoding="utf-8")
    (params_dir / "cases").mkdir(exist_ok=True)
    return tmp_path


@pytest.fixture
def mock_env_local(monkeypatch: pytest.MonkeyPatch):
    """get_environment を local に固定。"""
    import poreviz.env as env_module
    monkeypatch.setattr(env_module, "get_environment", lambda silent=False: "local")
    return "local"


@pytest.fixture
def mock_env_colab(monkeypatch: pytest.MonkeyPatch):
    """get_environment を colab に固定。"""
    import poreviz.env as env_module
    monkeypatch.setattr(env_module, "get_environment", lambda silent=False: "colab")
    return "colab"


@pytest.fixture
def mock_paths_from_root(test_root: Path, monkeypatch: pytest.MonkeyPatch):
    """get_paths が test_root 基準のパスを返すようにする。"""
    root = test_root.resolve()

    def _get_paths(env: str | None = None):
        return {
            "root": root,
            "data_dir": (root / "data").resolve(),
            "params_dir": (root / "params").resolve(),
            "output_dir": (root / "output").resolve(),
            "cases_dir": (root / "params" / "cases").resolve(),
        }

    import poreviz.env as env_module
    monkeypatch.setattr(env_module, "get_paths", _get_paths)
    monkeypatch.setattr(env_module, "get_environment", lambda silent=False: "local")
    return test_root
