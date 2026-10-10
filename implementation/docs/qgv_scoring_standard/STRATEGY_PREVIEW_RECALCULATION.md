# 전략 프로필 v1 재계산 — PREVIEW

최신 사용자 대기열6번. `personal/strategy_preview.py`는 [공식 Scoring Standard v1](QGV_SCORING_STANDARD_v1.md)의 Q/G/V **각 축 내부 요소 비중**을 복사해 개인 미리보기를 계산한다. 기존 `contracts/strategy.py`의 PROVISIONAL parameter pack과 구분하며, 공식 factor/비중/저장 snapshot을 변경하지 않는다.

## 호출 계약

`official_v1_weight_copy()`는 Q·G·V별 percentage 비중의 새 복사본을 반환한다. 각 축이100이며 Q/G/V를 합쳐100으로 만들거나 균등한 부모 비중을 만들지 않는다.

`recalculate_strategy_preview(observations, user_weights=None, profile_kind=GENERAL_CORPORATE)`는 공식 복사본에 제공된 사용자 비중을 적용한다. axis/factor 식별·유한 수치·0~100·**축별 합100**을 검사하고 잘못된 합을 자동 정규화하지 않는다. 사용자 PREVIEW를 새 공식5~30% 제약/표준 비중으로 채택하지 않는다.

반환 role은 항상 **PREVIEW**이며 불변 결과에 공식/실효 비중, 축별 점수·coverage, 결측 요소 ID/수, NOT_APPLICABLE 요소 ID를 제공한다. score는 repr에서 제외하고 공개 producer·serializer·모델 snapshot·DB/파일·로그·네트워크에 연결하지 않는다. 사용자 비중 저장·기기 화면은 코덱1 후속 범위다.

## 기존 집계 의미 보존

- 기존 `qgv.scoring._weighted`를 사용한다. 결측 요소 비중을 다른 요소로 재분배하지 않는다. BLOCKED_DEPENDENCY가 있으면 축 전체 점수는 null/BLOCKED다.
- 실제 점수0은 사용 가능한 값이다. 결측·PIT_UNAVAILABLE·NOT_APPLICABLE은0으로 채우지 않는다. FINANCIAL의 roic_wacc는 NOT_APPLICABLE로 별도 집계하며 결측수와 구분한다.
- V는 공식 Initial Prior의 요소 순서·산술을 보존한다. 합성10..70 참조는31.5이며 Fundamental Value25%가 누락된 나머지70점 사례는52.5/PARTIAL다.
- Q/G가 있으면 기존 `round((Q+G)/2,4)`를 **qg_preview_total**로만 제공한다. V를 합성하지 않는다. 결측/부분 coverage는 축별로 계속 표시한다.

## 미확정 범위

공식 Q/G/V **부모 비중 registry**와 Technical/Macro를 합성한 새 프로필, 모델 포트폴리오·6관점 정의는 이번 v1 근거에 없다. `UNDEFINED_PARENT_WEIGHTS`로 명시하고33/33/34 같은 부모 비중·새 총점을 만들지 않는다. 위 PREVIEW가 사용자의 새 공식 전략 채택·검증/PIT/OOS/Calibration·forward 시작을 뜻하지 않는다.

합성 테스트로 공식 복사본 불변성, 사용자 합100/오류, 기존 Q/G/V 참조값·0·결측·차단·금융 적용성, total의 V 제외, 고정 PREVIEW·RAM 경계를 검증한다. 실제 입력·가격·개인 프로필·Holdout은 사용하지 않는다.
