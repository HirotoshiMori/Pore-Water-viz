"""env 判定のテスト（Colab 判定をモック）。"""

import pytest


def test_get_environment_returns_local_when_mocked(mock_env_local: str) -> None:
    from poreviz import env
    assert env.get_environment() == "local"
    assert env.get_environment(silent=True) == "local"


def test_get_environment_returns_colab_when_mocked(mock_env_colab: str) -> None:
    from poreviz import env
    assert env.get_environment() == "colab"
    assert env.get_environment(silent=True) == "colab"


def test_get_paths_has_required_keys(mock_env_local: str) -> None:
    from poreviz import env
    paths = env.get_paths("local")
    assert "root" in paths
    assert "data_dir" in paths
    assert "params_dir" in paths
    assert "output_dir" in paths


def test_get_paths_local_uses_cwd(mock_env_local: str) -> None:
    from pathlib import Path
    from poreviz import env
    paths = env.get_paths("local")
    assert paths["data_dir"] == (Path.cwd() / "data").resolve()
    assert paths["params_dir"] == (Path.cwd() / "yaml").resolve()
    assert paths["output_dir"] == (Path.cwd() / "output").resolve()


def test_get_paths_colab_uses_content(mock_env_colab: str) -> None:
    from pathlib import Path
    from poreviz import env
    paths = env.get_paths("colab")
    assert paths["root"] == Path("/content").resolve()
    assert "content" in str(paths["data_dir"])
