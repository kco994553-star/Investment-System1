[QGV 표준 v1 고정 — v1.1 범위, READ_ONLY 유지. TARGET v0 작업과 별도 lane]

사용자 결정 (2026-10-08, D3-R, Decision Register에 원문과 함께 append-only 기록)
- QGV의 Q·G·V 계산 의미를 "QGV Scoring Standard v1"으로 고정한다.
  상태 표시: STANDARD v1 · UNCALIBRATED (사용자 판단으로 고정, 데이터 보정 전).
- 이후 실데이터 보정(PIT·OOS·Calibration) 결과로 v2를 별도 결정한다. v1은 덮어쓰지 않고 보존한다.
- C-03 해소: Q7 이름은 "Management Quality(경영진 품질)"로 확정한다.
  Capital Allocation은 Management Quality의 하위 해석으로 문서에 기록한다. 가중치 10%는 그대로.
- 효력 시점: 2026-10-08 채택 시점. 과거 날짜로 소급해 "그때도 v1이었다"고 기록하지 않는다.

v1에 고정하는 내용 (현재 코드 값 그대로, 수치 변경 금지)
- Q 가중치 7개: qgv/factors.py의 Q_WEIGHTS
- G 가중치 6개: qgv/factors.py의 G_WEIGHTS
- G 기본 분석 기간: 3Y (qgv/g_horizon.py DEFAULT_G_HORIZON)
- V 가중치 7개: qgv/factors.py의 V_INITIAL_PRIOR (25/20/15/15/10/10/5)
- 원점수→점수 변환: qgv/raw_map.py의 현재 선형 clip 규칙 (D-10)
- 기업 유형별 보정: v1에서는 적용하지 않음 (identity)

작업
1. 표준 문서: QGV_SCORING_STANDARD_v1 문서를 추가한다. 위 항목의 exact 값, 소스 파일 경로,
   exact HEAD, 상태(STANDARD v1 · UNCALIBRATED), 효력 시점, v2로 가는 조건을 적는다.
2. 코드: 위 값들의 상태 표시를 PROVISIONAL / PROVISIONAL_INITIAL_PRIOR에서
   STANDARD v1 · UNCALIBRATED로 바꾼다. 수치는 한 자리도 바꾸지 않는다.
   v1 값이 바뀌면 실패하는 고정 테스트(값·합계·5–30% 제약)를 추가한다.
3. V 운영 점수: 지금은 출력하지 않도록 되어 있다. v1 기준으로 출력하되 모든 결과에
   standard=v1, calibration=UNCALIBRATED 표시를 붙인다. CALIBRATED로 표시하지 않는다.
4. 연구용 V 후보(equal_research 등)는 RESEARCH로 그대로 두고 운영 점수에 쓰지 않는다.
5. C-03을 Contract Conflict Register에서 RESOLVED로 기록한다(기존 기록은 지우지 않음).
6. 회귀: 기존 QGV 테스트가 모두 통과해야 한다. 점수 결과가 바뀌는 테스트가 있으면
   (V 운영 점수 출력 외에) 원인을 보고하고 임의로 기대값을 고치지 않는다.

v2 준비 (기록만, 실행 금지)
- v2 보정 전에 Holdout 보호 상태를 먼저 확정해야 한다는 조건을 표준 문서에 적는다.
- Holdout 기간 선택·소비는 하지 않는다.

포함하지 않는 것
- 가중치·변환 규칙 수치 변경, 보정·재적합, Holdout, 기준 브랜치 병합,
  AUTONOMY_MODE 변경, 자동화 확장.
