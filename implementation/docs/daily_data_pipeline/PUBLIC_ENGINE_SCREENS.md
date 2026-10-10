# 공개 표시용 엔진 JSON — 코덱1 연결 계약

명시적으로 보존한 정부 원문을 입력으로 받아5개 price-free 파일을 생성한다. 네트워크·환경변수·키 조회·수집·워크플로·UI 연결은 하지 않는다. 개인 Universe/관심 기업/순위·가격·시총·환율·거래·V·전략·테마 override·DCF·Holdout은 입력이나 출력에 연결하지 않는다.

## 실행

```sh
PYTHONPATH=implementation/src python implementation/tools/public_engine_screens.py \
  --manifest /private-runtime/manifest.json \
  --output-dir /temporary-public-site \
  --as-of <현재-취득-cutoff-UTC> \
  --stale-after-hours <코덱1이-제공한-취득-TTL>
python implementation/tools/pages_artifact_guard.py --artifact-dir /temporary-public-site
```

as_of·취득 TTL은 호출자가 제공한다. 임의의 모델 임계값이나 검증 기간 기본값을 추가하지 않는다. 성공은 `PUBLIC_SCREENS_OK files=5`, 오류는 값·경로·원문 없는 고정 코드다. JSON은 allow_nan=False·파일당2MiB 이내이며 모두 생성/검증한 뒤 고정5개 파일을 원자적으로 교체한다. 기존 검토 자산을 다시 만들거나 hash를 repin하지 않는다. 전체 site와 최종 Pages tar 모두 guard 후 업로드한다. 다중 파일의 디스크 쓰기 자체는 하나의 트랜잭션이 아니므로 CLI 오류 시 업로드하지 않는다.

## 공통 envelope

schema_version=1, kind, as_of(UTC), state(LIVE/STALE/NOT_AVAILABLE), sources(agency·원문 SHA256·acquired_at), reason_codes, freshness_basis=SOURCE_ACQUISITION, stale_after_seconds, data.

LIVE는 **공급 원문 취득 신선도**이며 모델 승인·현재 재무 기간·PIT 빈티지·Calibration의 증거가 아니다. 회사별 factor/state와 파일 전체 상태가 일치한다. 일부 LIVE가 있으면 파일 LIVE, LIVE 없이 STALE가 있으면 STALE, 모두 결측이면 NOT_AVAILABLE다. 결측 수치는 null이며0으로 대체하지 않는다. source_hashes는 해당 행이 사용하는 source agency/SHA와 연결된다. 같은 해시를 서로 다른 취득시각으로 중복 공급하는 manifest는 지원하지 않는다; 현재 capture별 원문을 명시한다.

| 파일 | data·의미 |
| --- | --- |
| macro-screen.json | 기존8축×6차원48칸·RAW_EVIDENCE/NOT_AVAILABLE·정부 원자료 Decimal문자열·unit_scale·binding_sha256. FX는 공개 제외, regime=null, OBSERVED_BOUND_ONLY/NOT_VERIFIED. 원자료→국면 입력 정의가 승인되기 전 국면 생성 없음. |
| sec-13f-changes.json | 사용자 공급 두 분기의 SEC 정보표·manager CIK·NEW/ADD/REDUCE/EXIT **보고 수량 변화**. reported_before/after/delta만; 공시 USD value·가격·실제 거래·현재 보유 추론 없음. 현재 보고 취득 TTL로 신선도 판정하며 이전 보고의 오래된 분기 자체는 STALE 원인이 아니다. |
| sec-filing-windows.json | TARGET19의 관측10-Q/10-K 제출 월일 구간. role=ESTIMATED_PATTERN_NOT_CONFIRMED, confirmed_earnings_date=null. 확정 실적 발표일이나 선택한 미래 시작일 아님. |
| sec-qg-factors.json | 기존 SEC M1/M2·raw_map의 Q/G leaf factor score. PROVISIONAL_UNCALIBRATED·OBSERVED_CAPTURE_ONLY. 기존 가중치·산식 유지, 새 평균/QGV/V/순위 없음. |
| company-types-pricefree.json | growth/quality/cyclical/defensive만, membership0~1/null·config_version. 가격/배당수익률/시총/순위를 입력하지 않는다. type engine #135가 미병합이면 TYPE_ENGINE_PENDING_MERGE와 null이다. |

Q/G와 유형은 TARGET19만 포함한다. 미국17개는 원문이 없거나 M1/필수 연결 근거가 불충분하면 결측, KR/JP는 DART/EDINET 미연결로 결측이다. 3Y CAGR은 같은 revenue tag/unit의 정확한 연간4개 기간이 연결될 때만 계산한다;52주 회계연도를 추정해서 채우지 않는다. 우량의 ROIC 근거만으로 최종 소속도를 만들지 않고, 미확정 마진/부채·변동성 조건은 null로 유지한다. 이 모듈은 가격이 필요한 유형으로 데이터를 넘기지 않는다.

## 비공개 입력 manifest/1

최상위 정확한 필드: schema_version=1, sec(list), macro(list), thirteen_f(list). SEC 최대17개·macro64개·13F20쌍. 원문 파일 경로는 manifest 디렉터리 안의 상대경로만; ../·외부경로·파일 symlink·32MiB 초과를 차단한다. JSON 중복키/비유한 숫자를 차단한다. synthetic=true 입력과 as_of 이후 취득은 공개 값으로 쓰지 않는다. malformed manifest/원문은 고정 오류로 실패한다. 없는 자료는 해당 list를 비워 명시NA를 생성한다.

SEC 항목 정확한 필드: company_id(US17 ID), companyfacts(상대파일), submissions(상대파일), acquired_at, synthetic(bool). 원본 body의 CIK가 company_id와 맞아야 한다. SEC 공개schema/3는 주식 수 투영이므로 Q/G 입력으로 대체할 수 없다. 이 CLI에는 **원본 companyfacts/submissions**를 임시 RAM/실행 디렉터리에서 공급하고, 공개 디렉터리에 원문/manifest를 복사하지 않는다.

Macro 공통: provider,file,acquired_at,synthetic. BLS는 series_ids 목록, BEA는 table(T10106/T10101), Treasury는 기존10년 국채 수익률 XML. 후속FED_H41/H8/H10/TREASURY_MTS는 기존 RemainingSeriesBinding 전체 binding과 source_url을 입력한다. 새 series 선택/의미를 승인하지 않으며 공급 binding을 기존 parser가 검증한다. source URL·basis·selector/free text는 공개하지 않고 binding_sha256으로 구분한다. 단위는 승인된 표기만 공개하며 미확인 문자열은 해당 observation 제외다. BEA UNIT_MULT는 POWER_OF_TEN exponent, Fed UNIT_MULT는 MULTIPLIER factor로 구별해 보존한다; 배율을 적용한 새 수치를 만들지 않는다.

13F 쌍: previous/current 각각 file,metadata; 쌍 synthetic(bool). metadata는 기존 FilingMetadata 필드이며 quarter_end/filing_date는 ISO일자, acquired_at은 UTC timestamp다. 정보표 SHA는 CLI가 원문으로 재계산한다. manager 선택은 호출자가 명시한다; 기본 투자자·개인 선호를 저장하지 않는다. confidential/추가 정정/부분표/cover-binding 미확정/비연속분기는 기존 parser/compare의 NOT_AVAILABLE를 유지한다. issuer/titleClass 텍스트 대신 security_key 해시를 사용하며 옵션/수량 종류별 식별을 합치지 않는다.

## 연결·검증

코덱1이 별도 Actions에서 정부 원문과 manifest를 공급하고 CLI→directory guard→tar guard→업로드→앱 읽기를 연결한다. 이 PR은 워크플로·Worker·웹을 변경하지 않는다. 파일이 없거나 state가NA이면 UI도NA로 표시한다. 서버에서 개인 Sheet·기기 계산 값을 채우지 않는다.

합성 SEC·BLS/BEA/Treasury·Fed/MTS·13F를 사용해 정상/STALE/결측·출처 결속·사설 문자열/가격 필드 삽입·파일/tar 경계를 검사한다. 합성 참조 fixture를 실제 LIVE 자료로 배포하지 않는다. 실제 취득·화면 표시·504개 커버리지는 이 검증만으로 완료했다고 주장하지 않는다.
