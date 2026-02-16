"""discover_cases と run_case 統合（画像サイズ含む）のテスト。"""

from pathlib import Path

import pytest

from poreviz import pipeline


def test_discover_cases_empty_dir(tmp_path: Path) -> None:
    assert pipeline.discover_cases(tmp_path) == []
    assert pipeline.discover_cases(tmp_path, "*.csv") == []


def test_discover_cases_finds_csv_and_stem(test_root: Path) -> None:
    data_dir = test_root / "data"
    case_ids = pipeline.discover_cases(data_dir, "*.csv")
    assert case_ids == ["minimal"]
    assert len(case_ids) == 1


def test_discover_cases_glob_filter(test_root: Path) -> None:
    data_dir = test_root / "data"
    (data_dir / "other.txt").write_text("x")
    case_ids = pipeline.discover_cases(data_dir, "*.csv")
    assert case_ids == ["minimal"]


def test_run_case_produces_figures_and_config_used(
    mock_paths_from_root: Path,
) -> None:
    """run_case で figures/*.png と logs/config_used.yml が生成される。"""
    root = mock_paths_from_root
    base_path = root / "params" / "base_test.yaml"
    from poreviz import config
    base_cfg, paths = config.load_base(base_path, root / "params" / "cases")
    # print 抑制のため env.print_startup を noop に
    import poreviz.env as env_module
    env_module.print_startup = lambda p: None
    pipeline.run_case("minimal", base_config=base_cfg, paths=paths)
    out = root / "output" / "minimal"
    assert (out / "figures" / "line_chart.png").exists()
    assert (out / "logs" / "config_used.yml").exists()


def test_run_case_image_size_within_tolerance(
    mock_paths_from_root: Path,
) -> None:
    """画像サイズが width_in*dpi, height_in*dpi の ±2px である。"""
    from PIL import Image
    root = mock_paths_from_root
    base_path = root / "params" / "base_test.yaml"
    from poreviz import config
    base_cfg, paths = config.load_base(base_path, root / "params" / "cases")
    import poreviz.env as env_module
    env_module.print_startup = lambda p: None
    pipeline.run_case("minimal", base_config=base_cfg, paths=paths)
    img_path = root / "output" / "minimal" / "figures" / "line_chart.png"
    with Image.open(img_path) as im:
        w, h = im.size
    # base_test.yaml: width_in=6, height_in=4, dpi=100
    expected_w = 600
    expected_h = 400
    tol = 2
    assert abs(w - expected_w) <= tol, f"width {w} not in {expected_w}±{tol}"
    assert abs(h - expected_h) <= tol, f"height {h} not in {expected_h}±{tol}"


def test_run_case_missing_csv_raises(mock_paths_from_root: Path) -> None:
    root = mock_paths_from_root
    base_path = root / "params" / "base_test.yaml"
    from poreviz import config
    base_cfg, paths = config.load_base(base_path, root / "params" / "cases")
    with pytest.raises(FileNotFoundError, match="データファイル"):
        pipeline.run_case("nonexistent", base_config=base_cfg, paths=paths)
