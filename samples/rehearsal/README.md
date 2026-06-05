# リハーサル用サンプル — CK001 顧客残高マスタ日次更新

진짜 배치 붙기 전, **고객 입장에서 compare 파이프라인을 한 바퀴** 돌려보는 연습 세트.
銀行 계정계 시나리오: 입력=取引明細 → 배치 → 출력=顧客残高マスタ. 출력 형식 = DB export CSV
(**Shift-JIS·헤더 有**), `compare_mode=record`. 코어 코드/기존 테스트는 건드리지 않는 **신규 샘플**.

> DB 없이 돌리는 리허설이라 `type=file` 흐름이다. 출력 "DB export CSV"는 **형식**(Shift-JIS·헤더)으로
> 충실히 재현했고, 더미 배치가 진짜 배치 자리에서 To-Be를 낸다(호출규약은 코어 기본 BatchConfig).

## 구성
```
config.yaml                         실행 설정(파일 흐름, Shift-JIS)
shell_mapping.csv                   정의(사람이 채우는 Long CSV) — CK001
test_definition.yaml                위 CSV를 mapping_to_definition으로 변환한 정본(비노출 중간물)
make_rehearsal_data.py              As-Is 데이터 생성기(Shift-JIS)
batch/kokyaku_zandaka_update.py     더미 배치(진짜 배치 자리) — To-Be 출력 생성(결함 0003 포함)
asis/input/torihiki_meisai.csv      As-Is 입력(取引明細)
asis/output/kokyaku_zandaka_master.csv  As-Is 출력 = 정답(顧客残高マスタ)
tobe/, reports/                     런타임 생성물(.gitignore)
```

## 심은 차이 (To-Be vs As-Is 정답) — 5행 중 4행은 정당한 플랫폼 차이, 0003만 진짜 결함
| 컬럼 | As-Is(정답) | To-Be | 성격 | 해소 |
|---|---|---|---|---|
| (행 순서) | 0001..0005 | 셔플 | SELECT 비결정 | `key=KOKYAKU_ID` |
| SHITEN_CD | 0007 | 7 | 제로패딩 탈락 | `zeropad:4` |
| ZANDAKA | 150000.00 | 150000 | 소수자리 탈락 | `num:2` |
| KISAN_YMD | 2026-06-01 | 20260601 | 날짜포맷 | `date` |
| KOSHIN_NICHIJI | 2026-06-01 01:00:05 | 다른 실행시각 | 更新日時 | `mask` |
| BIKO | (빈칸) | NULL | NULL/공백 | `nullblank` |
| **0003 ZANDAKA** | **3000.00** | **2500** | **진짜 결함** | ❌ → **NG 유지** |

정규화 적용 시 **0001/0002/0004/0005 = OK, 0003만 NG(ZANDAKA)**.

## 실행 (repo 루트에서)
```sh
# (재)생성이 필요하면: python3 samples/rehearsal/make_rehearsal_data.py
python3 -m src.cli.main --preflight   --config samples/rehearsal/config.yaml   # 게이트: 통과
python3 -m src.cli.main --shells CK001 --config samples/rehearsal/config.yaml   # 비교 실행 → NG(0003)
python3 -m src.cli.main --evidence    --config samples/rehearsal/config.yaml   # 試験成績書(xlsx)
```

## 기대 결과
- **preflight**: 통과(파일·정답 존재, key/has_header 정합).
- **compare(레코드 레벨)**: 전체 5행 중 **4 OK / 1 NG**, NG는 **0003 ZANDAKA(3000.00 vs 2500)**만.
- **파이프라인(항목 레벨)**: CK001은 1체크리스트×1출력 = **全件 1 / NG 1**(레코드 5건은 그 출력 *안*의 행).
  → 사용자 표의 "全件 5 / OK 4 / NG 1"은 **레코드 레벨** 관점. 도구 집계는 (셸,출력) 항목 단위라 全件 1.
- **대조군(정규화 없이)**: byte 통짜·record-정규화X 모두 **5행 전부 NG**(전부 false-NG) → 정규화 필요성 입증.
- **試験成績書 明細**: CK001 NG 행에 0003 결함과 결과 출처(run 시각)가 표기됨.

⚠ 과정규화 주의: normalize/mask는 **실제 false-NG를 확인한 컬럼에만 최소로**. 과하면 false-PASS
(=마이그레이션 결함 은폐). 0003 같은 진짜 결함은 절대 정규화로 덮지 말 것.
