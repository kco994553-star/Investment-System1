# SIC 업종군 v0 · 전략 테마 v0 — 2026-10-11 사용자 결정 구현

모든 기본값은 **v0 · UNCALIBRATED · 나중에 수정 가능**(`V0_UNCALIBRATED_DEFAULT`)이며 화면에 같은 표식을 붙인다. Q/G/V 점수·가중치·TARGET에는 영향이 없다. GSQ-017 `type_config_v1.json`과 내장 사본 `type-config-defaults.js`는 수정하지 않았다.

## 설정

| 파일 | 내용 |
| --- | --- |
| [`qgv/sic_industry_groups_v0.json`](../../src/investment_system/qgv/sic_industry_groups_v0.json) | DESIGN_V1·QUEUE 초안 표 10개 범위 + 표에서 분리하라고 적힌 세부군(2080 음료, 357x 컴퓨터, 3674 반도체, 384x 의료기기, 5411 식품 소매, 737x 소프트웨어, 8000~8099 의료 서비스). 경기민감/방어는 표에 적힌 **후보 표식만**(1000~1799 민감 후보, 2000~2199·4900~4999 방어 후보) 보존하고 소속도는 NOT_AVAILABLE. SIC 없음·0000·범위 밖은 NOT_AVAILABLE. GICS 미사용. |
| [`qgv/theme_config_v0.json`](../../src/investment_system/qgv/theme_config_v0.json) | v1 제안 14개 바스켓·키워드. 전력 인프라=GRID만, 소비자 브랜드 `evidence_strength=WEAK`(화면 '근거 약함'). 소속 규칙·40% 경고 기본값 포함. v1 파일은 이력으로 보존. |

## 소속 규칙 (테마 v0)

- 소속 = 바스켓 ETF 중 1개 이상이 최신 원본 NPORT-P(정정본 제외)에서 보유(자산 분류 EC·Long, ISIN 또는 CUSIP 정확 일치) **OR** 최신 원본 10-K의 Item 1(Business)에 테마 키워드가 1회 이상(theme_exposure의 literal phrase 규칙, Item 1A·목차·숨은 XBRL 제외).
- 근거 종류(`ETF`·`KEYWORD`)와 보유 ETF 티커 목록을 기록한다.
- '비소속'은 바스켓 ETF 전부 확인 + 미보유 + 키워드 근거 음성(10-K 미제출 20-F 기업 포함)일 때만. 그 밖에는 null(NOT_AVAILABLE)이며 0으로 채우지 않는다.
- 기업 식별자는 공개 identity 카탈로그의 ISIN(미국 ISIN에서만 CUSIP 파생)만 사용한다. 이름 매칭·CUSIP 앞 6자리(발행사) 매칭은 하지 않는다. 그래서 GOOGL은 A주만 결속되고, 도쿄일렉트론·한미반도체는 거래소 코드만 있어 ETF 결속과 SIC가 NOT_AVAILABLE이다.

## 공개 파일 `company-classification.json`

Python([`product/public_classification.py`](../../src/investment_system/product/public_classification.py))이 생성·검증하고 JS([`classification-screens.js`](../../src/investment_system/product/web_assets/classification-screens.js))가 같은 규칙으로 다시 검증한다. Pages 가드가 파일 이름·구조를 검사한다.

- 담는 것: 업종군·테마 id/이름, 기업별 SIC·업종군·소속(true/false/null)·근거 종류·보유 ETF 티커, ETF별 보고 기준일, as-of, reason code, 원문 SHA-256.
- 담지 않는 것: ETF 비중·평가액·수량·가격, 10-K 본문·키워드 빈도.
- 오프라인 빌드(`build_pages_cockpit.py`)는 전부 NOT_AVAILABLE 파일을 만든다. 실데이터는 Actions의 `tools/public_classification_pipeline.py --live`가 채운다(SEC_USER_AGENT). 실시간 수집 실패 시 NOT_AVAILABLE 파일로 대체하고 배포를 막지 않는다.

## 쏠림 경고 (기기 전용)

- 단일 테마 노출이 포트폴리오의 40% **초과**면 경고(`v0 기본값` 칩). 정확히 40%는 경고 아님.
- 노출 = 소속 true인 보유 종목의 ACTUAL 비중 합. 소속 null·기록 없음은 '자료 없음' 비중으로 따로 더하며, 알려진 노출 ≤ 40% < 노출+자료 없음이면 '확인 불가'.
- S03에서 전략 테마 v0와 내 TARGET 테마의 ACTUAL 두 범위를 표시한다. 계산은 기기 RAM에서만 하고 저장·공개하지 않는다.
- Python 참조 `qgv.theme_membership.theme_concentration` ↔ JS `ClassificationScreens.themeConcentration`, 공유 벡터 `tests/fixtures/theme_concentration_v0_vectors.json`.

## 남은 결정 (NOT_AVAILABLE 유지)

1. 경기민감·경기방어 **소속도 산식**(type_config/1의 매출 변동성 램프·결합 미정). SIC 후보 표식만 표시.
2. 동종 비교 기준(업종군 v0 연결됨, 비교 산식 없음).
3. ETF 보유 비중 정규화·키워드 빈도 가중 등은 v0 규칙(이진 OR)에 없다.
