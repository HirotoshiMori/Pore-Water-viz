"""config merge と validate のテスト。"""

from pathlib import Path

import pytest

from poreviz import config


def test_merge_base_only() -> None:
    base = {"a": 1, "b": {"x": 10}}
    assert config.merge(base, None) == {"a": 1, "b": {"x": 10}}
    assert config.merge(base, {}) == {"a": 1, "b": {"x": 10}}


def test_merge_case_overwrites_scalar() -> None:
    base = {"a": 1, "b": 2}
    case = {"a": 99}
    got = config.merge(base, case)
    assert got["a"] == 99
    assert got["b"] == 2


def test_merge_case_overwrites_nested() -> None:
    base = {"plot_style": {"figure": {"dpi": 150}, "fonts": {"title": 14}}}
    case = {"plot_style": {"figure": {"dpi": 200}}}
    got = config.merge(base, case)
    assert got["plot_style"]["figure"]["dpi"] == 200
    assert got["plot_style"]["fonts"]["title"] == 14


def test_merge_list_is_replaced() -> None:
    base = {"items": [1, 2, 3]}
    case = {"items": [9]}
    got = config.merge(base, case)
    assert got["items"] == [9]


def test_validate_base_ok() -> None:
    base = {
        "project": {"paths": {"local": {"root": ".", "data_dir": "./data", "params_dir": "./params", "output_dir": "./output"},
                              "colab": {"root": "/c", "data_dir": "/c/data", "params_dir": "/c/params", "output_dir": "/c/output"}}},
        "io": {"encoding": "utf-8"},
        "plot_style": {"figure": {"dpi": 100, "aspect": {"mode": "width_height", "width_in": 6, "height_in": 4}},
                      "fonts": {"title": 12, "axis_label": 10, "legend": 9}},
    }
    config.validate_base(base)


def test_validate_base_missing_paths_raises() -> None:
    base = {"project": {"paths": {}}, "io": {"encoding": "utf-8"}, "plot_style": {}}
    with pytest.raises(ValueError, match="project.paths"):
        config.validate_base(base)


def test_validate_base_missing_plot_style_fonts_raises() -> None:
    base = {
        "project": {"paths": {"local": {"root": ".", "data_dir": ".", "params_dir": ".", "output_dir": "."},
                              "colab": {"root": ".", "data_dir": ".", "params_dir": ".", "output_dir": "."}}},
        "io": {"encoding": "utf-8"},
        "plot_style": {"figure": {"dpi": 100, "aspect": {"mode": "width_height", "width_in": 6, "height_in": 4}}, "fonts": {}},
    }
    with pytest.raises(ValueError, match="fonts"):
        config.validate_base(base)


def test_validate_case_accepts_empty() -> None:
    config.validate_case({})


def test_validate_case_accepts_dict_keys() -> None:
    config.validate_case({"channels": {"a": 1}, "geometry": {"b": 2}})


def test_validate_case_accepts_channels_list() -> None:
    config.validate_case({"channels": [1, 2]})


def test_validate_case_raises_on_wrong_type() -> None:
    with pytest.raises(ValueError, match="dict または list"):
        config.validate_case({"channels": "invalid"})
