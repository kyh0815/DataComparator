"""경로 해석 헬퍼(paths.py) 단위 테스트 — config 공통 + 항목별 override (D-036). DB 의존 0."""

from pathlib import Path

import pytest

from src.core.models import (
    BatchConfig,
    Config,
    DatabaseConfig,
    InputSpec,
    OutputConfig,
    OutputSpec,
)
from src.core import paths


def _config(tmp_path):
    return Config(
        encoding="Shift_JIS",
        asis_input_dir=tmp_path / "asis/input",
        asis_output_dir=tmp_path / "asis/output",
        tobe_output_dir=tmp_path / "tobe/output",
        report_dir=tmp_path / "reports",
        database=DatabaseConfig(host="h", port=1, dbname="d", user="u", password="p"),
        batch=BatchConfig(),
        shell_ids=["001"],
        output=OutputConfig(),
        tobe_input_dir=tmp_path / "tobe/input",
        definition_file=tmp_path / "def.yaml",
    )


def test_input_source_falls_back_to_config(tmp_path):
    cfg = _config(tmp_path)
    spec = InputSpec(csv="001.csv", type="file")
    assert paths.input_source_path(spec, cfg) == cfg.asis_input_dir / "001.csv"


def test_input_source_override(tmp_path):
    cfg = _config(tmp_path)
    ovr = tmp_path / "ovr_asis"  # ★OS-무관 절대경로(POSIX /mnt는 Windows서 드라이브가 붙음)
    spec = InputSpec(csv="001.csv", type="file", src_dir=str(ovr))
    assert paths.input_source_path(spec, cfg) == ovr / "001.csv"


def test_input_dest_override_and_rename(tmp_path):
    cfg = _config(tmp_path)
    ovr = tmp_path / "ovr_in"
    spec = InputSpec(csv="001.csv", type="file", dest_dir=str(ovr), dest_name="staged.csv")
    assert paths.input_dest_path(spec, cfg) == ovr / "staged.csv"


def test_input_dest_defaults_keep_name(tmp_path):
    cfg = _config(tmp_path)
    spec = InputSpec(csv="001.csv", type="file")
    assert paths.input_dest_path(spec, cfg) == cfg.tobe_input_dir / "001.csv"


def test_input_dest_missing_dir_raises(tmp_path):
    cfg = _config(tmp_path)
    cfg.tobe_input_dir = None
    spec = InputSpec(csv="001.csv", type="file")  # dest_dir도 없음
    with pytest.raises(ValueError):
        paths.input_dest_dir(spec, cfg)


def test_output_asis_override(tmp_path):
    cfg = _config(tmp_path)
    ovr = tmp_path / "ovr_gold"
    out = OutputSpec(type="file", expected="gold.dat", file="o.dat", expected_dir=str(ovr))
    assert paths.output_asis_path(out, cfg) == ovr / "gold.dat"


def test_output_tobe_override_creates_parent(tmp_path):
    cfg = _config(tmp_path)
    out = OutputSpec(type="file", expected="g.dat", file="o.dat", tobe_dir=str(tmp_path / "custom"))
    p = paths.output_tobe_path(out, cfg)
    assert p == tmp_path / "custom" / "o.dat"
    assert p.parent.is_dir()  # 부모 디렉토리 생성


def test_output_tobe_default(tmp_path):
    cfg = _config(tmp_path)
    out = OutputSpec(type="database", expected="g.csv", table="t", export_as="o.csv")
    assert paths.output_tobe_path(out, cfg) == cfg.tobe_output_dir / "o.csv"
