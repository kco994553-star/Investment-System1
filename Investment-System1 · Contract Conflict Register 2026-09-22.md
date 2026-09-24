Investment-System1 · Contract Conflict Register  
기준: 2026-09-22  
규칙: Existing / Proposed / Reason / Impact / Compatibility / Validation Required.  
검증 전 변경은 PROPOSED 또는 CONFLICT. v1.7.6 문구를 추측으로 재작성하지 않음.

C-01 BLOCKING · Macro 권한 v0.1.1 vs v0.1.4 Candidate  
Existing: Master Status · CURRENT_HANDOFF · 문서 §1 = v0.1.1, 28/28 PASS.  
Proposed: 같은 Latest 문서 §13 이후 = v0.1.4 Candidate, 36/36 PASS. 승격하지 않음.  
Reason: 한 파일이 두 기준선을 보유. Master Status 미갱신.  
Impact: 36/36을 공식 PASS로 오인 가능.  
Compatibility: QGV 불변·최종 주문 금지 원칙은 일치.  
Validation Required: 원본 패키지로 28 vs 36 재실행 후에만 승격 검토.  
Resolution: CONFLICT. Confirmed는 v0.1.1.

C-02 STALE_INDEX · Project Index Technical 69/69 vs Master 159/159  
Existing: Project Index Phase 4, 69/69.  
Proposed: Latest/Master = Phase 6 + Real PIT Validation v0.6, 159/159.  
Reason: Index가 Latest보다 구버전.  
Impact: Structural Freeze 범위 과소평가.  
Compatibility: 설계 방향 동일.  
Validation Required: 문서 동기화. 코드 재실행과 별개.  
Resolution: STALE_SYNC. Master Status 우선.

C-03 BLOCKING · Q7 Management Quality vs Capital Allocation  
Existing: Analysis v1.7.6 Q7 = Management Quality 10%.  
Proposed: Integrated Spec scoring freeze Q7 = Capital Allocation. 병합하지 않음.  
Reason: 동일 factor라는 증거가 없음.  
Impact: 채점·UI·Track Record 축 분기.  
Compatibility: 가중치 10%는 같을 수 있으나 이름 불일치.  
Validation Required: 원 코드 또는 사용자 확인.  
Resolution: CONFLICT.

C-04 ALIGNMENT · Common Schema vs Implementation Plan 필드명  
Existing: analyzed_at, qgv_system_version, qgv_standard_version, Q_score, resolve().  
Proposed: Plan의 as_of, standard_version, get_latest_available()는 구현 초안. Schema가 계약 우선.  
Reason: 이전 Handoff 지적, 이번 문서 대조로 확인. 소스 없음.  
Impact: Core Alpha 착수 시 매핑 표 필요.  
Compatibility: 의미 대응 가능, 이름 비1:1.  
Validation Required: 실제 소스 대조. Schema 재작성 금지.  
Resolution: CONFLICT (naming).

C-05 GAP · Common Schema v1.0 미반영 v1.7.6 필드  
Existing: Q/G/V 점수, confidence, drivers, refs.  
Proposed: additive only — factor_breakdown, calibration_version, coverage_state, v_policy_status, company_understanding_ref, evidence_refs, profile_kind, available_at.  
Reason: freeze가 Schema v1.0 이후.  
Impact: 스키마만으로 freeze 계약 구현 불가.  
Compatibility: additive 우선 정책과 맞음.  
Validation Required: PROPOSED additive revision. 패키지 대조 후.  
Resolution: GAP.

C-06 GAP · company_id vs security_id  
Existing: Canonical key = company_id.  
Proposed: Simulation/Leaderboard는 security_id + dated ticker aliases + corporate action.  
Reason: 기업≠상장증권 (dual listing, TEL).  
Impact: PIT universe 불완전.  
Compatibility: identifier_history로 일부 수용. security_id 미정의.  
Validation Required: Additive identifier 모델은 패키지 후 PROPOSED.  
Resolution: GAP.

C-07 GAP · Portfolio Holding에 company_id 없음  
Existing: Common Schema holding.company_id.  
Proposed: Portfolio spec §3는 name/ticker 중심.  
Reason: 표시 스키마와 정규 스키마 혼재.  
Impact: C-08 TEL과 결합 시 오연결.  
Compatibility: ticker=display, company_id=key 로 분리하면 양립.  
Validation Required: holding.company_id additive.  
Resolution: GAP.

C-08 BLOCKING · TEL 식별자  
Existing: Portfolio v1.1 반도체 장비 5% TEL. 문맥 = Tokyo Electron.  
Proposed: 미국 TEL(TE Connectivity) 해석 금지. exchange-qualified ID를 임의 고정하지 않음.  
Reason: 티커 충돌, company_id 없음.  
Impact: 가격·시장·통화·PIT가 전부 달라짐.  
Compatibility: 비중 5% 정책 유지.  
Validation Required: 사용자 확인 후 company_id 부여.  
Resolution: CONFLICT / OPEN.

C-09 ALIGNED_CAVEAT · V factor vs pipeline vs SOTP  
Existing: v1.7.6 V 7 factors, VALIDATION_SELECTED.  
Proposed: Integrated pipeline + “SOTP where applicable”. SOTP를 8번째 factor로 추가하지 않음.  
Reason: 계층이 다름.  
Impact: SOTP 공식 factor화는 freeze 위반.  
Compatibility: SOTP는 Fundamental Value 입력으로 해석 가능.  
Validation Required: V aggregate production 사용 금지 유지.  
Resolution: ALIGNED_CAVEAT.

C-10 ALIGNED_CAVEAT · PASS 숫자 합산 금지  
Existing: 모듈별 서로 다른 PASS 기록.  
Proposed: 패키지별 RECORDED로 분리. 전체 PASS 금지.  
Reason: 산출물·시점이 다름.  
Impact: 합산 시 검증 완료 오인.  
Validation Required: 원본 없으면 전부 RECORDED.  
Resolution: ALIGNED_CAVEAT.

C-11 ALIGNED_CAVEAT · Simulation 모드 용어  
Existing: UI 과거/현재. Schema HISTORICAL/CURRENT/FORWARD.  
Proposed: Current Mode를 FORWARD Validation과 섞지 않음.  
Compatibility: UI 2모드 ⊂ 실험 3모드 해석 가능.  
Resolution: ALIGNED_CAVEAT.

C-12 ALIGNED_CAVEAT · PIT 게이트 published_at vs available_at  
Existing: Plan은 published_at. Freeze·Simulation·Macro는 available_at ≤ as_of.  
Proposed: 결정 게이트 해석은 available_at. Schema 문구를 이번 턴에 수정하지 않음.  
Reason: 발표일 ≠ 이용가능일.  
Impact: look-ahead 또는 과도차단.  
Resolution: ALIGNED_CAVEAT.

C-13 ALIGNED_CAVEAT · Universal Q/G weights vs type-specific matrices  
Existing: v1.7.6 Q/G % freeze. Integrated: type-specific matrices CALIBRATION_PENDING.  
Proposed: 두 계층을 한 표로 합치지 않음. 유형 가중치 숫자 발명 금지.  
Resolution: ALIGNED_CAVEAT.

C-14 GAP · Integration Snapshot 부재  
Existing: Common Schema는 QGV 모듈 ID만.  
Proposed: qgv + technical + macro snapshot → gate → target_weight 객체는 상위 레이어. OM/TM/MM/RM은 PROVISIONAL.  
Impact: 결합 객체 이름 없음.  
Resolution: GAP. 신규 기능이 아니라 기존 흐름의 스키마화. 지금은 PROPOSED하지 않고 공백으로 남김.

C-15 GAP · Technical Fusion 출력 스키마 U-09  
Existing: Decision History U-09 미해소. Latest는 구조 구현 기록.  
Proposed: 추측으로 Fusion 수식/필드 작성 금지.  
Impact: Investment System 소비 필드명 미공식.  
Resolution: GAP.

C-16 GAP · ChatGPT Work와 Drive SSoT 사이 산출물 미이관  
Existing: Project Index는 구현·테스트를 ChatGPT Work 주 실행공간으로 둔다. Drive는 Source of Record.  
Proposed: Work/원 개발 산출물을 Drive에 이관하기 전 RECORDED 유지. 추정 재생성 금지.  
Reason: 2026-09-22 ZIP과 현재 워크스페이스에 실행 패키지 없음. Work 마운트 없음.  
Impact: PASS 재실행 경로가 없어 VERIFIED 승격 차단.  
Compatibility: 저장 정책과 일치. 설계 변경 아님.  
Validation Required: 원본 ZIP/리포 이관 후 재실행.  
Resolution: GAP.

Cross-system alignment (충돌 아님)  
- QGV 원본 불변: ALIGNED  
- 단일 Target Weight/Order 경계: ALIGNED  
- −20% Re-check: ALIGNED  
- News가 QGV를 직접 변경하지 않음: ALIGNED  
- Technical S=1~N 과 Macro S=1~N 객체 분리: ALIGNED  
- Snapshot immutability / PIT: ALIGNED  
