# 현재 인수인계 — Codex 2026-10-13

최신 사용자 결정은 [WORKING_RULES.md](WORKING_RULES.md)와 이 절에 적용한다. 아래 이전 인수인계는 역사이며 현재 열린 PR·결정·배포 상태를 대체하지 않는다.

## 현재 위치

- canonical: `claude/investment-system-top500-validation-alrugm`, 확인 HEAD `6717c896`(#229 병합, 2026-10-13 14:59:17 UTC).
- **#222 GSQ-022/023 병합 완료**: exact head `d25161e4`, 필수 6체크 SUCCESS·실패 0에서 정상 merge. force/admin 없음. 별도 수동 배포·Worker 배포는 실행하지 않았다.
- 기존 승인 병합 순서: **#222 → #224 → #226 → #225 → #210 → #215 → #211**. 새 레인 PR: D → A → B → C → E. 모든 병합은 D가 한 건씩 수행한다.
- **#224 병합 완료**: exact head `39b474c3`, 필수6 SUCCESS/실패0, normal merge `84998f27`. A가 업종 하위 지표 표본<8 GENERAL 전체분포 대체 규칙과 회귀 테스트 확인. canonical merge-forward 후 head `39b474c3` push 후 CI 성공 확인하여 병합.
- **#226 병합 완료**: exact head `66e59f9b`, 필수6 SUCCESS/실패0, normal merge `8382b1b5`. B의 10/13 승인 해석 commit `80cb2fdc`를 normal cherry-pick, 가드 해시 갱신하여 head `66e59f9b` push. Python playbook·Pages guard 50PASS, JS225PASS.  #224 기준 동기화·CI 성공 후 병합. Integral SIC 숫자표현 일치 followup은 B 화면 브랜치에 포함.
- **#225 병합 완료**: exact head `1b1cf960`, 필수6 SUCCESS/실패0, normal merge `c08faa15`(12:40:49 UTC). Prices_D/M 코드 승인 범위; Worker 배포는 별도.
- **#210 병합 완료**: exact head `8cead6ac`, 필수6 SUCCESS/실패0, normal merge `7136aa3f`(13:11:19 UTC). 당시 다음은 #215 → #211. 현재 #211까지 모두 완료.
- **#215 병합 완료**: exact head `0b4151a5`, 필수6 SUCCESS/실패0, normal merge `7a3745d5`(13:47:22 UTC). 당시 다음은 #211, 현재 모두 완료. 모든 레인 정상 merge-forward/최신 CI 진행.
- **#211 병합 완료**: exact head `67726de4`, 필수6 SUCCESS/실패0, normal merge `e048963f`(14:07:31 UTC). 기존 사용자 승인 7개 순서 전부 완료. DART 실 Secret 연결 성공은 다음 수집 실행 전 미확인; 코드/오프라인 계보 검증만 완료.
- **#230 D 정리/가드 병합 완료**: exact head `bff1f4df`, 필수6 SUCCESS/실패0, normal merge `4976092b`(14:28:38 UTC). 저장소/Pages 이메일 패턴 차단, 정확 공개 역사만 보존. Worker #229까지 병합 완료. #236은 최종 인수인계 문서 PR로 보존한다.
- **#227 수정본 → #237 clean 대체 PR**: canonical6717 기반 완성 소스를 신규 브랜치로 보존. 원래227의 post-session 테스트 버전은 이메일 history 검사에 걸려 예외/force 없이 [#237](https://github.com/kco994553-star/Investment-System1/pull/237)로 대체했으며 원래 브랜치/이력은 그대로 유지한다. Actions 로고 PNG 번들·직접 iframe OFF 구현. PNG 실제 decode/RGBA8 재인코딩 및 잘못된 raster/bitdepth/tRNS 회귀15PASS·E 재검토 중요 문제0. 로고/iframe390·1280 각2PASS. 새HEAD `639a59bf`의 privacy/email48records 위반0·Node50·Pages91·Python93+125sub·로고/iframe/잔고6브라우저 PASS, 필수6 모두 SUCCESS·deploy SKIPPED이며 **#237 수정본 병합 재승인 필요**. KRX/TSE 지원은 확인 불가, 외부 지원 조사 없음.
- DART 키 등록 사용자 확인됨. C 보고: 최신 실행 BEA_USERID 설정 마스킹 정상; 예전 빈 전달 로그를 근거로 재등록 요청하지 않는다. Fed 원인404/빈 추출, 공식 소스확인403이며 반복 시도 금지.
- **#229 Worker 확대 병합 완료**: exact head `9cbbdeb3`, 필수6 SUCCESS·실패0, normal merge `6717c896`(14:59:17 UTC). Universe504(하이픈 포함)·HYG·IEF는 사용자 승인 범위 그대로. 최신 집중검사189+262subtests·합성504 PriceStore·Worker169·잔고 KO 허용/QQQ 차단·credential-free Wrangler dry-run PASS. 실제504 가격 수집·Worker 배포는 실행하지 않았다. 별도 배포 결정 전 기존 Pages·Worker 유지.
- **10/19 v2 기록 시작은 아직 확정하지 못함**. A의 V·공개입력·v1/v2 원장 준비와 신규 PR 승인 후 실제 시작일을 보고한다. 소급하지 않는다.

## 로컬 통합 미리보기 검증

`codex/integration-review-20261013`의 frozen HEAD `de061f31`에 A#234·B#233·C#235·E#231·수정#227(현재clean대체#237) 및 canonical6717을 로컬 통합했다. 원격 push·canonical 병합·배포 없이 검증하며, 합성 입력의 결과를 실제 외부 수집 성공으로 표현하지 않는다.

- 공개 산출물97·정적83·실제SHA/최신 가드 PASS. MAX_ENTRIES128은 수정227/통합 미리보기에만 적용한다.
- B 실제 normalboot390/1280: 19종목 패널·유효 TARGET15·EUR 자료/USD 가격 거절·백업4 PASS. 가격값은 RAM에서만 계산한다.
- C5 실제 normalboot390/1280: 같은 TTM·원자료 SHA 일치 양성 및 기간/SHA 불일치 음성 총6 PASS.
- 실제 통합 A/C DART 원장 Python/JS 동등 계산·원파일 bytesSHA·v1 불변·NA 사례 PASS, Worker169 PASS.
- frozen 통합 전체 Python **2917PASS+271subtests**(143.76초)·실패0, CI와 같은 Node22.23.3의 **54 manifest PASS**·실패0. 전체 브라우저 **60고유파일 PASS**(최초59PASS/1FAIL 뒤 QGV 엄격 classifier/basis 회귀를 강화하여 해당1파일을 Node22.23.3에서 v1/v2×390/1280 **4/4PASS** 재검증). runtime artifact는 de061f31과 byte 동일, 강화 test source는32e8e020이다.

## 레인별 진행 (진행분은 브랜치·PR로 보존)

| 레인 | 완료 | 진행 | 대기·막힘 | 다음 |
| --- | --- | --- | --- | --- |
| A QGV v2 | #224 Q/G 병합, V·원장2·분리된 v2 기기 V이력·#18 strict6FY·한미 optional reference 구현 | #234 d20a895c: cfg/engine 필수2script 로드로 B 화면 유무와 관계없이 같은 분류 적용. 최신 Node22 manifest51·브라우저55/55·M2 4/4·standalone/통합 QGV4+4·Worker169·Pages91/static79·가드47+125sub PASS | 새 계산/공개 PR 승인; 앞선 head 원격 build 실패의 파일명 관측을 보완, 최신d20의 필수6 SUCCESS를 독립 GitHub Connector check-runs로 확인. 조건 완화 없음. 실제 품질224/504(3/7샤드), Q207/G222 | 10/19 실제 시작 미확정. #18 213코드/210발행사·#19 3PASS/3FAIL/13NA, 준비일부터 소급 없이 |
| B 플레이북 | #226 engine 병합; 19패널·백업4·E5·R1/W1·정보E4·채점 준비; RAM 내비게이션/통화 일치·quota 역순 rollback 수정 | #233 df19f835 필수6 SUCCESS: exactcanonical6717 반영, Node18·backup10·engine11 및 실제 normalboot390/1280 PASS | B6 초안 편집 준비·최종저장 A#234/v2입력 선행, B-1 휴장일 채점 NA | A 선행 및 마지막 canonical 동기화6 확인 뒤 화면 PR 병합 |
| C 데이터·매크로 | #210/#215/#211 병합; DART6FY 같은 v2 API·5경고등·TTM 날짜/해시·운영 연결·한미 원장 bridge 준비 | #235 8430ef62 필수6 SUCCESS: Py2833+273sub·Node52·390/1280브라우저12·strict55records/email0 PASS | Fed 공식 소스403; 실 DART Secret 첫수집 NOT_RUN. 실제 과거 매크로 2/5만 재생, full5 NOT_RUN | 공개입력/워크플로 승인 및 A 선행. old #232는 대체 PR 링크로 닫고 이력 보존 |
| D 운영 | 기존 승인7개 순서 및 #230·#229 병합; D4 기존6테스트 PASS·레거시9종 등록 유지·삭제0 | #236 최종 문서·안전한 CI 실패파일 진단2개·공용 핀·각 레인 canonical 동기화; 로컬 통합 preview de061f31(97파일/83정적) 가드 PASS | #237(#227 수정본) 재승인·별도 배포 D-DEPLOY. 통합2917+271sub·Node54·브라우저60고유파일·97파일 가드 PASS | guard240+262sub/E 독립84+137·우회/긴토큰 검증 PASS. 정확HEAD6 후 #236 병합 |
| E 13F·테마·Universe | E1/E4/E5 기존 구현 검증; Frozen6808/6808+실 privateRelease 존재/크기/digest 확인 | #231 1061e605 canonical6717 동기화·필수6 SUCCESS; 변경공용47+125sub·이전270+262sub·Node49 PASS, 새6 SUCCESS | E2 공개경계 승인 전 W2 기관수 NA/13F E4 비활성 | 최신6 유지. Release 무만료·artifact만 2026-12-26 만료 |

## 열린 PR 실제 상태 (2026-10-13 마지막 원격 관측)

필수 체크는 repository-guard / ingest-and-gate / build / validate / guard / presentation. 역사 base의 0/6은 그 당시 별도 체크의 실패를 뜻하지 않는다. 최신 체크를 다시 조회한 뒤 병합하며, 과거 PR은 자동 닫지 않는다.

| PR | HEAD | 필수 체크 | 충돌 | 권장 | 이유 |
| --- | --- | --- | --- | --- | --- |
| #237 | `639a59bf` | 6/6 | MERGEABLE | #227 수정본 재승인 | 같은 완성소스·엄격 이메일 가드 PASS의 clean 대체 |
| #236 | `이 PR 최종 HEAD` | 문서 갱신 뒤 재검사 | canonical6717 동기화 | 6체크 후 정리 병합 | 최종 문서·CI 실패파일 진단만; 산식/체크조건/YAML 변경 없음 |
| #235 | `8430ef62` | 6/6 | MERGEABLE | 공개/워크플로 승인 대기 | DART6FY·macro·TTM 계보, clean235로 old232 대체 |
| #234 | `d20a895c` | 6/6 | MERGEABLE | 계산/공개 승인 대기 | 기본v2 이미 결정됨; 새 V/원장2/공개 descriptor |
| #233 | `df19f835` | 6/6 | MERGEABLE | 6체크/A 선행 후 화면 병합 | canonical6717와 RAM 가격/통화 fix 최종반영 |
| #231 | `1061e605` | 6/6 | MERGEABLE | 공개 승인 대기 | SEC13F 원값, 가격 변환·개인 보유 없음 |
| #227 | `68d8cf11` | 과거6/6 | CONFLICTING | 보존·병합 금지 | #237 clean 수정본 대체. 역사/브랜치 유지 |
| #71 | `923ba8ea` | 5/6 | CONFLICTING | 유지 | 과거 별도 base; 자동 병합·닫기 권한 없음 |
| #43 | `4c5f7ff9` | 0/6 | MERGEABLE | 유지 | 과거 별도 base; 자동 병합·닫기 권한 없음 |
| #31 | `c9e0fa7e` | 1/6 | MERGEABLE | 유지 | 과거 별도 base; 자동 병합·닫기 권한 없음 |
| #29 | `d0444583` | 0/6 | MERGEABLE | 유지 | 과거 별도 base; 자동 병합·닫기 권한 없음 |
| #19 | `c3dbf8a0` | 0/6 | MERGEABLE | 유지 | 과거 별도 base; 자동 병합·닫기 권한 없음 |
| #18 | `2c088cea` | 0/6 | MERGEABLE | 유지 | 과거 별도 base; 자동 병합·닫기 권한 없음 |
| #17 | `21039a0a` | 0/6 | MERGEABLE | 유지 | 과거 별도 base; 자동 병합·닫기 권한 없음 |
| #16 | `ef65caa5` | 0/6 | MERGEABLE | 유지 | 과거 별도 base; 자동 병합·닫기 권한 없음 |
| #15 | `ce587040` | 0/6 | MERGEABLE | 유지 | 과거 별도 base; 자동 병합·닫기 권한 없음 |
| #14 | `0d48d863` | 0/6 | MERGEABLE | 유지 | 과거 별도 base; 자동 병합·닫기 권한 없음 |
| #13 | `8bb990bd` | 0/6 | MERGEABLE | 유지 | 과거 별도 base; 자동 병합·닫기 권한 없음 |
| #12 | `61d3352d` | 0/6 | MERGEABLE | 유지 | 과거 별도 base; 자동 병합·닫기 권한 없음 |
| #11 | `a2e0790d` | 0/6 | MERGEABLE | 유지 | 과거 별도 base; 자동 병합·닫기 권한 없음 |
| #10 | `5eec129e` | 0/6 | MERGEABLE | 유지 | 과거 별도 base; 자동 병합·닫기 권한 없음 |
| #7 | `a013f1c1` | 0/6 | MERGEABLE | 유지 | 과거 별도 base; 자동 병합·닫기 권한 없음 |
| #4 | `ff78c4f6` | 1/6 | CONFLICTING | 유지 | 과거 별도 base; 자동 병합·닫기 권한 없음 |

**#228→#236, #232→#235 대체 정리 완료**: 두 PR은 10/13 닫고 각 본문에 대체 링크·사유를 남겼다. 브랜치·커밋 이력 삭제 없음. #152·#153은 #178 대체로 이미 닫힘(10/11 기록). 기존 레거시9종 app_nav_ia / device_actual / google_sheet_storage / manual_quotes / prompt_field_guide / web_mvp / web_research_guard / web_state_presentation / global_language_search 모두 현행 CI manifest에 등록됨. 삭제 없음; 현재 UI 검증을 수행한다.

## 사용자 결정 대기

[USER_DECISIONS_PENDING.md](implementation/docs/USER_DECISIONS_PENDING.md)에 남은 결정만 기록한다. 승인된 기존 PR 순서·플레이북26건·DART 등록·Worker 확대는 다시 대기 질문하지 않는다. 신규 계산·워크플로·공개경계·외부연결·GSQ PR은 완성본 승인, #227은 수정본 재승인. 테스트/문서/화면만이면 필수6체크로 자체 병합 가능. CI 원격 전용 실패에는 테스트 조건을 완화하지 않고 실패 manifest명/종료코드·M2 phase/error.name만 annotation한다. shell exit/첫 실패 중단4경계 및 M2 runtime canary 미노출/exit1 회귀 PASS.

## 원격 접근 상태

GitHub CLI는 10/13 조회에서 HTTP401 Bad credentials로 막혔다. 값 출력·같은 인증 경로 반복 시도 없음. 독립된 기존 GitHub Connector는 정상 인증되므로 원격 조회·완성된 문서/테스트 진단 게시·정확HEAD6 확인은 그 연결로 이어간다. 새 Secret·외부 허용 범위·역사 예외는 추가하지 않는다. 원격 #236 기존8ebd4b73의6SUCCESS는 이후 로컬 변경의 CI 성공으로 간주하지 않으며, 게시된 새HEAD에서 다시 검사한다.

## 다음 할 일 5개

1. #236 최종 문서·CI 진단4파일을 동일 검증 blob으로 push하고 최신6 성공 후 자체 병합. 각 레인 canonical 재동기화/최신6 확인; C manifest의 중복2node/2browser도 D가 정리.
2. 로컬 통합2917+271sub·Node54·60고유브라우저·Worker169·97파일 가드 및 실제 RAM/TARGET/C5/DART원장 연결 PASS. 검증 이력/부분 재검증을 보존하며 실제main으로 통합 병합하거나 배포하지 않는다.
3. A#234 새 계산/공개·C#235 수집/공개·E#231 공개·#227 clean 수정본#237 재승인 요청. 승인 순서 A→B→C→E, B 화면 PR은 선행 A와 필수6 성공 뒤 자체병합 가능.
4. Fed403/실 DART 첫 실행/전체504와 실제 매크로full5 재생 미완료는 원인·범위를 보존하고 같은 외부 실패 재시도 금지. 10/19 실제 시작은 준비/승인/배포 확인 후 정하며 소급 금지.
5. 남은 결정 B-1·A-V2·C-MACRO·E-13F·D-227·D-DEPLOY만 유지. Worker 범위/키 등록/v2 기본/기기 V이력 저장 승인 재요청 없음.

---

# 이전 인수인계 (과거 기록·현재 운영 기준 아님)

이하 내용은 이전 세션의 과거 기록이다. 예전의 등록 대기·알림 전 호출 금지·BEA 재등록·미승인 상태를 현행 운영에 재적용하지 않는다. **DART_API_KEY는 사용자 등록 완료 확인, 실제 Secret 수집 Actions는 NOT_RUN. BEA_USERID는 최신 SET_MASKED·재등록 불필요.** 현재 승인·완료·대기 6건은 이 파일 첫 절과 USER_DECISIONS_PENDING.md만 따른다.

# 현재 인수인계 — 2026-10-13 (Claude Code 메인 개발)

## 현재 위치 (2026-10-13 세션 종료 시점, 여기서 이어받기)

이 세션은 사용자 지시로 여기서 종료했다. 아래 PR은 모두 **열려 있고 병합되지 않았다**. 끝나지 않은 에이전트 작업은 각 브랜치에 `WIP:` 커밋으로 push했다. push되지 않았으면 그 브랜치에는 진행분이 없다.

### 최신 지시 (우선순위, 2026-10-13)
1. **기초 데이터**
   - V 계산 조건(PLAYBOOK 13-1)
   - QGV v2 계산(13-11·14). v2를 기본으로, v1은 비교용으로 함께 기록한다. 준비된 날부터 전환하고 소급 계산하지 않는다. 가능하면 10-19 전.
   - DART 연결(#211 마무리, 13-7). 키·권한·형식 문제로 막히면 원인만 보고하고 미국 작업을 계속한다. 같은 문제로 반복 시도하지 않는다.
2. 매크로 경고등 5개 + U3(13-5).
3. 나머지 플레이북: 11절, 0-1절 핵심 v0, 15·16절.
- 문서 기준·문구는 바꾸지 않는다. 모순·빈 곳은 목록으로 보고한다.
- 숫자는 설정 파일에 넣고 v0 · UNCALIBRATED로 표시한다.
- 병합은 사용자 승인 후. 보고는 한국어 5줄 요약 + 사용자가 결정할 것만 번호로.
- 10-17에 10-19 시작 방식을 판단해 보고한다(아래 2가지 중 하나).
  - v2가 10-18까지 준비되면 → 10-19에 v2로 가상거래 시작.
  - 준비되지 않으면 → 10-19부터 원장에 v1·v2를 함께 기록하고, 가상거래는 v2 준비일에 시작.

### 열린 PR (승인 대기, 권장 병합 순서)
| PR | 브랜치 | 내용 | 상태 |
|---|---|---|---|
| #222 | claude/gsq-022-qgv-v2-default | GSQ-022(v2 기본·v1·v2 재정규화 50%·next_3_5y_growth 정의) / GSQ-023(가격 저장: RAM + 개인 시트) — 26E | 승인 필요 |
| #225 | claude/prices-tab-store | 개인 시트 `Prices_D`·`Prices_M` 증분 저장, 크기·속도 보고(약 40만 셀, 4%) | 승인 필요(GSQ-023) |
| #227 | claude/tradingview-widgets | TradingView 위젯 + 기업 로고 + `universe-domains.json`, CSP 확장 | 승인 필요(CSP). TSE 8035 = 표시 안 됨(제3자 근거), KRX 042700 = 미확인 |
| #210 → #215 → #211 | 8-K / GDELT·IR / DART | 공시·뉴스·DART | 승인 필요. 병합은 이 순서로 |

- **#211 (DART):** 10-13에 기준 브랜치를 합쳤다(head 10cc7710).
  - 부채 정의를 단기 + 장기(유동성 포함) + 사채 + 리스로 바꿨다.
  - pytest·노드·브라우저 51/51 통과.
  - 컨테이너에서 opendart에 접속할 수 없어 실데이터는 병합 후 첫 실행에서 확인한다.
  - 한국 종목 '참고 순위'(미국 504 분포 대입)는 #224 병합 후 붙인다.

### 진행 중이던 작업 (이어서 할 일)
- **V(기기) + 종합 점수 + v1·v2 재정규화 + `scoring_default`** — 브랜치 `claude/qgv-v2-v-device` @ 8a2429b2 (마지막 커밋은 WIP), **PR 아직 없음**
  - 완료:
    - v2 V 요인 5개, 축·종합·프리셋, `value_trap_gate`
    - v1·v2 50% 재정규화, 13-1 v1 V 조건, v2 경기민감 정상화 이익
    - 점수 접근자 하나로 통합, '임시 기본' 표시
  - 테스트(58243267 기준): pytest 2606, node 46, guard PASS(81), 브라우저 51개 중 `virtual_trading_rehearsal_browser_test` 1개 실패.
    - 실패 원인: 13-1 조건이 바뀌어 V가 기록되는데, 테스트는 아직 예전 기대값 `V_CORE_FACTOR_MISSING`을 쓴다.
  - **다음:**
    - 그 테스트 기대값을 13-1에 맞게 고치고 PR을 연다(#224 다음 순서).
    - v1 경기민감 정상화 이익 반영.
    - 공개 입력에 매출·영업이익률 이력이 없어 v2 정상화 이익은 실제로 항상 NA다.
    - 금융사 V 정의 없음.
    - 자기 과거 대비 요인은 PriceStore(#225) 병합 후.
  - v2로 전환하려면 `scoring-default.js`에서 `{scoring_default:'v2', v2_since:'YYYY-MM-DD'}` 한 줄을 바꾼다(#222 승인 후).
- **매크로 경고등 v1** — 브랜치 `claude/macro-lights-v1` @ 2512bdbf (WIP), **PR 아직 없음**
  - 완료:
    - Python·JS 순수 함수, 벡터 59개 JS==Python
    - 재무부 일일 금리 곡선 수집기
    - 공개 경고등(고용·물가·곡선), 기기 SPY 시장 경고등(RAM만)
    - 매크로 화면 카드, `MacroLights.current()`, 재생 도구
  - 테스트: pytest 2668, node 44, guard PASS(77), 브라우저는 pwa(로컬 Playwright 1.56)를 빼고 모두 통과.
  - **다음:**
    - 저장소 가드 diff 실행.
    - PR 열기. 본문 초안은 `implementation/docs/handoff/MACRO_LIGHTS_V1_PR_BODY_DRAFT.md`.
    - 신용 경고등은 Worker에 HYG·IEF를 추가해야 하고, 이건 별도 승인이 필요하다.
  - 재생 요약(가격 파생값이라 공개 금지, 사용자에게만 보고됨): 평온한 시기에도 시장+신용이 동시에 켜져 위기로 잘못 판정된 사례가 있다(2015-10, 2016-01·02, 2018-12, 2025-04). 기준 점검이 필요하다.
- **플레이북 핵심 v0 화면·기록** — 브랜치 `claude/playbook-v1-screens`
  - **진행분 없음.** #226 끝 커밋(7cd7ff87)과 같다. 다시 시작해야 한다.
  - 범위: 산 이유·무효화 조건(모든 보유 종목 필수), 판단 칩 → 플레이북 패널, AI 프롬프트(10절 원문), 기록·백업·E5, TARGET v1 작성 화면, 16절 한도.
  - 출발점:
    - 판단 칩은 `virtual-trading.js`의 `judgementHtml`을 `portfolio-screen.js`와 `daily-report.js`가 쓴다.
    - 백업 형식은 `device-backup.js`의 `investment-device-backup/3`이다. 기록을 넣으려면 `/4`로 올리고 `/1`~`/3` 가져오기를 유지한다.

### 아직 시작하지 않은 작업
- S13 전략 프로필 v2(QGV_V2_CANDIDATE §3~§6, 과거 성과는 수익률·MDD를 함께 표시, PIT만, Holdout 제외).
- 화면 보완 5-1~5-4: S06 '내 시총 순위(기기 계산)'·빈 상태, 요인 상세 한국어, 내부 값 라벨, S10 연구 프롬프트.
- Worker 허용 목록 확장 PR(승인 필요): 504종목(`-` 허용, Prices 월말용)과 HYG·IEF(신용 경고등).
- Fed DDP 패키지 ID·H15 경로 수정(예전 값이라 404·빈 HTML), BEA 수집 방식 로그 추가.
- 전진검증 원장에 v1·v2 동시 기록(공개 데이터, 승인 필요).

### 사용자 결정 대기 (10-13 보고 기준)
1. 승인 병합: #222 → #224 → #226 / #225 / #227 / #210 → #215 → #211.
2. Worker 허용 목록 확장 PR을 만들지(504종목, HYG·IEF).
3. 플레이북 빈 곳 6가지:
   - R2 Q·G 하락의 비교 기간
   - W1을 핵심으로 둘지
   - v2 상대적 하락 → E4(후보 코드)를 화면에 보일지
   - 무효화 시 확신 해제 시점(8절 대 3절)
   - 6-2 경기민감·경기방어 후보 업종군
   - 매크로 자료 0/5일 때 확대를 막을지
4. #227:
   - TradingView 스크립트 방식과 iframe 방식 중 무엇을 쓸지
   - 로고·위젯 기본값을 켜짐으로 둘지(화면 종목이 제3자에 전달됨)
5. #224·#211 본문의 개별 질문.

### 주의 사항
- **이메일 노출 시도:** 10-13에 SEC 접속 확인 중 요청 헤더(User-Agent)에 사용자 이메일을 넣은 일이 2번 있었다(메인 1, 에이전트 1). 둘 다 프록시가 연결 전에 막아 외부로 나가지 않았다. 컨테이너에서는 sec.gov·github.io·wikidata·opendart·tradingview가 모두 막혀 있다.
- **Pages 가드:** `files_scanned`·`ALLOWED_NAMES` 한 줄·해시 고정은 PR마다 바뀐다. 병합 순서에 따라 재고정이 필요하다.
- **브라우저 테스트 로컬 실행:** `build_pages_cockpit.py --out <dir>` → `http.server` → `PAGES_COCKPIT_URL`과 `PRIVATE_HISTORY_URL` 지정 → 각 테스트를 node로 실행.

---

## 이전 판 — 2026-10-11

메인 개발은 Claude Code가 맡는다(이전 코덱1·코덱2 역할 통합). 사용량이 떨어지면 이 파일만 보고 코덱스가 이어받을 수 있게 단위가 끝날 때마다 갱신한다. 이전 판(#155)의 상세 이력은 Git에 있다.

## 현재 위치 (중단 시 여기서 이어받기)

- 작업 방식: 기능 단위 PR, 독립 작업은 서브에이전트 최대 3개가 각자 worktree·브랜치에서 병렬 진행, 진척마다 push, 병합 때마다 이 절 갱신.
- 로컬 검증 도구(세션 scratchpad, 없으면 재작성): `pin_assets.sh`(가드 해시·files_scanned), `ci_local.sh`(필수 CI 동등 실행), `run_browser.sh`, `pytest_full.sh`(py3.12). Playwright는 1.58.2.
- 이번 세션 추가 병합: #161 S03·S04·S05, #162 py3.13 호환+백업 `/3`(투자자 ★), #163 ROADMAP 상태+[사용자 결정 대기 목록](implementation/docs/USER_DECISIONS_PENDING.md), #164 S06·S07·S11·S13, #166 S08 지표 6카드·S09·S10 세부, #167 레거시 테스트 10종 복구+문구 현지화.
- 로컬 통합 도구 추가: `integrate.sh <worktree> <branch>`(canonical 병합 → 실제 충돌이면 중단 → 가드·테스트 목록 합집합 재고정 → 빈 화면 fixture 재생성 → 전체 pytest 깨끗할 때만 커밋·push).
- **2026-10-11 병합(모두 필수 체크 성공):** #156 CI manifest, #165 공개 유형 metrics, #169 원자료 비공개 Release 워크플로, #171 시간대 테스트, #172 가상매매·일일보고서 문서·S17 명세·D-22 초안, #173 13F 운용사 v0 10곳, **#175 실데이터 배포 빌드에서 멈추던 빈 상태 테스트 수정**(10-10 22:24 SEC 일일·10-11 첫 수동 배포 실패 원인), #174 M3 Universe504 주식수 공개 JSON, #176 DCF v1 기본값·FCFE 공개 입력·기기 역DCF, #177 매크로 v0 Growth·Inflation, #178 SIC 업종군 v0·테마 v0·집중 경고 40%, #180 가상매매 엔진 v1(PROVISIONAL, 시작일 미정이라 기록 없음)·S17 일일보고서 2화면·금액 숨김, #181 인수인계, #183 전진검증 원장 v1(10-19 시작, 추가 전용·워크플로 연결·Pages 가드 항목 상한 96).
- **2026-10-11 오후 병합:** #185 원자료 사본 기록(6808/6808 PASS, DURABLE_COPY_PRESENT), #187 D-22·시작일 10-19, #188 M3 경제적 동일 종류 합산 v0. **사용자 승인 병합(순서대로):** #170 GSQ-020 → #179 GSQ-018·019 → #182 AI 우체통 → #186 Worker 벤치마크 ETF 15종 → #189 DCF v1.1(IFRS·성장률 h·`BORROWING_PAIR_PARTIAL`) → #190 매크로 6축 원시 표시. 이어서 #194 가상매매 기기 실행기(Worker 일봉·환율·전진검증 Q·G → 장부, RAM 전용).
- **10-11 오후 2차 병합:** #191 Worker 환율(승인), #192 GSQ-021(승인), #193 M3 Alphabet Class B(승인), #194 가상매매 실행기, #195 인수인계, #196 D-5 실데이터 활성·V 기록·리허설, #197 장부 시트(D-10)·세트 B·내 TARGET·그림자 스냅샷, #198 PC 배치(1024px+). 닫음: #152·#153(대체됨).
- **배포:** Worker 수동 배포 38123761241 성공(08:08 UTC, #191 환율 포함). 검증: 출처 없음 403 `ORIGIN_FORBIDDEN`, 승인 출처·인증 없음 403 `AUTH_FORBIDDEN`. Pages는 SEC 일일 실행(22:17 UTC)에서 배포된다.
- **대기열 1(10-19 준비) 완료:** #196(D-5·V 기록·리허설), #197(장부 시트·세트 B·내 TARGET·그림자), #203(판단 7단계 일관성·코드 라벨 120개), #204(보유 캡처+개인 AI·Holdings 탭·범위 밖 보유·TEL Worker 종가). #200 뉴스 소스 비교 문서. #201은 저장소 가드(이력의 합성 보유 행) 때문에 닫고 #204로 재제출.
- **10-11 오후 3차 병합:** #202 universe-codes(승인), #205 SEC Universe504 일일 Q·G(승인), #207 판단 일관성 테스트 스텁, #208 화면 보완(S06 M3 순위·기업 검색·복원 알림·SEC 404·수집 상태·PWA), #209 GOOG 'Class C Capital Stock, $0.001 par value' 정확 문구(비공개 원자료 10-Q 2건으로 확인), #212 ⑫⑬⑪ 실제 계산, #213 S16 13F 분기 변화·S13 유형 커스텀, #214 가상매매 v2(시트 정본 이어서 계산·PRICE_REVISED·V 핵심 요인 NA·세트 A 예시/버전·세트 B·C·D·비교 탭·Example_ 탭 무시).
- **승인 대기 PR:** #210 SEC 8-K 공시(워크플로·공개), #211 DART 042700 재무·공시(워크플로·공개, `DART_API_KEY`), #215 GDELT·IR 뉴스(#210 위에 쌓음).
- **사용자 결정 대기:** V 핵심 요인 범위(현재 전부 핵심 → 기기 V 항상 NA), 비교 지표 최소 표본(10/20/20일), 세트 종목 ETF 허용 여부, ⑫ 공백 시 입금 처리(엔진 TWR과 차이), NYSE 휴장일 2028+ 확장, ASML 6-K 포함 여부, 리더보드 실적 '확인' 표시, DART 실패 시 배포 중단 여부·042700 Q·G 합치기·부채 정의, IR 제목 공개·연결 규칙 B·한국어/일본어 GDELT, 13F 공개 데이터 보강(제출일·미변동 보유·보고 가치·발행사명·Eaton CUSIP), 수집 상태 기준(36시간/3시간).
- **10-11 22:25 SEC 일일 실행(run 38180399003):** 수집 단계 전부 성공(매크로 Growth·Inflation·Fiscal·Labor LIVE, Liquidity·Credit·Monetary Policy `SOURCE_NOT_AVAILABLE`; 13F 10곳 CIK 확인·비교 가능 1곳; 분류 LIVE; Universe 샤드 0 주식수 LIVE 82·Q·G 85; 원자료 업로드 성공; 전진검증 NOT_STARTED). 비밀값 노출 0건, 단 `BEA_USERID`가 빈 값으로 전달됨. 마지막 검증 단계에서 실데이터를 가정하지 않은 브라우저 테스트 2개가 실패해 **배포 안 됨** → #218로 수정(합성 실데이터 사이트에서 브라우저 테스트 50개 전부 통과 확인). #219로 Fed 실패 진단 로그(`MACRO_V0_FETCH`, 고정 토큰) 추가.
- **다음 할 일:** 사용자: `BEA_USERID` 시크릿 확인, 수동 SEC 일일 실행(배포) 여부 결정 → 다음 실행 로그로 Fed 경로 원인 보고 → 승인 시 #210 → #215 → #211 병합 → S07 '뉴스 무료 출처 미정' 문구 갱신·DART를 통합 목록으로.
- 알려진 제품 갭(결정 필요 아님, 후속 후보): 전체 검색이 기업을 내지 않음(GSQ-010 identity 디렉터리만), 백업 복원 후 ACTUAL 화면 알림 없음, `sec-public-inputs.json`은 SEC 수집 없는 빌드에서 404.

## 읽기 순서와 운영 경계

1. [WORKING_RULES.md](WORKING_RULES.md): 1인용 혼합 운영 규칙.
2. 이 파일: 실제 완료·미완료·의존·운영 상태.
3. [ROADMAP_2026Q4.md](implementation/docs/ROADMAP_2026Q4.md): 범위·연구 및 후속 정책. 진행 상태는 이 파일이 우선한다.
4. [DESIGN_CANVAS_SCREENS_v1.md](implementation/docs/cockpit_ia/DESIGN_CANVAS_SCREENS_v1.md): S01~S17 화면 정본.
5. 26E 결정 기록: [GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md](implementation/docs/pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md) GSQ-005~017.

병합 규칙(2026-10-10 사용자 지시): PR 단위로 push하고 **실행된 필수 체크 전부 성공·실패 0이면 자체 병합**. 단 **인증·배포·Worker·워크플로·공개 데이터 경계·26E 결정 기록 변경은 사용자 승인 후 병합**. force push·ruleset·AUTONOMY_MODE 변경(READ_ONLY 유지) 금지, 새 방법론·가중치·TARGET 임의 변경과 Holdout 사용 금지, 공개 저장소·Pages·Actions 로그에 가격·가격 파생값·개인 데이터 금지, Secret 값 출력 금지, 매수·매도·주문·이체 기능 금지, 결측은 NOT_AVAILABLE(0 대체 금지).

구조 원칙: 가격 불필요 공개 데이터는 Actions에서 Python으로 계산해 공개 JSON, 가격 필요 계산은 기기 JS(RAM 전용)로 하고 Python은 대조용 참조.

## canonical·배포 상태

- 저장소 `kco994553-star/Investment-System1`, canonical `claude/investment-system-top500-validation-alrugm`. 최신 HEAD는 GitHub에서 확인(이 문서 PR 직전 병합: #150 #151 #147 #122 #157 #158 #159 #160).
- Pages: https://kco994553-star.github.io/Investment-System1/ . 마지막 실제 배포는 여전히 **SEC run 38042681260(2026-10-10 09:52 UTC, #144 기준)**. #148 이후 병합분(프로필·엔진 이식·★·A2·B9·B10·C11)은 **아직 배포되지 않았다.** 배포(cockpit-pages workflow_dispatch 또는 SEC 일일 실행)는 사용자 승인 대상이며 이번 작업에서 실행하지 않았다. 다음 SEC 일일 실행(22:17 UTC)이 canonical을 빌드·배포하면 포함된다.
- Worker: 마지막 수동 배포 38034132303(07:21 UTC) 그대로. 변경·재배포 없음.
- SEC 매일: US TARGET 17개 범위 그대로. #145 504 분할 모듈은 workflow 미연결.

## 이번 세션 완료 (모두 필수 6체크 SUCCESS·실패 0 확인 후 병합)

| PR | 내용 |
| --- | --- |
| #150 | JS 엔진 이식 완료: DCF·역DCF·V·전략·M3·SEC 어댑터 + **기업 유형 JS**. #146 Python 참조 **36/36 대조 PASS**(Node·브라우저). locale `기업 유형 커스텀` 누락 해소 |
| #151 | ★·그룹·관심 기업 화면(S15)·리더보드 관심 필터. identity 기업 화면 제목은 티커(M2 계약) |
| #147 | 정본 색상·좁은 화면 줄바꿈, 12화면 390/1440 반응형 검사 |
| #122 | M3 '내 기기 기준' Universe 읽기·설정(시트 ID 기기 저장·백업 제외). SEC 주식수 입력 미연결 → `NOT_AVAILABLE · SEC_INPUTS_NOT_CONNECTED` |
| #157 | **A2** S01~S16 구조 정합: 흐름 번호 배지·QGV 소분류·S01 통합 판단/시스템/데이터 기준·S02 허브 4그룹+범례·**S14 모델 포트폴리오 신설(MODEL —)**·S08/S09/S10 배지·탭 |
| #158 | **B9** 전략 프로필 PREVIEW 재계산(공개 Q/G 요소, 공식 vs 내 프로필 Q·G·순위 변화, V NA) + **기업 유형 커스텀 편집기**(공식 type_config 내장 사본, 검증·기기 저장·백업) |
| #159 | **B10** 13F 읽기 경고·투자자별/종목별/겹침(NA)·투자자 ★(기기 전용) + 실적 '다음 예상 시기·확정일 아님'·S15 이번 주 실적 |
| #160 | **C11** 데이터 운영 상태 카드(설정): SEC 공개 입력 마지막 성공·실패 회사 수, 5개 화면 JSON 상태·STALE(각 파일 stale_after 기준) |

## 열린 PR

| PR | 상태 | 다음 단계 |
| --- | --- | --- |
| [#156](https://github.com/kco994553-star/Investment-System1/pull/156) | **[승인 필요] 워크플로 변경** draft. cockpit-pages·SEC 일일이 `implementation/tools/ci_node_tests.txt`·`ci_browser_tests.txt` manifest로 테스트 실행 + 전체 `pytest tests/` 단계 추가 | 사용자 승인 후 병합. 병합 후 이번 세션 새 테스트(design_responsive, design_canvas, profile_preview, thirteenf_filings, ops_status_node/browser, private_subset node/browser)를 manifest에 추가하는 작은 PR. 지금은 로컬에서만 실행·통과 확인 |
| [#152](https://github.com/kco994553-star/Investment-System1/pull/152) | draft. 테마 참고 메타데이터(14 바스켓 제안·ETF 티커)를 새 공개 파일로 표시 | 바스켓 승인 + 새 공개 파일(공개 데이터 경계) 승인 필요. 승인 후 canonical 병합·충돌 해소 |
| [#153](https://github.com/kco994553-star/Investment-System1/pull/153) | 과거 매크로 스냅샷 보존용 | 병합하지 않음 |
| #4~#71 | 과거 장기 draft·일반 PR | 수정·닫기·병합하지 않음(이전 판 표 참고) |

## 사용자 결정·조치 대기

1. **#156 워크플로 PR 병합 승인.**
2. **배포 승인**: #148 이후 앱 변경을 Pages에 배포(cockpit-pages workflow_dispatch). 또는 다음 SEC 일일 실행에 맡김.
3. **M3 SEC 주식수 공급 경로**(B8): (a) Actions가 Universe 코드별 SEC 주식수·basis(가격 없음)를 공개 JSON으로 제공(권장, 공개 데이터 경계 + 504 workflow 확장) 또는 (b) Worker SEC 중계(Worker 변경). 참고: 현재 공개 `sec-public-inputs.json`에 US17 reported_shares가 이미 있으나 M3 어댑터는 원본 body+SHA 검증을 요구한다.
4. **유형 지표 공개**(B9): `company-types-pricefree.json`에 가격 불필요 지표(revenue_cagr_3y·roic) 원값을 추가해야 기기에서 커스텀 유형 램프로 기업별 미리보기가 가능. 공개 데이터 경계 변경.
5. 기존 대기: SIC→업종군 매핑 확인, DCF 기본값, 매크로 8축 대응표, 테마 바스켓 승인(#152), 13F 추적 기관 집합, forward 시작 시점, **DART 등록 알림(10/11 18시 이후, 알림 전 착수 금지)**.

## 다음 할 일 — 장기 대기열(막히면 건너뛰고 의존 해소 시 복귀)

1. A1 PWA: 코드 완료. 실기기 설치 확인은 사용자.
2. A2 16화면: **완료(#157)**. 후속은 실데이터 연결 시 각 카드 채우기.
3. A3 프로필 골격: **완료(#148·#158)**.
4. A4 테마: #152 승인 대기.
5. A5 ★·그룹: **완료(#151)**.
6. B6 공개 JSON: 코드 연결 완료. 실제 정부/13F 입력·최신 앱 재배포는 사용자 결정(위 2·5).
7. B7 JS 이식: **완료(#150, 36/36)**.
8. B8 M3: 기기 읽기 완료(#122). SEC 주식수 공급 결정 대기(위 3).
9. B9 유형·전략: **완료(#158)**. 기업별 유형 미리보기는 위 4 대기.
10. B10 13F·실적·매크로: **완료(#159)**. 투자자 ★ 백업 포함은 후속(백업 schema 변경 필요).
11. C11 운영 상태 UI: **완료(#160)**.
12. C12 DART: 등록 알림 후 착수.

기타 후속: #156 병합 후 manifest에 새 테스트 등록. 레거시 브라우저 테스트 9종(app_nav_ia, device_actual, google_sheet_storage, manual_quotes, prompt_field_guide, web_mvp, web_research_guard, web_state_presentation, global_language_search)은 CI 미등록이며 현재 UI와 불일치로 실패 — 갱신 또는 정리 필요(삭제는 승인 후).

## 검증 방법

- 필수 체크: repository-guard, ingest-and-gate, build, validate, guard, presentation. deploy SKIPPED는 배포 아님.
- 전체 Python: `cd implementation && PYTHONPATH=src python3.12 -m pytest -q tests` → 2071 PASS(py3.12). Python 3.13에서는 3건(strategy_preview·sec_13f·scoring_standard의 3.13 특이 동작) 실패, `experiments/chart-contract` 9건은 고정 기준선 부재로 실패 — 둘 다 이번 변경과 무관.
- 로컬 Playwright는 CI와 같은 **playwright@1.58.2**를 써야 한다(1.56에서는 PWA 오프라인 테스트가 거짓 실패).
- 공개 산출물 해시는 `implementation/tools/pages_artifact_guard.py` APPROVED_SHA256에 고정. 웹 자산을 바꾸면 해시·`files_scanned`·`test_pages_cockpit_build.py` 파일 목록을 함께 갱신한다.

## 비밀값·외부 서비스 — 현행 설정 이름·상태 (2026-10-13 갱신)

| 서비스 | 상태 | 필요한 이름 | 저장 위치 |
| --- | --- | --- | --- |
| Cloudflare Worker | 위 실제 deploy SUCCESS, 본인 가격 경로 | ALLOWED_EMAIL, GOOGLE_CLIENT_ID, TIINGO_API_KEY, KRX_API_KEY | Worker: ALLOWED_EMAIL/TIINGO_API_KEY/KRX_API_KEY Secret, GOOGLE_CLIENT_ID Text; 값 기록 금지 |
| Worker 배포 Actions | 마지막 수동 deploy SUCCESS | CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID | GitHub Actions Secrets, 값/계정 ID 출력 금지 |
| Google OAuth/Drive/Picker/Sheets | API/scope/리퍼러 제한 키 설정 완료 사용자 통지; 첫 설정 코드 병합 | Google OAuth client ID, Picker browser key/app ID | 공개 제한된 앱 설정은 app-config.js, OAuth token RAM, 생성/선택 시트 ID 기기 설정만·백업 제외 |
| BEA | 최신 SEC 실행 SET_MASKED 확인·재등록 불필요. 수집 코드/매크로 v0 연결은 #235 승인 대기 | BEA_USERID | GitHub Actions Secret, 값 출력 금지 |
| SEC EDGAR | US17 manual SUCCESS·daily 등록 | SEC_USER_AGENT | GitHub Actions Secret, 값/이메일 출력 금지 |
| DART | 사용자 키 등록 완료 확인·#211 병합. 실제 Secret 수집 첫 Actions NOT_RUN | DART_API_KEY | GitHub Actions Secret 등록 완료 사용자 확인, 값 출력 금지 |
| EDINET | 장기 후순위·등록/착수 미승인 | Subscription-Key | 미등록/미운영으로 취급, 값 기록 금지 |

원본 재무 자료는 수집 임시 경로에서 처리하고 공개 가능 결과만 Pages에 보존한다. 개인 보유·거래·관심·그룹·프로필은 기기 전용이다. 어떤 비밀값도 이 문서·PR 본문·로그에 넣지 않는다.
