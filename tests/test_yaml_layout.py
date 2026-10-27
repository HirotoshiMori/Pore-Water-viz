"""yaml は clone 先に残し、既存ファイルは上書きしない。"""

from pathlib import Path

from poreviz.config import ensure_yaml_dir, resolve_case_yaml


def test_resolve_case_yaml_prefers_file_next_to_base(tmp_path: Path) -> None:
    yaml_dir = tmp_path / "yaml"
    cases = yaml_dir / "cases"
    cases.mkdir(parents=True)
    (yaml_dir / "No4.yaml").write_text("flat: true\n", encoding="utf-8")
    (cases / "No4.yaml").write_text("nested: true\n", encoding="utf-8")
    assert resolve_case_yaml(yaml_dir, "No4", cases).name == "No4.yaml"
    assert resolve_case_yaml(yaml_dir, "No4", cases).parent == yaml_dir


def test_ensure_yaml_dir_does_not_overwrite_existing_base(tmp_path: Path) -> None:
    yaml_dir = tmp_path / "yaml"
    yaml_dir.mkdir()
    base = yaml_dir / "base.yaml"
    base.write_text("keep: me\n", encoding="utf-8")
    (yaml_dir / "No4.yaml").write_text("case: mine\n", encoding="utf-8")
    ensure_yaml_dir(tmp_path)
    assert base.read_text(encoding="utf-8") == "keep: me\n"
    assert (yaml_dir / "No4.yaml").read_text(encoding="utf-8") == "case: mine\n"


def test_ensure_yaml_dir_copies_template_when_missing(tmp_path: Path) -> None:
    ensure_yaml_dir(tmp_path)
    assert (tmp_path / "yaml" / "base.yaml").is_file()
    assert "params_dir: \"./yaml\"" in (tmp_path / "yaml" / "base.yaml").read_text(encoding="utf-8")
