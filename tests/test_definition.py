"""T2-3 정의 파일 파서(load_definitions) 단위 테스트 — 항상 실행(DB 의존 0)."""

from pathlib import Path

import pytest

from src.config.definition import DefinitionError, load_definitions

_VALID = """
tests:
  - test_id: 1
    test_name: "결제 - DB입력/DB출력"
    input:   { type: database, table: transaction_log, csv: 001.csv }
    execution: { shell_program: stub_batch/run_batch_db.py, timeout: 30 }
    output:  { type: database, table: tobe_result, export_csv: 001.csv }
    expected_output_csv: 001.csv
  - test_id: "006"
    test_name: "야간배치 - 파일입력/파일출력"
    input:   { type: file, dest_dir: ./out/tobe_input/, csv: 006.csv }
    execution: { shell_program: stub_batch/run_batch_file.py }
    output:  { type: file, file: 006.csv }
    expected_output_csv: 006.csv
"""


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "test_definition.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_load_valid_definitions(tmp_path):
    """정상 정의 → ShellDefinition 목록, test_id 3자리 정규화·필드 매핑."""
    defs = load_definitions(_write(tmp_path, _VALID))
    assert [d.test_id for d in defs] == ["001", "006"]  # 정수 1도 "001"로 정규화

    db = defs[0]
    assert db.input_type == "database"
    assert db.input_table == "transaction_log"
    assert db.output_type == "database"
    assert db.output_table == "tobe_result"
    assert db.export_csv == "001.csv"
    assert db.shell_program == "stub_batch/run_batch_db.py"
    assert db.timeout_seconds == 30

    f = defs[1]
    assert f.input_type == "file"
    assert f.input_dest_dir == "./out/tobe_input/"
    assert f.output_type == "file"
    assert f.output_file == "006.csv"
    assert f.timeout_seconds == 60  # 기본값


def test_file_not_found_raises(tmp_path):
    with pytest.raises(DefinitionError, match="찾을 수 없"):
        load_definitions(tmp_path / "nope.yaml")


def test_missing_tests_key_raises(tmp_path):
    with pytest.raises(DefinitionError, match="tests"):
        load_definitions(_write(tmp_path, "foo: bar\n"))


def test_invalid_input_type_raises(tmp_path):
    text = _VALID.replace("type: database, table", "type: nosql, table")
    with pytest.raises(DefinitionError, match="type"):
        load_definitions(_write(tmp_path, text))


def test_database_output_requires_export_csv(tmp_path):
    """output.type=database인데 export_csv 누락 → DefinitionError."""
    text = """
tests:
  - test_id: "001"
    input:   { type: database, table: transaction_log, csv: 001.csv }
    execution: { shell_program: x.py }
    output:  { type: database, table: tobe_result }
    expected_output_csv: 001.csv
"""
    with pytest.raises(DefinitionError, match="export_csv"):
        load_definitions(_write(tmp_path, text))


def test_database_input_requires_table(tmp_path):
    """input.type=database인데 table 누락 → DefinitionError."""
    text = """
tests:
  - test_id: "001"
    input:   { type: database, csv: 001.csv }
    execution: { shell_program: x.py }
    output:  { type: file, file: 001.csv }
    expected_output_csv: 001.csv
"""
    with pytest.raises(DefinitionError, match="table"):
        load_definitions(_write(tmp_path, text))


# --- D-033: 다중 입력(tables[]) ---------------------------------------------------


def test_multi_input_tables_parsed(tmp_path):
    """input.tables[] 신형 → inputs 리스트, 단일 호환 필드는 1차 입력에서 파생."""
    text = """
tests:
  - test_id: "001"
    input:
      type: database
      tables:
        - { csv: trans.csv, table: transaction_log }
        - { csv: cust.csv,  table: customer_master }
    execution: { shell_program: x.py }
    output:  { type: file, file: 001.csv }
    expected_output_csv: 001.csv
"""
    d = load_definitions(_write(tmp_path, text))[0]
    assert [(s.csv, s.table) for s in d.inputs] == [
        ("trans.csv", "transaction_log"), ("cust.csv", "customer_master")
    ]
    # 하위호환 단일 필드 = inputs[0]
    assert d.input_csv == "trans.csv" and d.input_table == "transaction_log"


def test_single_input_normalized_to_list(tmp_path):
    """구형 단일 입력도 inputs 1건 리스트로 정규화된다(하위호환)."""
    d = load_definitions(_write(tmp_path, _VALID))[0]
    assert len(d.inputs) == 1 and d.inputs[0].table == "transaction_log"


def test_multi_input_db_requires_table_each(tmp_path):
    """tables[] 중 database 항목에 table 누락 → DefinitionError."""
    text = """
tests:
  - test_id: "001"
    input:
      type: database
      tables:
        - { csv: trans.csv, table: transaction_log }
        - { csv: cust.csv }
    execution: { shell_program: x.py }
    output:  { type: file, file: 001.csv }
    expected_output_csv: 001.csv
"""
    with pytest.raises(DefinitionError, match="table"):
        load_definitions(_write(tmp_path, text))


# --- D-033 P2: 다중 출력(outputs[]) ----------------------------------------------


def test_multi_output_parsed(tmp_path):
    """outputs[] 신형 → outputs 리스트(각 expected), 단일 호환 필드는 1차 출력에서 파생."""
    text = """
tests:
  - test_id: "001"
    input: { type: database, table: transaction_log, csv: 001.csv }
    execution: { shell_program: x.py }
    outputs:
      - { type: database, table: result_a, export_as: 出A.csv, expected: 正解A.csv }
      - { type: file,     file: 出B.sam,                       expected: 正解B.sam }
"""
    d = load_definitions(_write(tmp_path, text))[0]
    assert [(o.type, o.expected) for o in d.outputs] == [
        ("database", "正解A.csv"), ("file", "正解B.sam")
    ]
    assert d.outputs[0].table == "result_a" and d.outputs[0].export_as == "出A.csv"
    assert d.outputs[1].file == "出B.sam"
    # 하위호환 단일 필드 = outputs[0]
    assert d.output_type == "database" and d.expected_output_csv == "正解A.csv"


def test_multi_output_requires_expected(tmp_path):
    """outputs[] 항목에 expected 누락 → DefinitionError."""
    text = """
tests:
  - test_id: "001"
    input: { type: database, table: transaction_log, csv: 001.csv }
    execution: { shell_program: x.py }
    outputs:
      - { type: file, file: 出B.sam }
"""
    with pytest.raises(DefinitionError, match="expected"):
        load_definitions(_write(tmp_path, text))


def test_single_output_normalized(tmp_path):
    """구형 단일 출력도 outputs 1건으로 정규화(하위호환)."""
    d = load_definitions(_write(tmp_path, _VALID))[0]
    assert len(d.outputs) == 1 and d.outputs[0].expected == "001.csv"


# --- D-036: 항목별 격납 패스 override(사장님 규격 #4·#6·#7·#7-3·#7-4·#11) -------------


def test_per_item_paths_parsed(tmp_path):
    """입력/출력 항목에 격납 패스·메타 필드가 적히면 그대로 InputSpec/OutputSpec에 실린다."""
    text = """
tests:
  - test_id: "001"
    input:
      tables:
        - { csv: in.csv, type: file, src_dir: /mnt/asis/in, dest_dir: /mnt/tobe/in, dest_name: staged.csv }
    execution: { shell_program: x.py }
    outputs:
      - type: file
        file: out.dat
        expected: gold.dat
        expected_dir: /mnt/asis/out
        tobe_dir: /mnt/tobe/out
"""
    d = load_definitions(_write(tmp_path, text))[0]
    i = d.inputs[0]
    assert (i.src_dir, i.dest_dir, i.dest_name) == ("/mnt/asis/in", "/mnt/tobe/in", "staged.csv")
    o = d.outputs[0]
    assert (o.expected_dir, o.tobe_dir) == ("/mnt/asis/out", "/mnt/tobe/out")


def test_per_item_paths_default_none(tmp_path):
    """경로 필드 미기재 시 None(= config 공통 디렉토리 사용, 하위호환)."""
    d = load_definitions(_write(tmp_path, _VALID))[0]
    assert d.inputs[0].src_dir is None and d.inputs[0].dest_name is None
    assert d.outputs[0].expected_dir is None and d.outputs[0].tobe_dir is None


# --- P0: compare 블록 / setup / in_encoding 운반 (HANDOFF §2·§3) ------------------

_P0 = """
tests:
  - test_id: "1"
    input:
      tables:
        - { type: database, table: TBL_A, csv: a.csv, in_encoding: shift_jis }
    execution: { shell_program: x.sh, setup: db/reset.sql }
    outputs:
      - type: database
        table: TBL_C
        export_as: c.csv
        expected: c_expected.dat
        compare:
          mode: record
          key: CUST_ID
          encoding: utf-8
          mask: UPD_TS
          tolerance: 0.001
          has_header: true
          normalize: "DT:date;BAL:num:2"
"""


def test_compare_block_parsed_into_outputspec(tmp_path):
    """출력 compare 블록이 OutputSpec 옵션 + compare_options로 구조화된다."""
    d = load_definitions(_write(tmp_path, _P0))[0]
    out = d.outputs[0]
    assert out.compare_mode == "record" and out.key == "CUST_ID"
    opts = out.compare_options
    assert opts.mode == "record"
    assert opts.encoding == "utf-8"
    assert opts.mask == ["UPD_TS"]
    assert opts.tolerance == 0.001
    assert opts.has_header is True
    assert opts.normalize == [("DT", "date", None), ("BAL", "num", "2")]


def test_setup_and_in_encoding_carried(tmp_path):
    """setup(execution)·in_encoding(input)이 ShellDefinition/InputSpec로 실린다."""
    d = load_definitions(_write(tmp_path, _P0))[0]
    assert d.setup == "db/reset.sql"
    assert d.inputs[0].in_encoding == "shift_jis"


def test_missing_compare_defaults_to_byte(tmp_path):
    """compare 미지정 출력은 byte 기본(현 동작 보존)."""
    d = load_definitions(_write(tmp_path, _VALID))[0]
    assert d.outputs[0].compare_options.mode == "byte"
    assert d.setup is None


def test_invalid_compare_mode_raises(tmp_path):
    text = _P0.replace("mode: record", "mode: bogus")
    with pytest.raises(DefinitionError, match="compare.mode"):
        load_definitions(_write(tmp_path, text))
