"""시연용 stub 배치 (진짜 Net COBOL 배치의 대역).

# === 인수인계 시 교체 포인트 ===
# 이 파일은 시연용 stub 배치다. 실 운영에서는 Net COBOL 배치 호출로 교체한다.
# 입출력 계약(--shell-id, --output-path)은 유지할 것.

DB에서 input을 읽어 단순 변환 후 To-Be 출력 CSV(Shift-JIS)를 생성한다.
특정 shell_id에서는 의도적으로 다른 결과를 만들어 NG 시연을 한다(SPEC 6-2).

# TODO (T2-3): --shell-id / --output-path 인자 처리 + 정상/NG 패턴 구현
"""
