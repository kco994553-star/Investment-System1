# 승인 대기열 구현 계획 — GSQ-017

2026-10-10 사용자 사양과 연속 실행 지시가 설계·실행 기준이다. 기존 PR은 지정 순서로 병합했고 추가 승인이 필요한 값만 미정으로 남긴다. 문서·Python 단위로 분리해 순차 PR로 보존하며 웹/Worker/Actions는 코덱1이다.

1. **SEC M3**: `providers/sec_m3_adapter.py`·합성 테스트·코드 전용 `universe/universe_codes_v1.json`. 기존 M3를 입력/형 변환으로 연결, XBRL cover class proof·hash/time/issuer 검증, 미확정/차이 표시만. 실제 수집/연결 완료로 주장하지 않음.
2. **유형**: `qgv/type_config_v1.json`, `type_config.py`, `company_types.py`. 승인된 8유형/램프/7유형 비중/미분류/혼합/클램프를 versioned JSON으로 두고 계산은 입력 설정의 순수 함수. 공식 복사본 custom→PREVIEW, 스키마/사유 코드·결측/경계/충돌/불변성 테스트. 미정 quality/discount/volatility/theme 조합은 null. GSQ-017 append-only와 SIC 근거·19종목 비가격 결과 표 포함.
3. **테마**: 14개 사용자 테마·ETF 바스켓/키워드 후보를 문서/후보 설정으로 제안. N-PORT 원기관 공개 주기·영역·정정/유효시각과 키워드 의미·정규화의 미확정 상태 명시. 확인 전 membership 숫자·QGV 영향 생성 없음, 기기 override 경계 설계.
4. **DCF**: `qgv/dcf.py`·합성 분석해/역산 테스트. 5년 2단계/Gordon·이분법 구조만 구현하고 명시적 parameter confirmation 없으면 NOT_AVAILABLE. 할인율/영구성장률·FCFE/FCFF/주당 basis·성장 bracket 제안은 결정 대기, 가격은 인자/RAM만.
5. **Macro·대기**: 정부 GDP/CPI/후속4축→8축 초안 표만 문서, 채택 전 구현 없음. EDINET 후순위 보류, DART 등록 알림 전 비착수. CURRENT_HANDOFF/로드맵을 실제 PR·운영 상태로 갱신.

공통 리뷰 초점: 결측≠0, 유효 source vintage/단위·연속 연간기간, 가격없는 결과만 기록, 공식/기기 custom 분리, 설정 오류 시 부분 적용 금지, 유형 분류가 v2 calibration/모델 채택을 뜻하지 않음. 의미가 정해지지 않은 수치는 임의 산식으로 메우지 않는다.
