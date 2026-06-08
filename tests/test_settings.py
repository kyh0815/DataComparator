"""T0-3 설정 로더 단위 테스트.

정상/이상 케이스를 커버한다: 정상 로드·기본값·shells(range/ids/우선순위)·
경로 해석·비밀번호 환경변수·필수 키 누락·파일 없음·YAML 오류.
"""

from pathlib import Path

import pytest

from src.config.settings import ConfigError, load_config

_FULL_YAML = """
encoding: Shift_JIS
paths:
  asis_input_dir: ./samples/asis/input
  asis_output_dir: ./samples/asis/output
  tobe_output_dir: ./out/tobe_output
  report_dir: ./out/reports
database:
  host: localhost
  port: 5432
  dbname: compare_proto
  user: postgres
  password_env: TEST_PG_PW
batch:
  type: stub
  stub_path: ./stub_batch/run_batch.py
  timeout_seconds: 60
shells:
  range: [1, 10]
output:
  cli_color: true
  cli_verbose: false
  report_with_bom: true
"""


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "config.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_load_full_config(tmp_path, monkeypatch):
    """완전한 config를 로드 → 모든 필드 정확, 비밀번호 환경변수 해석."""
    monkeypatch.setenv("TEST_PG_PW", "secret123")
    cfg = load_config(_write(tmp_path, _FULL_YAML))

    assert cfg.encoding == "Shift_JIS"
    assert cfg.database.dbname == "compare_proto"
    assert cfg.database.port == 5432
    assert cfg.database.password == "secret123"
    assert cfg.database.password_env == "TEST_PG_PW"
    assert cfg.batch.type == "stub"
    assert cfg.batch.timeout_seconds == 60
    assert cfg.output.report_with_bom is True
    # range [1,10] inclusive → 10개, 3자리 zero-pad
    assert cfg.shell_ids == [f"{n:03d}" for n in range(1, 11)]


def test_relative_paths_resolved_against_config_dir(tmp_path):
    """상대경로는 config 파일 위치 기준으로 절대경로화된다."""
    cfg = load_config(_write(tmp_path, _FULL_YAML))
    assert cfg.asis_input_dir.is_absolute()
    assert cfg.asis_input_dir == (tmp_path / "samples/asis/input").resolve()
    assert cfg.batch.stub_path == (tmp_path / "stub_batch/run_batch.py").resolve()


def test_shells_ids_beats_range(tmp_path):
    """ids와 range가 둘 다 있으면 ids 우선 (구체 > 일반)."""
    text = _FULL_YAML.replace("  range: [1, 10]", '  range: [1, 10]\n  ids: ["001", "003", 7]')
    cfg = load_config(_write(tmp_path, text))
    # 정수 7도 3자리 zero-pad로 정규화
    assert cfg.shell_ids == ["001", "003", "007"]


def test_defaults_applied_when_optional_blocks_missing(tmp_path, monkeypatch):
    """encoding/shells/batch/output 누락 시 기본값 적용. password 없으면 None."""
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
    text = """
paths:
  asis_input_dir: ./a
  asis_output_dir: ./b
  tobe_output_dir: ./c
  report_dir: ./d
database:
  host: localhost
  port: 5432
  dbname: db
  user: postgres
"""
    cfg = load_config(_write(tmp_path, text))
    assert cfg.encoding == "Shift_JIS"               # 기본값
    assert cfg.shell_ids == [f"{n:03d}" for n in range(1, 11)]  # 기본 range
    assert cfg.batch.type == "stub"                  # dataclass 기본값
    assert cfg.output.cli_color is True
    assert cfg.database.password is None             # 환경변수 미설정 → None (예외 아님)
    assert cfg.database.password_env == "POSTGRES_PASSWORD"


def test_missing_paths_block_raises(tmp_path):
    """필수 blocks 'paths' 누락 → ConfigError."""
    text = "\n".join(
        line for line in _FULL_YAML.splitlines() if "dir:" not in line and line.strip() != "paths:"
    )
    with pytest.raises(ConfigError, match="paths"):
        load_config(_write(tmp_path, text))


def test_missing_database_key_raises(tmp_path):
    """database 필수 키(dbname) 누락 → ConfigError."""
    text = _FULL_YAML.replace("  dbname: compare_proto\n", "")
    with pytest.raises(ConfigError, match="dbname"):
        load_config(_write(tmp_path, text))


def test_file_not_found_raises(tmp_path):
    """존재하지 않는 경로 → ConfigError."""
    with pytest.raises(ConfigError, match="찾을 수 없"):
        load_config(tmp_path / "nope.yaml")


def test_invalid_yaml_raises(tmp_path):
    """깨진 YAML → ConfigError."""
    with pytest.raises(ConfigError):
        load_config(_write(tmp_path, "paths: [unclosed\n  : :"))


def test_range_inclusive_and_reversed_rejected(tmp_path):
    """range는 inclusive, 시작 > 끝이면 ConfigError."""
    ok = load_config(_write(tmp_path, _FULL_YAML.replace("  range: [1, 10]", "  range: [3, 5]")))
    assert ok.shell_ids == ["003", "004", "005"]

    with pytest.raises(ConfigError, match="range"):
        load_config(_write(tmp_path, _FULL_YAML.replace("  range: [1, 10]", "  range: [9, 2]")))


# --- B: batch.groups(업무별 배치 환경) -------------------------------------------

_GROUPS_YAML = _FULL_YAML.replace(
    "batch:\n  type: stub\n  stub_path: ./stub_batch/run_batch.py\n  timeout_seconds: 60\n",
    "batch:\n  type: stub\n  success_exit_code: 0\n  env: { POSTGRES_PASSWORD: gpw }\n"
    "  groups:\n"
    "    業務A: { base_dir: ./mock/A }\n"
    '    業務B: { base_dir: /abs/B, success_exit_code: 3, env: { X: "y" } }\n',
)


def test_batch_groups_parsed_with_inheritance(tmp_path):
    """batch.groups: base_dir 그룹 필수, env/success_exit_code는 비면 batch 전역 상속(B-Q2)."""
    g = load_config(_write(tmp_path, _GROUPS_YAML)).batch.groups
    assert set(g) == {"業務A", "業務B"}
    assert g["業務A"].success_exit_code == 0                       # 상속(전역 0)
    assert g["業務A"].env == {"POSTGRES_PASSWORD": "gpw"}          # 상속(전역 env)
    assert g["業務A"].base_dir == (tmp_path / "mock/A").resolve()  # 상대→config 기준 절대화
    assert g["業務B"].success_exit_code == 3                       # override
    assert g["業務B"].env == {"X": "y"}                            # override
    assert g["業務B"].base_dir == Path("/abs/B")                   # 절대경로 그대로


def test_batch_groups_absent_is_empty(tmp_path):
    """groups 미지정이면 빈 dict(하위호환)."""
    assert load_config(_write(tmp_path, _FULL_YAML)).batch.groups == {}


def test_batch_group_missing_base_dir_errors(tmp_path):
    """그룹에 base_dir 없으면 ConfigError(base_dir만 그룹 필수)."""
    bad = _GROUPS_YAML.replace("業務A: { base_dir: ./mock/A }", "業務A: { env: {} }")
    with pytest.raises(ConfigError, match="base_dir"):
        load_config(_write(tmp_path, bad))


def test_batch_group_data_dirs_parsed(tmp_path):
    """batch.groups[업무]의 업무별 데이터 디렉토리 파싱·절대화(D-044, 3단계 폴백 중간층)."""
    y = _GROUPS_YAML.replace(
        "業務A: { base_dir: ./mock/A }",
        "業務A: { base_dir: ./mock/A, asis_input_dir: ./A/asis/in, tobe_output_dir: /abs/A/tobe }",
    )
    g = load_config(_write(tmp_path, y)).batch.groups["業務A"]
    assert g.asis_input_dir == (tmp_path / "A/asis/in").resolve()   # 상대 → config 기준 절대화
    assert g.tobe_output_dir == Path("/abs/A/tobe")                  # 절대 그대로
    assert g.asis_output_dir is None                                 # 미지정 → None(전역 폴백)


def test_apply_group_dirs_three_level_priority():
    """경로 폴백: 항목 override > 업무 그룹 dir > 전역(미설정). 항목 override는 불변(D-044)."""
    from src.core.models import (BatchConfig, BatchGroup, Config, DatabaseConfig,
                                  InputSpec, OutputConfig, OutputSpec, ShellDefinition)
    from src.core.paths import apply_group_dirs

    group = BatchGroup(base_dir=Path("/g"), asis_input_dir=Path("/g/asis/in"),
                       asis_output_dir=Path("/g/asis/out"), tobe_output_dir=Path("/g/tobe/out"))
    cfg = Config(
        encoding="shift_jis", asis_input_dir=Path("/G/in"), asis_output_dir=Path("/G/out"),
        tobe_output_dir=Path("/G/tobe"), report_dir=Path("/r"),
        database=DatabaseConfig(host="h", port=1, dbname="d", user="u"),
        batch=BatchConfig(groups={"業務A": group}), shell_ids=["001"], output=OutputConfig(),
    )
    d = ShellDefinition(
        test_id="001", test_name="t", input_type="file", input_csv="in.csv",
        output_type="file", expected_output_csv="exp.dat", shell_program="x.sh", shell_group="業務A",
        inputs=[InputSpec(csv="a.csv", type="file"),                       # override 없음 → 그룹
                InputSpec(csv="b.csv", type="file", src_dir="/item/in")],  # 항목 override 우선
        outputs=[OutputSpec(type="file", expected="exp.dat", file="out.dat")],
    )
    apply_group_dirs(d, cfg)
    assert d.inputs[0].src_dir == "/g/asis/in"        # 빈칸 → 그룹
    assert d.inputs[1].src_dir == "/item/in"          # 항목 override 우선(불변)
    assert d.outputs[0].expected_dir == "/g/asis/out" # 빈칸 → 그룹
    assert d.outputs[0].tobe_dir == "/g/tobe/out"
    assert d.inputs[0].dest_dir is None               # 그룹에 tobe_input_dir 없음 → None(전역 폴백)
