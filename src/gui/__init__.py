"""GUI(웹) Interface Layer — Core를 그대로 재사용하는 또 하나의 인터페이스 (Phase 5, D-028).

CLI(`src/cli`)와 동일하게 `core.run_full_comparison(config, on_progress, shell_ids)`를 호출하고
`ProgressEvent`/`RunSummary`를 소비할 뿐, Core는 한 줄도 바꾸지 않는다(D-006/D-025의 콜백 설계가
GUI 이식을 전제로 한 지점). 표시용 dict 직렬화는 이 패키지(`serialize.py`)에만 둔다(models 불변).
"""
