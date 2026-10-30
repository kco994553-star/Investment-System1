# Main 인계 — 확장 카탈로그 E0/E1-A

기준 HEAD `282382a76c963e885bfd090d3eec79543bcd90e0`, 작업 브랜치
`codex/expanded-universe-e0-e1a-20261029`. 사용자 직접 승인 범위의 독립 구현이다.
실행 상태: E0 감사 작성, E1-A IMPLEMENTED / 합성 TESTED. INTEGRATED/DEPLOYED/LIVE_VERIFIED 아님.
실제 상장 수·전체시장 커버리지·실수집·실가격·시총·백테스트·실환경은 모두 **NOT_RUN**.

## 변경 범위와 사용법

기존 파일 수정 없이 아래 신규 파일만 제출한다.

- `src/investment_system/universe/expanded_catalog.py`: immutable 모델·정규화·검증.
- `src/investment_system/universe/expanded_catalog_events.py`: PIT 사건 재생·구간 보존·diff.
- `src/investment_system/universe/expanded_catalog_snapshot.py`: private canonical bytes/hash,
  집계 receipt, 메모리 dry-run 실패 보존. 실제 저장/atomic file publish는 없음.
- `tests/test_expanded_catalog.py`, `tests/fixtures/expanded_universe/catalog_cases.json`.
- 이 디렉터리의 전용 계약·감사·권리·후속 설계·인계 문서.

`CatalogSnapshot(as_of=<명시적 UTC>, policy=CatalogPolicy())` 빈 상태에
`normalize_security_record(raw, policy)`로 검사한 SecurityRecord와 ListingEvent를 주입한다.
`apply_listing_events(previous, events, cutoff)`는 새 immutable snapshot 또는 고정 CatalogError를
돌려준다. `dry_run_refresh`는 소스 실패/무효 batch에서 exact previous object와 FAILED receipt를
돌려준다. 이전 last_success_at은 이전 receipt에서 명시적으로 주입한다. as_of/available_at을
성공 시각으로 대체하지 않는다. snapshot_bytes는 private용이며 공개 producer가 아니다.

`universe_version = SHA-256(snapshot_bytes)`이고 input_manifest_hash는 정렬된 사건 내용의
별도 hash다. 실패 receipt의 input_hash는 마지막 **수락된** 원장을 나타낸다. 실패 입력의
원문/값/메시지/hash를 공개 진단으로 자동 내보내지 않는다.
diff는 두 cutoff의 현재 증권 집합을 비교한다. 그 사이 신규 상장 후 종료된 종목의
처리량은 diff 개수에서 추측하지 말고 보존 원장·이력에서 별도로 검사한다.

재사용: 기존 `universe.resolve.company_id_for`를 엄격한 CIK 검사 뒤 직접 호출한다.
#417/#418은 읽기 전용으로 확인했으며 연구 엔진/명세를 복제·수정하지 않았다.
자세한 실제 경로와 충돌 목록은 [E0_AUDIT](E0_AUDIT.md)에 있다.

## 독립 리뷰·수정 근거

별도 검토자는 구현 commit `4498e39d`를 읽기 전용으로 검사했다. Critical 없음,
Important 3건과 malformed input 1묶음을 보고했다. 아래 8개 재현 시험을 먼저 실패시킨 뒤 수정했다.

| 발견 | 조치·반례 |
| --- | --- |
| collected_at만 바뀐 중복 이벤트를 충돌로 처리 | 내용은 별도 비교, 최초 수집 시각 보존. 최초 batch 중복 순서도 동일 결과 |
| 동시 합병 대상의 유효성이 ID 사전순에 따라 달라짐 | 대상 증권도 같은 효력 시각에 변경되면 MERGER_TARGET_TIME_AMBIGUOUS. 전/후 ID 순서 × 상장/상폐 4반례 |
| receipt 직접 호출로 수집 전 성공 시각 생성 가능 | 성공 receipt에도 모든 collected_at <= attempted_at 검사 |
| 매우 큰 정수 CIK와 오류를 던지는 timezone 객체 | CIK 변환 전 범위 제한, timezone 예외를 고정 INVALID_TIMESTAMP로 정규화 |

마지막 묶음은 검토자가 Minor로 분류했으나, 고정 오류·민감값 미반사 계약을 위반할 수 있어
이번 수정에 포함했다. 보류한 코드 발견 사항은 없다.

결정 기록: 같은 시각 합병 의존관계는 v1에 공급원 순서 증거가 없어 추측하지 않고 보류한다.
비용은 향후 동시 사건의 수동 대사/스키마 확장 필요다. 첫 batch에서는 가장 이른 collected_at을
선택하고 이후에는 원래 시각을 보존한다. 잘못된 시간 증거 정정은 event_id 재사용으로 하지 말고
후속 정정 계약으로 처리해야 한다.

검토자가 판단을 유보한 항목도 확인했다. fingerprint는 인증이 아닌 일관성 검사이며,
과거 삽입이 후속 full-record 사건을 모순되게 하면 전체 거절한다. as_of 이후 수집한
retrospective 자료는 허용하되 성공 시각은 수집 뒤여야 한다. 같은 증권·같은 시각 사건은
명시적으로 거절한다. E0 자료 권리와 실데이터·스케줄·통합은 별도 증거/권한 대상이다.

## Main 통합 순서

1. 이 Draft PR의 신규 파일만 검토한다. #417/#418·중앙 V·프론트엔드와 교집합이 없음을
   최신 canonical에서 다시 확인하고 필수 repository-guard를 확인한다.
2. Main이 별도 오너 승인 범위에서 병합한다. 공용 CURRENT_HANDOFF/기능 현황 등은
   **Main이** 이번 작업의 제한 승인과 실제 상태를 반영한다. Codex가 수정하지 않았다.
3. 모듈을 기존 Universe504 수집기·QGV·공개 검색 목록에 import/연결하지 않은 상태로
   우선 인수한다. 소비자와 공개 범위 변경은 다음 별도 작업이다.
4. [SOURCE_RIGHTS](SOURCE_RIGHTS.md)의 현재 상장 metadata 저장권·영구 ID·과거 상폐/PIT·
   가격/shares·계약 만료/보관·공개 집계권을 확보한다. 유료 구매는 오너 결정이다.
5. 그 뒤 [E1B_E2_PLAN](E1B_E2_PLAN.md)의 adapter/checkpoint/CAS와 운영 실패 시험을
   연결한다. 이번 합성 429 시험은 실제 HTTP/파일 복구 검증을 대체하지 않는다.
6. #417 membership 계약에 별도 어댑터로 넘기고 백테스트는 웹 밖에서 실행한다.
   웹은 권리를 확인한 결과만 읽는다. 기존 504 공식 점수를 확장 모집단에 복사하지 않는다.

공급원/사용권 전 E1-B 운영은 BLOCKED_ON_LICENSE, E2는 BLOCKED_ON_LICENSE/BLOCKED_ON_DATA다.
병합·배포·유료 계약·신규 정기 자동 실행은 이 PR로 승인되지 않는다.

## 직접 실행한 시험

명령은 `implementation/`에서, Python은 별도 작업 환경
`/workspace/scratch/expanded-venv/bin/python`을 사용했다. 저장소 dependency 파일은 수정하지 않았다.
전체 Python·가드의 최종 수치는 아래 검증 기록에서 확인한다.

- 변경 전 관련 기존 시험: 42 passed.
- 첫 모델 반례: 39 failed → 구현 뒤 기존 일부 회귀 포함 55 passed.
- 사건 반례 추가: 29 failed / 39 passed → 68 passed.
- receipt/hash/실패 보존 추가: 12 failed / 68 passed → 80 passed.
- fixture/I/O 불사용·성공 시각 미추정: 82 passed.
- 독립 리뷰 재현: 8 failed → 수정 뒤 새 합성 전체 **90 passed**.
- 수정 뒤 관련 회귀:
  `PYTHONPATH=src python -m pytest -q tests/test_expanded_catalog.py tests/test_universe_engine.py tests/test_universe_pit_incremental.py tests/test_universe_resolve_and_candidates.py tests/test_universe_codes_public.py tests/test_universe_listing_ended.py tests/test_public_price_boundary.py tests/test_spec_direction_guard.py`
  → **203 passed (32.59s)**.
- `python tools/spec_direction_guard.py` → 0 hits.
- 처음 shallow clone에서 repository guard는 완전 이력 필요로 exit 2였다.
  `git fetch --unshallow origin` 뒤 같은 guard는 READ_ONLY / violations=[] / privacy·email·repository PASS.
  보호 검사 완화·설정 변경은 없었다. 최종 제출 파일을 포함한 결과는 다음 기록에 둔다.

최종 검증 기록:

- `PYTHONPATH=src python -m pytest -q --tb=short -p no:cacheprovider tests`
  → **3,757 passed, 298 subtests passed (610.19s)**, 실패 0.
  이 전체 실행은 리뷰 보완 전 수집한 합성 80개를 포함한다. 실행 중 추가한 10개까지 포함한
  최종 합성 90개와 수정 코드의 최종 확인은 위의 **203 passed** 별도 실행으로 검증했다.
- 기준 HEAD의 기존 tracked 파일 수정/삭제 **0개**. Universe504 목록 수 **504**.
  목록·sec_universe_shares.py·sec_qgv2.py·forward_ledger.py·AUTONOMY_MODE·
  CURRENT_HANDOFF·SEC workflow·공용 검색 source의 기준 blob과 작업 파일 바이트도 각각 동일했다.
- 새 테스트와 fixture는 합성 데이터만 포함한다. full suite의 다른 기존 합성/회귀 실행을
  실제 전체시장 수집·실가격·라이선스·백테스트 검증으로 계산하지 않는다.
