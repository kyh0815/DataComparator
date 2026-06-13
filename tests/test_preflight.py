"""C3 프리플라이트(dry-run 게이트) 단위 테스트 (HANDOFF_V3 C3, DB 불요).

점검: 정의 무결성(checklist 重複)·정답 파일(존재/0バイト/읽기)·입력 파일·shell 실행파일·
출력 디렉토리 쓰기권한·record key 경고·이름+has_header=false 에러·DB 접속(주입)·문제 일괄 수집.
"""

import os
import sys
from pathlib import Path

import pytest

from src.core.models import (
    BatchConfig,
    Config,
    DatabaseConfig,
    InputSpec,
    OutputConfig,
    OutputSpec,
    ShellDefinition,
)
from src.core.preflight import preflight


def _config(tmp_path: Path) -> Config:
    for sub in ("asis/in", "asis/out", "tobe/out", "tobe/in", "reports"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    return Config(
        encoding="shift_jis",
        asis_input_dir=tmp_path / "asis/in",
        asis_output_dir=tmp_path / "asis/out",
        tobe_output_dir=tmp_path / "tobe/out",
        report_dir=tmp_path / "reports",
        database=DatabaseConfig(host="localhost", port=5432, dbname="x", user="u", password="p"),
        batch=BatchConfig(),
        shell_ids=["001"],
        output=OutputConfig(),
        tobe_input_dir=tmp_path / "tobe/in",
        definition_file=tmp_path / "test_definition.yaml",
    )


def _shell(tmp_path, **out_kw) -> ShellDefinition:
    """clean 케이스 1셸(파일 입력/파일 출력). 입력·정답 파일·shell을 실제로 만든다."""
    (tmp_path / "asis/in").mkdir(parents=True, exist_ok=True)
    (tmp_path / "asis/out").mkdir(parents=True, exist_ok=True)
    (tmp_path / "asis/in/in.csv").write_text("data\n", encoding="utf-8")
    (tmp_path / "asis/out/exp.dat").write_text("golden\n", encoding="utf-8")
    shell = tmp_path / "batch.sh"
    shell.write_text("#!/bin/sh\n", encoding="utf-8")
    shell.chmod(0o755)
    out = OutputSpec(type="file", expected="exp.dat", file="out.dat", **out_kw)
    return ShellDefinition(
        test_id="001",
        test_name="t",
        input_type="file",
        input_csv="in.csv",
        output_type="file",
        expected_output_csv="exp.dat",
        shell_program=str(shell),
        inputs=[InputSpec(csv="in.csv", type="file")],
        outputs=[out],
    )


def _run(tmp_path, definitions):
    return preflight(_config(tmp_path), definitions, connect=lambda db: _FakeConn())


class _FakeConn:
    def close(self):
        pass


# --- clean ----------------------------------------------------------------------


def test_clean_passes(tmp_path):
    """모든 점검 통과 → ok=True, 이슈 0건."""
    r = _run(tmp_path, [_shell(tmp_path)])
    assert r.ok and r.issues == []


# --- 정답 파일 ------------------------------------------------------------------


def test_missing_expected_is_error(tmp_path):
    d = _shell(tmp_path)
    (tmp_path / "asis/out/exp.dat").unlink()  # 정답 삭제
    r = _run(tmp_path, [d])
    assert not r.ok
    assert any("正解ファイルがありません" in i.message for i in r.errors)


def test_zero_byte_expected_is_error(tmp_path):
    d = _shell(tmp_path)
    (tmp_path / "asis/out/exp.dat").write_text("", encoding="utf-8")  # 0バイト
    r = _run(tmp_path, [d])
    assert not r.ok and any("0バイト" in i.message for i in r.errors)


# --- 입력 / shell --------------------------------------------------------------


def test_missing_input_file_is_error(tmp_path):
    d = _shell(tmp_path)
    (tmp_path / "asis/in/in.csv").unlink()
    r = _run(tmp_path, [d])
    assert not r.ok and any("入力ファイルがありません" in i.message for i in r.errors)


def test_missing_shell_program_is_error(tmp_path):
    d = _shell(tmp_path)
    Path(d.shell_program).unlink()
    r = _run(tmp_path, [d])
    assert not r.ok and any("shell 実行ファイルがありません" in i.message for i in r.errors)


# --- 정의 무결성 ----------------------------------------------------------------


def test_duplicate_checklist_is_error(tmp_path):
    d1 = _shell(tmp_path)
    d2 = _shell(tmp_path)  # 같은 test_id "001"
    r = _run(tmp_path, [d1, d2])
    assert not r.ok and any("重複" in i.message and i.coordinate == "001" for i in r.errors)


# --- record 비교 옵션 (key 경고 / 이름+무헤더 에러) ------------------------------


def test_record_without_key_is_warning_not_error(tmp_path):
    """record인데 key 없음 → 경고(실행은 허용)."""
    d = _shell(tmp_path, compare_mode="record")
    r = _run(tmp_path, [d])
    assert r.ok  # 경고뿐이라 통과
    assert any("key がありません" in i.message for i in r.warnings)


def test_named_column_without_header_is_error(tmp_path):
    """has_header=false인데 컬럼명(key=CUST_ID) → 에러."""
    d = _shell(tmp_path, compare_mode="record", key="CUST_ID", has_header=False)
    r = _run(tmp_path, [d])
    assert not r.ok and any("has_header=false" in i.message for i in r.errors)


def test_named_column_with_header_ok(tmp_path):
    """has_header=true면 컬럼명 허용(에러 없음)."""
    d = _shell(tmp_path, compare_mode="record", key="CUST_ID", has_header=True)
    r = _run(tmp_path, [d])
    assert r.ok


# --- 출력 디렉토리 쓰기권한 -----------------------------------------------------


@pytest.mark.skipif(
    sys.platform == "win32" or (os.name == "posix" and os.getuid() == 0),
    reason="POSIX 쓰기권한(chmod) 의미 — Windows는 ACL이라 chmod 미적용, root는 권한 우회",
)
def test_unwritable_output_dir_is_error(tmp_path):
    ro = tmp_path / "readonly_out"
    ro.mkdir()
    ro.chmod(0o500)  # 읽기/실행만, 쓰기 없음
    try:
        d = _shell(tmp_path, tobe_dir=str(ro))
        r = _run(tmp_path, [d])
        assert not r.ok and any("出力ディレクトリに書き込めません" in i.message for i in r.errors)
    finally:
        ro.chmod(0o755)  # 정리(tmp 삭제 가능하게)


# --- DB 접속 --------------------------------------------------------------------


def test_db_connect_failure_is_error(tmp_path):
    """DB 쓰는 셸인데 접속 실패 → 에러 1건."""
    (tmp_path / "asis/in").mkdir(parents=True, exist_ok=True)
    (tmp_path / "asis/out").mkdir(parents=True, exist_ok=True)
    (tmp_path / "asis/in/in.csv").write_text("data\n", encoding="utf-8")
    (tmp_path / "asis/out/exp.dat").write_text("g\n", encoding="utf-8")
    shell = tmp_path / "b.sh"
    shell.write_text("#!/bin/sh\n", encoding="utf-8")
    shell.chmod(0o755)
    d = ShellDefinition(
        test_id="001", test_name="t", input_type="database", input_csv="in.csv",
        output_type="file", expected_output_csv="exp.dat", shell_program=str(shell),
        inputs=[InputSpec(csv="in.csv", type="database", table="T")],
        outputs=[OutputSpec(type="file", expected="exp.dat", file="o.dat")],
    )

    def boom(db):
        raise RuntimeError("connection refused")

    r = preflight(_config(tmp_path), [d], connect=boom)
    assert not r.ok and any("DB 接続に失敗" in i.message and i.coordinate == "DB" for i in r.errors)


def test_db_failure_hints_unset_password_env(tmp_path):
    """비번 env 미설정(password=None)이면 접속 실패 메시지에 env 키 미설정 사실을 1줄 덧붙인다."""
    shell = tmp_path / "batch.sh"
    shell.write_text("#!/bin/sh\n", encoding="utf-8")
    shell.chmod(0o755)
    d = ShellDefinition(
        test_id="001", test_name="t", input_type="database", input_csv="in.csv",
        output_type="file", expected_output_csv="exp.dat", shell_program=str(shell),
        inputs=[InputSpec(csv="in.csv", type="database", table="T")],
        outputs=[OutputSpec(type="file", expected="exp.dat", file="o.dat")],
    )
    config = _config(tmp_path)
    config.database.password = None  # env 미설정 상태 재현
    config.database.password_env = "POSTGRES_PASSWORD"

    def boom(db):
        raise RuntimeError("connection refused")

    r = preflight(config, [d], connect=boom)
    db_errors = [i.message for i in r.errors if i.coordinate == "DB"]
    assert db_errors and "POSTGRES_PASSWORD" in db_errors[0] and "設定されていません" in db_errors[0]


def test_db_not_called_when_no_db(tmp_path):
    """파일 전용 셸이면 DB 접속을 시도하지 않는다(connect 미호출)."""
    called = []
    preflight(_config(tmp_path), [_shell(tmp_path)], connect=lambda db: called.append(1))
    assert called == []


# --- 일괄 수집(첫 에러에서 멈추지 않음) -----------------------------------------


def test_collects_all_problems_not_first(tmp_path):
    """여러 문제를 한 번에 모은다(부분 보고 = 통과 착시 차단)."""
    d = _shell(tmp_path, compare_mode="record", key="NAME", has_header=False)
    (tmp_path / "asis/out/exp.dat").unlink()   # 정답 없음
    (tmp_path / "asis/in/in.csv").unlink()     # 입력 없음
    Path(d.shell_program).unlink()             # shell 없음
    r = _run(tmp_path, [d])
    msgs = " | ".join(i.message for i in r.errors)
    assert "正解ファイルがありません" in msgs
    assert "入力ファイルがありません" in msgs
    assert "shell 実行ファイルがありません" in msgs
    assert "has_header=false" in msgs
    assert len(r.errors) >= 4  # 첫 에러에서 멈췄다면 1건뿐이었을 것


# --- B: shell_group lint(멤버십·모호성=config-only / 셸 위치=FS) -------------------

from src.core.models import BatchGroup  # noqa: E402
from src.core.preflight import _check_shell_group  # noqa: E402


def _cfg_groups(tmp_path, groups):
    cfg = _config(tmp_path)
    cfg.batch.groups = groups
    return cfg


def _def_group(test_id, shell_group, shell_program):
    return ShellDefinition(
        test_id=test_id, test_name="t",
        input_type="file", input_csv="in.csv",
        output_type="file", expected_output_csv="exp.dat",
        shell_program=shell_program, shell_group=shell_group,
        inputs=[InputSpec(csv="in.csv", type="file")],
        outputs=[OutputSpec(type="file", expected="exp.dat", file="out.dat")],
    )


def test_shell_group_undefined_is_error(tmp_path):
    """선언한 shell_group이 batch.groups에 없으면 error(멤버십, config-only)."""
    cfg = _cfg_groups(tmp_path, {"業務A": BatchGroup(base_dir=tmp_path / "A")})
    issues = []
    _check_shell_group(_def_group("001", "業務X", str(tmp_path / "A/ck.sh")), cfg, issues)
    assert len(issues) == 1 and issues[0].level == "error"
    assert "定義されていません" in issues[0].message


def test_shell_group_empty_with_multiple_groups_warns(tmp_path):
    """그룹이 여러 개인데 태그가 비면 모호 경고(config-only)."""
    cfg = _cfg_groups(tmp_path, {
        "業務A": BatchGroup(base_dir=tmp_path / "A"),
        "業務B": BatchGroup(base_dir=tmp_path / "B"),
    })
    issues = []
    _check_shell_group(_def_group("001", None, str(tmp_path / "x.sh")), cfg, issues)
    assert len(issues) == 1 and issues[0].level == "warning"


def test_shell_group_valid_under_group_dir_ok(tmp_path):
    """유효 그룹 + 셸이 그 디렉토리 配下 → 이슈 없음."""
    (tmp_path / "A").mkdir()
    shell = tmp_path / "A/ck.sh"
    shell.write_text("#!/bin/sh\n", encoding="utf-8")
    cfg = _cfg_groups(tmp_path, {"業務A": BatchGroup(base_dir=tmp_path / "A")})
    issues = []
    _check_shell_group(_def_group("001", "業務A", str(shell)), cfg, issues)
    assert issues == []


def test_shell_group_shell_outside_group_dir_warns(tmp_path):
    """유효 그룹이지만 셸이 그 디렉토리 밖 → 위치 경고(FS)."""
    (tmp_path / "A").mkdir()
    shell = tmp_path / "elsewhere.sh"
    shell.write_text("#!/bin/sh\n", encoding="utf-8")
    cfg = _cfg_groups(tmp_path, {"業務A": BatchGroup(base_dir=tmp_path / "A")})
    issues = []
    _check_shell_group(_def_group("001", "業務A", str(shell)), cfg, issues)
    assert len(issues) == 1 and issues[0].level == "warning"
    assert "配下にありません" in issues[0].message


def test_shell_group_none_single_group_no_issue(tmp_path):
    """그룹 1개 + 태그 없음 → 모호하지 않음(현행 동작, 하위호환)."""
    cfg = _cfg_groups(tmp_path, {"業務A": BatchGroup(base_dir=tmp_path / "A")})
    issues = []
    _check_shell_group(_def_group("001", None, str(tmp_path / "x.sh")), cfg, issues)
    assert issues == []
