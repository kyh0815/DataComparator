"""정의 파일 미리보기 (Phase 7, T7-3 / D-034).

운영 타깃은 **디렉토리 기반**이다 — 데이터·정답·정의 파일이 `config.yaml`이 가리키는
디렉토리에 이미 있고, 화면은 그 정의를 그대로 실행만 한다(`/run`). 따라서 브라우저 업로드
검증·매핑표 생성(Phase 5/6, D-028~031)은 T7-3에서 화면·라우트와 함께 걷어냈다(불필요·간결).

여기 남은 것은 **정의 파일 요약**뿐 — 실행 전 "몇 셸인지, 셸별 입출력이 무엇인지"를
화면 상단에 미리 보여주기 위한 읽기전용 파싱이다(엔진 호출 없음).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from src.config.definition import DefinitionError, load_definitions


def summarize_definition_path(path: Path) -> dict:
    """config가 가리키는 정의 파일을 읽어 요약한다(읽기전용). 없으면 ok=False.

    web.py의 index()가 호출해 실행 전 미리보기(N셸·셸별 I/O)를 폼에 내린다.
    """
    if not path or not path.is_file():
        return {"ok": False, "count": 0, "shells": [], "message": "定義ファイルが見つかりません。"}
    return summarize_definition(path.read_bytes())


def summarize_definition(definition_bytes: bytes) -> dict:
    """정의 파일 바이트를 파싱만 해서 셸 요약을 돌려준다(미리보기용, 실행·파일 불요).

    {ok, count, shells:[{test_id, input_type, output_type, input_count, output_count}],
    message}. 파싱 실패는 ok=False + 메시지.
    """
    with tempfile.NamedTemporaryFile("wb", suffix=".yaml", delete=False) as tf:
        tf.write(definition_bytes)
        p = Path(tf.name)
    try:
        defs = load_definitions(p)
    except DefinitionError as exc:
        return {"ok": False, "count": 0, "shells": [], "message": f"定義ファイルの解析に失敗: {exc}"}
    finally:
        p.unlink(missing_ok=True)
    shells = [
        {
            "test_id": d.test_id,
            # 레거시 백필 프로퍼티(inputs[0]/outputs[0] 기준) — 대표 타입 표시용.
            "input_type": d.input_type,
            "output_type": d.output_type,
            # 다중 입출력(T7-1/T7-2 복원) — 셸당 입력·출력 건수.
            "input_count": len(d.inputs),
            "output_count": len(d.outputs),
        }
        for d in defs
    ]
    return {"ok": True, "count": len(shells), "shells": shells, "message": f"{len(shells)} シェルを読み込みました。"}
