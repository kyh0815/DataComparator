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
