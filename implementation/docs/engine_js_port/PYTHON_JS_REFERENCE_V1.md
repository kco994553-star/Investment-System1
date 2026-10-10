# 가격 계산 JS 이식 계약·합성 Python 참조 v1

코덱1은 `tests/fixtures/python_js_reference_v1.json`의36개 synthetic=true 사례를 JS 입력으로 적용하고 expected를 대조한다. fixture는 테스트 전용이며 가격·시총·역DCF·유형조정·선정 결과를 포함하므로 Pages에 복사하면 안 된다. 실제 종목/가격/검증기간·Holdout 자료는 없다. 날짜는 발행/취득 순서 실패 검사용 합성 입력이며 전진 검증 시작일이 아니다. JSON 원문에서 **숫자0과null을 구분**하고 bool을 숫자로 취급하지 않는다.

```sh
PYTHONPATH=implementation/src python implementation/tools/python_js_reference.py \
  implementation/tests/fixtures/python_js_reference_v1.json
PYTHONPATH=implementation/src python -m pytest -q implementation/tests/test_python_js_reference.py
```

이 도구는 synthetic=true 입력만 replay하는 테스트 하네스다. live serializer가 아니다. PYTHON 결과를 고정한 뒤 JS 비교는 코덱1 구현에서 수행한다; 이 PR은 JS 일치 성공을 주장하지 않는다. 숫자는 abs/relative1e−10 이내, key·enum·null·순서·사유 코드는 정확히 일치해야 한다. DCF math.fsum과 JS의 합산 차이는 수치 허용오차로 비교한다. 주요 금액/주식수는 JS binary64 안전 정수 범위 밖에서 정밀도를 잃을 수 있으므로 원본 Decimal/BigInt 처리 또는 NOT_AVAILABLE을 명시하며 자동 반올림하지 않는다.

## 진입점·출력

| operation | Python | 입력·출력 계약 |
| --- | --- | --- |
| dcf / reverse_dcf | qgv.dcf의two_stage_dcf / reverse_dcf | fixture.input의keyword args. FCFE_PER_SHARE/COST_OF_EQUITY·통화·주당 basis·confirmed gate. PV 및 이분법은 DCF_V1_PARAMETERS.md의동일 순서. 실패는null+고정 reason. 금융 기본값은비활성. |
| v_factors | qgv.price_value.calculate_v_price_factors | inputs→VPriceInputs, price는별도 인자. 승인v1raw_map만 적용; 자체multiple/업종·역사 기준·FCFE 도출은새로 만들지 않음. 결과 factor별score/state/reason. EPS fallback·supplied implied_growth=0을 진짜값으로 처리. |
| strategy | qgv.strategy_preview.recalculate_strategy_preview | observations[factor_id]={score,quality}, user_weights optional, profile_kind. input score는0..100/결측null. 각 축 비중 복사본에 sparse override 후 합100검증; 오류는 테스트 wire에서INVALID_INPUT. PREVIEW이며 Q/G평균과V별도, 부모 비중추정 금지. |
| company_types | qgv.company_types.calculate_company_types | metrics/original_qgv/config 명시 공급. dividend_yield는가격 경로에서같은통화/주식basis 확인후계산한ratio;5년지급gate는bool. 가치할인ramp 미확정은NA. 설정은compile_custom_config로PREVIEW, 공식결과승격 금지. |
| m3_sec | providers.sec_m3_adapter.build_sec_m3_input | SEC 원본body UTF8문자열→bytes,UTC aware datetime,optional cover XML/accession/acquired. exactCIK/exchange/ticker/covercontext 확인. single ticker로singleclass 추정 금지. 명시다중종류는SHARE_CLASS_BASIS표시만, 단순수치불일치는COVER_FACT_MISMATCH. |
| m3_universe | universe.private_subset의parse/prepare/compare/select | values Acode/Bmarketcap/Cprice와SEC식별입력. synthetic receipt SHA는sort_keys+compact+ensure_ascii JSON UTF8. 확정quality10%, N은fixture명시(실기기기본20). 선택은검증된후보만;전체커버리지/공식순위아님. |

원본 PythonAPI 결과의dataclass·enum·tuple·Mapping을 하네스가JSONobject/string/array로 projection한다. m3_sec는 원본receipt를가격과합쳐공개하지 않고 state/reasons/shares/basis/listingID의테스트결과만 비교한다. 타입은 #135에 구현/26E GSQ-017 기록이 같이 있어서 승인 대기다. 승인 전 canonical Python은 해당5사례에서 TYPE_ENGINE_PENDING_MERGE를 반환하고 테스트는 그 의존성 차단을 검증한다. **나머지31사례는canonical Python참조값 대조**, 타입5사례는 #135의Python참조에서 생성/검증했다. 타입fixtures의config를기기공식설정으로자동채택하지 않는다.

## JS 정밀도·기존 산식의 주의점

- Strategy Python round(x,4)는nearest ties-to-even이다. JavaScript Math.round를대체로쓰지말고 동일라운딩과예상값을확인한다. 결측은 reducer의기존분모를유지하며남은요소로재정규화하지 않는다. 금융profile NOT_APPLICABLE은일반결측과구분한다.
- M3의relative_difference=abs(G−R)/R에서 R=SECshares×price. mismatch는 **>=0.10**으로경계포함. Python은str(number)의정확유리수로경계를판정한다. JS도공급10진표현의정수교차곱을BigInt로판정하여0.1의binary오차로경계가달라지지않게한다. 정렬key는기존unrounded R이며 SHARE_CLASS_BASIS는R로자동보정하지 않는다.
- 종류별shares를합산하거나ADR/split을추정하지않는다. 동일issuer중복은기존selection규칙으로처리한다. rowlimit/미확인row는partialcoverage로보존;missingprice/blankPSKY는0이아니다.
- Type 소속도ramp clip0..1·최소0.3·상위최대3·cyc/def높은쪽·한번15..60clamp후합100재정규화의승인순서를보존한다. 배당5년gateFalse는0,unknown은NA. 성장+가치동시허용,가치비교기준은미확정이다.
- 원QGV·조정QGV·설정version·metrics근거를보존한다. QGV/Model/TSV/QGV-v2 입력을연결하지않는다. 현공식leafweight와유형부모weight는다른단계다.

## 파일 경계

JS는웹/Worker담당코덱1이작성한다. 이PR은워크플로·웹·Worker를변경하지않는다. 테스트벡터·가격계산출력·기기선정/별표/SheetID/로그인정보는공개producer입력이나백업에넣지않는다. 공개SEC식별asset은#134의가격없는별도projection이며bodyhash를다시pack하면originalSHA와repackedSHA를구분한다.

## #135 병합 후 상태 (2026-10-10)

사용자 승인과 필수 체크 성공 후 #135가 병합되어 타입5사례도 canonical Python으로 replay한다. 전체36개 합성 expected를 대조할 수 있으며 fixture의 type_dependency=PR135_APPROVAL_PENDING은 생성 당시 이력이지 현재 런타임 차단 플래그가 아니다. SIC 표는 별도 사용자 확인 전 비활성, 경기민감·방어는 NOT_AVAILABLE다. JS 구현/실제 parity와 금융 기본값 채택은 여전히 별도다.

## JS 대조 결과 (#150)

`engine-preview.js`가 36개 사례 전부(유형 5개 포함)를 Node와 브라우저에서 대조 PASS한다. 유형 JS는 `compileCustomTypeConfig`로 만든 PREVIEW 핸들만 받으며 공식 라벨을 붙여도 승격되지 않는다. 공식 v1 설정 로딩·화면 연결은 B9 후속이다.
