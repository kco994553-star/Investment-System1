# 1.1.8 기술 조건 필터 (기능 3.5) — 화면과 `technical-leaderboard/1` 연동

작성 2026-11-03 · Main. 갱신 2026-11-04: Codex 계약에 연동했다.

근거는 다음과 같다.
- 오너 지시 "계층 3 기술적 분석 리더보드 화면"(11/03)과 11/04 지시 3(#469 공개 합성 fixture를 변환 없이 판독).
- 계산은 Codex, 화면·접근성·운영 통합은 Main이다(DC-42).
- 이 기록은 비공개 연구값 공개, 병합, 배포 승인이 아니다.

## 1. 계약

Codex 연구 스키마 **`technical-leaderboard/1`**을 그대로 읽는다.
- 기준: #469 `f1ca390a`, 설정 `technical-leaderboard/2026-11-03.1`, 문서 `implementation/docs/lab/TECHNICAL_LEADERBOARD_V1.md`
- 회신: #437 [6601332838](https://github.com/kco994553-star/Investment-System1/pull/437#issuecomment-6601332838)·[6602595466](https://github.com/kco994553-star/Investment-System1/pull/437#issuecomment-6602595466)
- 11/03에 만든 임시 계약 `tech-screen-v0`는 버렸다.

- **보드는 `(signal_day, group_id)`마다 하나다.**
  - 보드 항목: `schema`, `signal_day`, `settings_version`, `settings_sha256`, `group_id`, `membership_status`(CONFIRMED·UNKNOWN), `membership_source`, `population_hash`, `metrics`
  - 지표는 `momentum_3m`·`momentum_6m`·`momentum_12m`·`volatility_6m`·`dollar_volume_6m`이다.
  - 지표마다 `n_valid`, `n_members`, `median`, `k`, `null_reason`, `rows`가 있다.
  - 행 항목: `value`(decimal string 또는 null), `null_reasons`, `security_id`, `series_id`, `rank`, `decile`, `conditions{gt_zero, ge_median, gt_median, top_decile, bottom_decile, exclude_D10}`
- **입력 형태:** 보드 하나, 보드 배열, 또는 Codex fixture 묶음(`{cases:{…}}`). fixture 파일(`implementation/tests/fixtures/technical_leaderboard_v1.json`)은 #469와 바이트까지 같고 sha256을 고정했다.
- **단위:**
  - 모멘텀: %, 가격 수익률, 배당 재투자 없음
  - **변동성: "6개월 일간 변동성(%, 비연율화)"**. 일간 수익률의 표본 표준편차(ddof=1)이며 %/일로 표시한다.
  - 거래대금: USD/거래일. 같은 체결 범위가 확인된 완전 관측 평균이다.
- **조건:** 파일이 준 불린을 그대로 쓰고 다시 계산하지 않는다.
  - 중앙값 이상 = `ge_median`, 중앙값 초과 = `gt_median`이다. 중앙값과 같은 행은 이상이 참, 초과가 거짓이다.
  - null 조건은 판정 불가다. 통과로도 미충족으로도 세지 않고, 미충족이 함께 있으면 미충족으로 센다.
- **판독기 검사:** 첫 위반에서 입력 전체를 거부한다.
  - 그룹 구성 미확인이면 N·순위·중앙값·분위·상대 조건이 모두 null이어야 한다.
  - N은 채택값 수와 같아야 한다.
  - 순위는 1..N에 한 번씩이어야 한다.
  - k는 N≥10일 때 floor(N×0.10)이고, N<10이면 분위가 없어야 한다.
  - 각 조건은 값·중앙값·분위와 맞아야 한다.
- **원시값:** 채택값이 null이면 NA와 사유로 보여 준다. 행에 `raw_value`가 있어도 화면에 쓰지 않고 null을 채우지 않는다.

## 2. 화면 흐름 (새 앱 `#/qgv` → 1.1 리더보드 → 1.1.8)

1. **① 평가일 · 비교 그룹:** 보드를 고른다. 화면에 평가일·그룹·구성원 확인 여부·설정 버전을 보여 준다.
2. **② 지표 카드 5개:** 카드마다 단위, 기준일, 비교 그룹, 유효 종목 n/구성원, 중앙값, 상태와 D10의 뜻이 나온다. 상태는 셋 중 하나다.
   - 분위 매김(D10·D1 각 k개)
   - **유효 종목 n < 10 · 순위·중앙값만 · 분위 없음**
   - **그룹 구성 미확인 · 순위·중앙값·분위 없음**
3. **③ 필터:**
   - 모멘텀: 0% 초과·중앙값 이상·중앙값 초과·상위 10%
   - 변동성: D10 제외·D10만
   - 거래대금: D10만·D1만
   - "원래 순위 기준" 지표를 고른다. "리더보드 표에도 적용" 스위치가 있다.
4. **④ 결과:**
   - 통과·미충족·판정 불가 수와 판정 불가 목록(사유)을 보여 준다.
   - **계산 후 조건 충족 0건**(모든 조건을 판정, 통과 없음)과 **조건 충족 0건·판정 불가 n건**은 따로 표시한다.
   - 보드 표(휴대폰에서는 목록)는 통과 행을 **원래 보드 순위 그대로**, 그 순서대로 보여 준다. 필터를 더해도 순위 번호를 다시 매기지 않는다.
   - 리더보드 표는 같은 평가일·같은 증권으로 확인된 행만 거른다(11/07 오너 감사, [TECH_FILTER_QGV_JOIN](TECH_FILTER_QGV_JOIN.md)). `security_id`와 행 id·code의 글자 비교로는 결합하지 않는다. 걸러진 표의 정렬은 1.1.2 그대로(기본 QGV 높은 순)다.
   - 결합이 안 되면(평가일 없음·불일치, 매핑 계약 없음·누락·중복, 신원 불일치) 리더보드 표를 바꾸지 않고, 그 이유를 적는다.

기술 지표 값은 가격 파생값이므로 `[data-ram-price]` 안의 텍스트로만 보여 준다. 화면 상태는 RAM에만 두고 저장하지 않는다. 원천(`IS2.techScreen.source()`)은 지금 `NONE`이고 아무것도 요청하지 않는다.

## 3. 시험 (`tools/web_app_tech_filter_*`)

- **node 9개:**
  - fixture 해시와 그대로 판독
  - 중앙값 같은 행(interior_remainder_23 S011, negative_ties_10 momentum_3m 전원 동률)
  - 세 상태 구분
  - fixture `filter_example` 재현
  - 필터 뒤 순위·N·중앙값 불변
  - raw_value 미사용
  - 거부 규칙 10종
  - 결합 보드 생성기(N=23 분위 크기 2,3,3,3,2,2,2,2,2,2)
- **브라우저(1440·390) 23개:** 위 항목을 화면에서 확인한다. 더해서 결합 보드로 리더보드 표가 QGV 순으로 걸러지는지, 휴대폰 가로 넘침·44px, RAM 텍스트, 요청·저장·CSP 경계를 본다.

## 4. 남은 것

- 실자료 연결: 비공개 경로(#436), 공개 연결은 별도 승인이다.
- 리더보드와의 실제 결합: 고정 증권 ID ↔ Universe 상장 키·유효기간 매핑이 필요하다([TECH_FILTER_QGV_JOIN](TECH_FILTER_QGV_JOIN.md)). PIT·증권 신원 작업은 Codex 담당이다.
